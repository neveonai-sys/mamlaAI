"""
Document-type classification.

The frontend has been sending `document_type` on every draft request all along
(`DraftingWorkspace.jsx:972`); the backend has never read it. This module is the
other end of that wire, plus the fallbacks for the four entry points that have no
explicit hint.

Order is cheap-first, and deliberately so — an explicit hint or a keyword hit
costs nothing, and only a genuinely ambiguous free-text query is worth an LLM
round trip:

    explicit hint  ->  keyword scan  ->  one brain:t1 call  ->  GENERIC

`branch` is never classified. It is read off the playbook, so the statute gate
cannot disagree with the document type.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from . import playbooks

logger = logging.getLogger(__name__)

# Confidence levels, in descending order of trust.
EXPLICIT = 'explicit'
KEYWORD = 'keyword'
LLM = 'llm'
FALLBACK = 'fallback'

#: Minimum keyword score to accept a classification. Below this the query has
#: not said enough — one stray "notice" should not route a will to the notice
#: playbook.
_KEYWORD_THRESHOLD = 5

#: Characters at the head of a query treated as the *request*, as opposed to the
#: *facts*. A drafting instruction names the document it wants up front ("Draft a
#: legal notice from my client ...") and only then recites the background, which
#: routinely names a different instrument ("... under a lease agreement dated
#: ..."). Without this split, fixture 001 — a rent-arrears NOTICE — classifies as
#: a lease AGREEMENT, because the underlying instrument is mentioned more often
#: than the document actually requested. Matches inside the lead window score
#: twice: once for the whole text, once again here.
_LEAD_CHARS = 200


@dataclass(frozen=True)
class DraftContext:
    """What the prompt builder and validator both need to know about a draft."""

    doc_type: str
    branch: str
    label: str
    confidence: str
    source: str

    @property
    def playbook(self):
        return playbooks.get(self.doc_type)

    @property
    def is_generic(self) -> bool:
        return self.doc_type == playbooks.GENERIC.doc_type

    def to_dict(self) -> dict:
        return {
            'doc_type': self.doc_type,
            'branch': self.branch,
            'label': self.label,
            'confidence': self.confidence,
            'source': self.source,
        }

    @classmethod
    def from_dict(cls, raw: dict | None) -> 'DraftContext | None':
        """Rehydrate a stored context. Returns None if it is unusable."""
        if not isinstance(raw, dict) or not raw.get('doc_type'):
            return None
        pb = playbooks.get(raw.get('doc_type'))
        if pb.doc_type == playbooks.GENERIC.doc_type and raw.get('doc_type') != 'generic':
            return None          # stored a type we no longer recognise
        return cls(
            doc_type=pb.doc_type,
            branch=pb.branch,
            label=pb.label,
            confidence=raw.get('confidence') or FALLBACK,
            source=raw.get('source') or FALLBACK,
        )


def _context(pb, confidence: str, source: str) -> DraftContext:
    return DraftContext(
        doc_type=pb.doc_type,
        branch=pb.branch,
        label=pb.label,
        confidence=confidence,
        source=source,
    )


# ---------------------------------------------------------------------------
# Type-hint normalisation
# ---------------------------------------------------------------------------

#: Keys that mark a payload as case/client association rather than a document
#: type. `draft_for` is `[{case_id, client_id, client_name}]` — threading it into
#: the prompt would inject a client's name where a document type belongs. The
#: chat path overloads the same argument with a genuine string label, so the
#: refusal has to be by shape, not by argument name.
_ASSOCIATION_KEYS = frozenset({
    'case_id', 'caseid', 'client_id', 'clientid', 'client_name', 'clientname',
    'caseid_with_clientid', 'case_number', 'personal',
})

#: The same association vocabulary arriving as a bare string. `draft_for` is
#: filtered to `caseid|clientid|personal`, so those literals reach us on their
#: own as well as inside a dict.
_ASSOCIATION_LITERALS = frozenset({
    'personal', 'caseid', 'clientid', 'case_id', 'client_id',
    'caseid_with_clientid', 'case', 'client',
})

_SEPARATORS_RE = re.compile(r'[_\-/]+')


def normalize_type_hint(raw) -> str:
    """
    Reduce whatever a caller supplies to a lookup key, or '' if it carries none.

    Accepts a string, a list (first usable entry wins), or a dict. Deliberately
    REFUSES case/client association payloads — returning '' so the caller falls
    through to the keyword scan rather than classifying on a client's name.
    """
    if raw is None:
        return ''

    if isinstance(raw, dict):
        if _ASSOCIATION_KEYS & {str(k).strip().lower() for k in raw.keys()}:
            logger.debug('normalize_type_hint: refusing case/client payload %s', list(raw.keys()))
            return ''
        for key in ('document_type', 'doc_type', 'draft_type', 'type', 'label'):
            if raw.get(key):
                return normalize_type_hint(raw[key])
        return ''

    if isinstance(raw, (list, tuple)):
        for item in raw:
            hint = normalize_type_hint(item)
            if hint:
                return hint
        return ''

    text = str(raw).strip()
    if not text or len(text) > 120:
        return ''
    if text.lower() in _ASSOCIATION_LITERALS:
        logger.debug('normalize_type_hint: refusing association literal %r', text)
        return ''
    return text


def _resolve_hint(hint: str):
    """Alias lookup, then a punctuation-insensitive retry. None if no match."""
    if not hint:
        return None
    if playbooks.exists(hint):
        return playbooks.get(hint)

    loosened = _SEPARATORS_RE.sub(' ', hint).strip().lower()
    if playbooks.exists(loosened):
        return playbooks.get(loosened)

    collapsed = re.sub(r'\s+', ' ', loosened)
    for alias, doc_type in playbooks.aliases().items():
        if _SEPARATORS_RE.sub(' ', alias) == collapsed:
            return playbooks.get(doc_type)
    return None


# ---------------------------------------------------------------------------
# Keyword scan
# ---------------------------------------------------------------------------

def score_all(text: str) -> list[tuple[int, object]]:
    """
    Every playbook with a non-zero score, best first. Exposed for tests.

    Score is `score(whole text) + score(lead window)`, so a document type named
    in the instruction outranks one merely recited in the facts.
    """
    lead = (text or '')[:_LEAD_CHARS]
    scored = [(pb.score(text) + pb.score(lead), pb) for pb in playbooks.all_playbooks()]
    scored = [(s, pb) for s, pb in scored if s > 0]
    scored.sort(key=lambda pair: (-pair[0], pair[1].doc_type))
    return scored


def _keyword_classify(text: str):
    scored = score_all(text)
    if not scored:
        return None
    best_score, best = scored[0]
    if best_score < _KEYWORD_THRESHOLD:
        return None
    return best


# ---------------------------------------------------------------------------
# LLM fallback — one cheap call, closed enum, fails soft
# ---------------------------------------------------------------------------

_CLASSIFY_SYSTEM = """\
You classify Indian legal drafting requests by document type.

