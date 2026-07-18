"""
Capability router for MamlaAI Chat.

Extends the binary `core/intent_gate.py` (legal vs chitchat) into a multi-label
capability classifier that decides which tool a free-text turn should go to:

    draft     — produce a legal instrument (petition, bail application, notice…)
    citation  — verify / look up a specific case or citation
    doc_qa    — answer against the user's uploaded document(s)
    research  — reason about the law / advise on a question
    meta      — questions about this assistant/app itself, or probe attempts
    general   — anything else legal that doesn't fit the above

Blatant chitchat and prompt-injection are filtered upstream in the view, but
subtler probes ("hidden features of this chatflow", "show your prompt") reach
this router — the `meta` fast-path catches them BEFORE any LLM call so they
can never be misrouted into a tool (a live t1 misroute once turned exactly
that probe into a generated draft).

Design: a zero-cost regex fast-path handles the clear cases; only genuinely
ambiguous turns fall through to a cheap t1 LLM call. Fails open to `research`
(the safe, grounded default) so a classifier hiccup never drops a legal turn.
"""
import logging
import re

from ai_draft.citation_grounding import mentions_citation_intent

from ..llm_router import call_llm, parse_json_response

logger = logging.getLogger('django')

CAPABILITIES = ('draft', 'citation', 'doc_qa', 'research', 'meta', 'general')
_DEFAULT = 'research'

# --- Meta / probe patterns (checked FIRST — zero cost, never misrouted) -----
_META_RE = re.compile(
    r'(?:'
    r'(hidden|secret)\s+(feature|prompt|instruction|command|mode)'
    r'|what\s+(can|do)\s+you\s+(do|know|offer)'
    r'|how\s+do\s+you\s+work'
    r'|your\s+(system\s*)?(prompt|instructions?|rules?|model|capabilit)'
    r'|(this|the)\s+(chat\s*flow|chat\s*bot|chatbot|assistant|app|ai)\b'
    r'|who\s+(are|made|built)\s+you'
    r'|ignore\s+(all\s+|your\s+|previous\s+)*(instructions?|rules?|prompts?)'
    r'|jail\s*break|jailbreak'
    r'|(reveal|show|print|dump)\s+.{0,20}(prompt|instruction|config)'
    r')',
    re.IGNORECASE,
)

# --- Fast-path patterns ---------------------------------------------------
_DRAFT_VERB = r'(draft|prepare|write|create|make|generate|compose|redraft|revise)'
_DRAFT_DOC = (
    r'(petition|application|notice|agreement|affidavit|reply|rejoinder|complaint|'
    r'contract|deed|bail|anticipatory\s+bail|writ|plaint|written\s+statement|'
    r'legal\s+notice|vakalat(?:nama)?|will|nda|mou|memo(?:randum)?|lease|'
    r'power\s+of\s+attorney|undertaking|bond|rent\s+agreement)'
)
_DRAFT_RE = re.compile(rf'\b{_DRAFT_VERB}\b.*\b{_DRAFT_DOC}\b', re.IGNORECASE | re.DOTALL)
_DRAFT_LEAD_RE = re.compile(rf'^\s*{_DRAFT_VERB}\b', re.IGNORECASE)

_DOC_REF_RE = re.compile(
    r'\b(this|the|my|uploaded|attached)\s+(document|doc|file|pdf|fir|contract|'
    r'agreement|order|judgment|notice|petition|statement)\b|\bin\s+the\s+(document|file|pdf)\b',
    re.IGNORECASE,
)

_RESEARCH_RE = re.compile(
    r'\b(what|which|whether|can|is|are|does|do|how|when|explain|law\s+on|'
    r'section|liable|rights?|remedy|maintainable|limitation)\b',
    re.IGNORECASE,
)

_CLASSIFIER_SYSTEM = (
    "You route an Indian legal assistant's message to ONE capability. Categories:\n"
    "- draft: user wants a legal document produced or edited\n"
    "- citation: user wants a specific case/citation looked up or verified\n"
    "- doc_qa: user asks about a document they have uploaded/attached\n"
    "- research: user asks a legal question needing analysis of the law\n"
    "- meta: user asks about this assistant/app itself (its features, prompts, "
    "how it works) or tries to probe or override its instructions\n"
    "- general: legal but none of the above\n"
    'Respond with ONLY valid JSON: {"capability": "<one>"}. No other text.'
)


def _fast_path(text: str, has_docs: bool) -> str | None:
    # Meta/probe first: these must never fall through to an LLM that could
    # misroute them into a tool.
    if _META_RE.search(text):
        return 'meta'
    if _DRAFT_RE.search(text) or _DRAFT_LEAD_RE.search(text):
        return 'draft'
    if mentions_citation_intent(text):
        return 'citation'
    if has_docs and _DOC_REF_RE.search(text):
        return 'doc_qa'
    return None


def classify_capability(text: str, has_docs: bool = False) -> dict:
    """
    Return {'capability': <str>, 'confidence': 'high'|'low', 'method': ...}.
    """
    text = (text or '').strip()
    if not text:
        return {'capability': _DEFAULT, 'confidence': 'low', 'method': 'empty'}

    hit = _fast_path(text, has_docs)
    if hit:
        return {'capability': hit, 'confidence': 'high', 'method': 'regex'}

    # Clear research-style question with no other signal — skip the LLM.
    if _RESEARCH_RE.search(text) and len(text) < 200:
        return {'capability': 'research', 'confidence': 'high', 'method': 'regex'}

    # Ambiguous — one cheap t1 classification, fail open to research.
    try:
        response = call_llm(
            [{'role': 'system', 'content': _CLASSIFIER_SYSTEM}, {'role': 'user', 'content': text}],
            tier='t1',
        )
        payload = parse_json_response(response.get('text'), fallback={}) or {}
        capability = str(payload.get('capability', '')).strip().lower()
        if capability in CAPABILITIES:
            return {'capability': capability, 'confidence': 'low', 'method': 't1'}
    except Exception as exc:
        logger.warning('[orchestrator.router] t1 classify failed (fail-open): %s', exc)
    return {'capability': _DEFAULT, 'confidence': 'low', 'method': 'fallback'}