Reply with ONLY a JSON object: {"doc_type": "<one of the allowed values>"}

Allowed values (use EXACTLY one of these strings):
%s

Choose "generic" if the request does not clearly match any listed type. Do not
explain. Do not add any text outside the JSON object."""


def _llm_classify(user_query: str):
    """One `brain:t1` call. Any failure returns None — classification is never fatal."""
    allowed = [pb.doc_type for pb in playbooks.all_playbooks()] + [playbooks.GENERIC.doc_type]
    enum_block = '\n'.join(
        f'  {pb.doc_type} — {pb.label}' for pb in playbooks.all_playbooks()
    ) + '\n  generic — anything else'

    try:
        from core import llm_client          # local import: keeps this module Django-free

        raw = llm_client.chat_complete(
            messages=[
                {'role': 'system', 'content': _CLASSIFY_SYSTEM % enum_block},
                {'role': 'user', 'content': (user_query or '')[:2000]},
            ],
            app_scenario='brain:t1',
            temperature=0,
            max_tokens=60,
        )
    except Exception as exc:
        logger.warning('[classify] LLM classification failed: %s', exc)
        return None

    try:
        match = re.search(r'\{.*\}', raw or '', re.DOTALL)
        doc_type = (json.loads(match.group(0)) if match else {}).get('doc_type', '')
    except Exception:
        logger.warning('[classify] LLM returned unparseable payload: %r', (raw or '')[:200])
        return None

    doc_type = str(doc_type).strip().lower()
    if doc_type not in allowed:
        logger.warning('[classify] LLM returned out-of-enum doc_type %r', doc_type)
        return None
    return playbooks.get(doc_type)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def classify(user_query: str = '', type_hint=None, *, allow_llm: bool = True) -> DraftContext:
    """
    Resolve a draft request to a `DraftContext`.

    `type_hint` is whatever the caller has — the frontend's `document_type`, the
    chat agent's label, or a stored `draft_type`. Anything unusable (including a
    case/client payload) is ignored rather than trusted.
    """
    hint = normalize_type_hint(type_hint)
    if hint:
        pb = _resolve_hint(hint)
        if pb is not None:
            return _context(pb, EXPLICIT, EXPLICIT)
        # An unrecognised hint is still a signal — fold it into the text we scan.
        logger.debug('[classify] unrecognised type hint %r; falling through', hint)

    haystack = ' '.join(part for part in (hint, user_query or '') if part).strip()

    pb = _keyword_classify(haystack)
    if pb is not None:
        return _context(pb, KEYWORD, KEYWORD)

    if allow_llm and (user_query or '').strip():
        pb = _llm_classify(haystack)
        if pb is not None and pb.doc_type != playbooks.GENERIC.doc_type:
            return _context(pb, LLM, LLM)

    return _context(playbooks.GENERIC, FALLBACK, FALLBACK)
