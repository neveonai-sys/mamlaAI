"""
Deterministic checks over a generated draft.

These are pure functions over text — no LLM, no I/O, no Django. They are the
shared substrate for two callers:

  * `ai_draft.evals.rubric.score_deterministic` (Phase 0) — scores golden-set
    runs without spending a token.
  * `ai_draft.drafting.draft_validator` (Phase 2) — gates real generations and
    drives the correction turn.

Writing them once is deliberate: the thing that scores the eval must be the
same thing that guards production, or the eval measures a fiction.

Each documented defect from the intern benchmark maps to a function here:
  defect #1 (BNSS in a civil rent notice)      -> find_statute_misuse
  defect #2 (no NOW THEREFORE / TAKE NOTICE)   -> find_missing_phrases
  defect #3a (deed ends mid-sentence)          -> detect_truncation
  defect #3b (50:30:20 silently dropped)       -> find_dropped_literals
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Text normalisation
#
# Section content is stored as HTML (the drafting workspace editor is
# contentEditable and posts innerHTML), so every check must strip tags before
# pattern-matching or a `<strong>NOW THEREFORE</strong>` would read as a miss.
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r'<[^>]+>')
_ENTITY_RE = re.compile(r'&(nbsp|amp|lt|gt|quot|#39|rsquo|lsquo|ldquo|rdquo);')
_ENTITIES = {
    'nbsp': ' ', 'amp': '&', 'lt': '<', 'gt': '>', 'quot': '"',
    '#39': "'", 'rsquo': "'", 'lsquo': "'", 'ldquo': '"', 'rdquo': '"',
}
_WS_RE = re.compile(r'[ \t\r\f\v]+')


def strip_html(text: str) -> str:
    """Reduce editor HTML to plain text, preserving line structure."""
    if not text:
        return ''
    # Block-level tags become newlines so heading/paragraph boundaries survive.
    out = re.sub(r'(?i)<\s*(br|/p|/div|/li|/h[1-6])\s*/?>', '\n', text)
    out = _TAG_RE.sub('', out)
    out = _ENTITY_RE.sub(lambda m: _ENTITIES.get(m.group(1), ' '), out)
    out = _WS_RE.sub(' ', out)
    return out.strip()


def sections_text(sections: list) -> str:
    """Concatenate every section's name + content as plain text."""
    parts = []
    for s in sections or []:
        if not isinstance(s, dict):
            continue
        parts.append(strip_html(s.get('section_name') or ''))
        parts.append(strip_html(s.get('content') or ''))
    return '\n'.join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Defect #1 — statute misuse
#
# The penal codes must never appear in a civil / commercial / testamentary /
# family instrument. This is the exact error the reviewers flagged twice: BNSS
# threatened for eviction in a rent dispute, BNS+BNSS cited as the basis of a
# contractual money claim.
# ---------------------------------------------------------------------------

PENAL_TOKEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r'\bBNSS\b', 'BNSS'),
    (r'\bBNS\b', 'BNS'),
    (r'\bBSA\b', 'BSA'),
    (r'\bIPC\b', 'IPC'),
    (r'\bCr\.?\s?P\.?\s?C\.?(?![a-z])', 'CrPC'),
    (r'Bharatiya\s+Nyaya\s+Sanhita', 'Bharatiya Nyaya Sanhita'),
    (r'Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita', 'Bharatiya Nagarik Suraksha Sanhita'),
    (r'Bharatiya\s+Sakshya\s+Adhiniyam', 'Bharatiya Sakshya Adhiniyam'),
    (r'Indian\s+Penal\s+Code', 'Indian Penal Code'),
    (r'Code\s+of\s+Criminal\s+Procedure', 'Code of Criminal Procedure'),
    (r'Indian\s+Evidence\s+Act', 'Indian Evidence Act'),
)

# A draft may legitimately say "this is a civil matter; the penal codes do not
# apply". Only exempt a hit when its own sentence carries that disclaimer —
# scoped narrowly so it cannot be used to smuggle a real citation through.
_DISCLAIMER_RE = re.compile(
    r'not\s+applicable|no\s+criminal|does\s+not\s+apply|inapplicable|'
    r'civil\s+in\s+nature|purely\s+civil|not\s+a\s+criminal',
    re.IGNORECASE,
)

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?;])\s+|\n+')


def _sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_SPLIT_RE.split(text or '') if s.strip()]


@dataclass(frozen=True)
class StatuteHit:
    token: str
    sentence: str
    section_name: str


def find_statute_misuse(
    sections: list,
    deny_patterns: tuple[tuple[str, str], ...] = PENAL_TOKEN_PATTERNS,
    extra_text: str = '',
) -> list[StatuteHit]:
    """
    Return every disallowed statute reference, sentence-scoped.

    `extra_text` lets the caller sweep drafting_notes alongside the sections —
    a note that *recommends* citing BNSS is as wrong as a section that does.
    """
    compiled = [(re.compile(p, re.IGNORECASE), label) for p, label in deny_patterns]
    hits: list[StatuteHit] = []

    haystacks: list[tuple[str, str]] = []
    for s in sections or []:
        if isinstance(s, dict):
            haystacks.append((
                strip_html(s.get('section_name') or '') or '(untitled)',
                strip_html(s.get('content') or ''),
            ))
    if extra_text:
        haystacks.append(('(drafting notes)', strip_html(extra_text)))

    for section_name, body in haystacks:
        for sentence in _sentences(body):
            if _DISCLAIMER_RE.search(sentence):
                continue
            for rx, label in compiled:
                if rx.search(sentence):
                    hits.append(StatuteHit(
                        token=label,
                        sentence=sentence.strip()[:240],
                        section_name=section_name,
                    ))
    return hits


# ---------------------------------------------------------------------------
# Defect #2 — missing structural phrases
#
# An Indian legal notice without "NOW THEREFORE" and "TAKE NOTICE" is not a
# legal notice. Playbooks declare these as `must_contain`; this asserts them.
# ---------------------------------------------------------------------------

#: An alternative prefixed `re:` is treated as a case-insensitive regex rather
#: than a literal substring. Needed for clause-level checks, where what matters
#: is a legal concept and not a word sequence: a restraint on alienation is
#: equally well drafted as "shall not sell, mortgage or alienate", "shall NOT
#: have the power to sell ... or otherwise alienate", and "without any power of
#: alienation". Enumerating surface forms produced a false positive on a
#: correctly-drafted life interest, which is the failure mode that matters here
#: — a check that scores good drafting as a defect steers the product toward
#: the defect.
_REGEX_PREFIX = 're:'


def _phrase_present(alt: str, hay_lower: str, hay: str) -> bool:
    alt = str(alt).strip()
    if not alt:
        return False
    if alt.startswith(_REGEX_PREFIX):
        pattern = alt[len(_REGEX_PREFIX):]
        try:
            return bool(re.search(pattern, hay, re.IGNORECASE))
        except re.error:
            # A malformed fixture pattern must not crash a whole eval run; it
            # reads as "not present", which surfaces as a visible finding.
            return False
    return alt.lower() in hay_lower


def find_missing_phrases(sections: list, phrases) -> list[str]:
    """
    Return the required phrases absent from the draft (case-insensitive).

    An entry may be a string, or a list of accepted alternatives satisfied when
    ANY one is present. The convention genuinely admits variants — a demand
    paragraph opening "NOW THEREFORE, I hereby call upon you" and one opening
    "I, therefore, call upon you" are both proper; only the absence of an
    operative demand is a defect. Asserting a single phrasing would make the
    check measure style rather than compliance.

    An alternative may be written `re:<pattern>` to match by regex.
    """
    hay = sections_text(sections)
    hay_lower = hay.lower()
    missing: list[str] = []
    for entry in (phrases or ()):
        alts = [entry] if isinstance(entry, str) else list(entry)
        if not any(_phrase_present(a, hay_lower, hay) for a in alts):
            missing.append(' / '.join(str(a) for a in alts))
    return missing


def _norm_section_name(name: str) -> str:
    """Fold a section name for comparison: upper, no punctuation, no articles."""
    n = strip_html(name or '').upper()
    n = re.sub(r'[^A-Z0-9 ]+', ' ', n)
    n = re.sub(r'\b(THE|A|AN|OF|FOR|AND)\b', ' ', n)
    return re.sub(r'\s+', ' ', n).strip()


def find_missing_sections(sections: list, required_names: tuple[str, ...]) -> list[str]:
    """
    Return required section names with no counterpart in the draft.

    Matching is fuzzy-by-normalisation and substring-tolerant in both
    directions, so "NOW THEREFORE" matches a section titled
    "NOW THEREFORE — DEMAND".
    """
    present = [_norm_section_name(s.get('section_name', ''))
               for s in (sections or []) if isinstance(s, dict)]
    missing = []
    for want in required_names or ():
        w = _norm_section_name(want)
        if not w:
            continue
        if not any(w in p or p in w for p in present if p):
            missing.append(want)
    return missing


# ---------------------------------------------------------------------------
# Defect #3a — truncation
#
# The benchmark's partnership deed ended "...shall sign below in the presence
# of the". max_tokens=4000 cut it mid-clause and nothing noticed.
# ---------------------------------------------------------------------------

_TERMINAL_RE = re.compile(r'[.!?:;\'"\)\]—’”]\s*$')
_DANGLING_RE = re.compile(
    r'\b(the|of|and|to|by|for|in|on|at|with|from|a|an|is|are|was|were|be|been|'
    r'shall|will|may|must|that|which|who|whom|whose|as|or|nor|but|if|before|'
    r'after|under|over|between|among|upon|into|presence|pursuant|subject)\s*$',
    re.IGNORECASE,
)
# A signature, attestation or designation block legitimately ends on a role word
# with no full stop ("Yours faithfully, [ADVOCATE'S NAME], Advocate"). Treating
# that as truncation would penalise a correctly-drafted closing.
_SIGNATURE_TAIL_RE = re.compile(
    r'\b(advocate|counsel|testator|testatrix|deponent|witness(?:es)?|partner|'
    r'petitioner|plaintiff|applicant|complainant|executor|executrix|proprietor|'
    r'director|signature|sd/-|seal)\s*$',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TruncationHit:
    section_name: str
    tail: str
    reason: str  # 'no_terminal_punctuation' | 'dangling_connective' | 'finish_reason_length'


def detect_truncation(sections: list, finish_reason: str | None = None) -> list[TruncationHit]:
    """
    Flag a draft that stopped mid-thought.

    `finish_reason == 'length'` from the provider is authoritative on its own;
    the textual heuristics catch the cases where the field is unavailable
    (it is not surfaced by `chat_complete` today — Phase 0 adds it).
    """
    hits: list[TruncationHit] = []

    bodies = [(strip_html(s.get('section_name') or '') or '(untitled)',
               strip_html(s.get('content') or ''))
              for s in (sections or []) if isinstance(s, dict)]
    bodies = [(n, b) for n, b in bodies if b]

    if finish_reason == 'length':
        name = bodies[-1][0] if bodies else '(no sections)'
        tail = bodies[-1][1][-120:] if bodies else ''
        hits.append(TruncationHit(name, tail, 'finish_reason_length'))

    if not bodies:
        return hits

    name, body = bodies[-1]
    tail = body[-120:]
    if _DANGLING_RE.search(body):
        # Unambiguous: no well-formed clause ends on "of the".
        hits.append(TruncationHit(name, tail, 'dangling_connective'))
    elif not _TERMINAL_RE.search(body):
        # Missing punctuation alone is weak evidence — signature and attestation
        # blocks are short and end on a designation by convention.
        if not (_SIGNATURE_TAIL_RE.search(body) or len(body) < 120):
            hits.append(TruncationHit(name, tail, 'no_terminal_punctuation'))
    return hits


# ---------------------------------------------------------------------------
# Defect #3b — dropped instructions
#
# The prompt said 50:30:20. The deed never mentioned it and never flagged the
# omission. Ratios and percentages are unambiguous enough to assert; money and
# durations vary too much in representation ("Rs. 2.8 crore" vs "2,80,00,000")
# so they are reported at lower confidence.
# ---------------------------------------------------------------------------

# Indian legal drafting writes a numeral then the same figure in words —
# "15 (fifteen) days", "Rs 96,000/- (Rupees Ninety-Six Thousand only)". The
# patterns must step over that parenthetical or every honoured instruction
# reads as dropped.
_WORDS_PAREN = r'(?:\s*\([^)]{0,40}\))?'

_RATIO_RE = re.compile(r'\d{1,3}\s*[:：]\s*\d{1,3}(?:\s*[:：]\s*\d{1,3})*')
_PERCENT_RE = re.compile(
    rf'\d{{1,3}}(?:\.\d+)?{_WORDS_PAREN}\s*(?:%|per\s*cent|percent)', re.IGNORECASE)
_MONEY_RE = re.compile(
    rf'(?:Rs\.?|₹|INR)\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakhs?|crores?))?{_WORDS_PAREN}'
    rf'|\b[\d,]+(?:\.\d+)?\s*(?:lakhs?|crores?)\b',
    re.IGNORECASE,
)
_DURATION_RE = re.compile(
    rf'\b\d{{1,4}}{_WORDS_PAREN}\s*(?:days?|weeks?|months?|years?)\b', re.IGNORECASE)


@dataclass(frozen=True)
class Literal:
    raw: str
    kind: str        # 'ratio' | 'percent' | 'money' | 'duration'
    confidence: str  # 'high' -> error on omission; 'low' -> warn


def extract_prompt_literals(user_query: str) -> list[Literal]:
    """Pull the express numeric instructions a draft must honour or flag."""
    q = user_query or ''
    seen: set[str] = set()
    out: list[Literal] = []

    def _add(raw: str, kind: str, confidence: str):
        key = _normalize_literal(raw)
        if key and key not in seen:
            seen.add(key)
            out.append(Literal(raw=raw.strip(), kind=kind, confidence=confidence))

    for m in _RATIO_RE.finditer(q):
        _add(m.group(0), 'ratio', 'high')
    for m in _PERCENT_RE.finditer(q):
        _add(m.group(0), 'percent', 'high')
    for m in _MONEY_RE.finditer(q):
        _add(m.group(0), 'money', 'low')
    for m in _DURATION_RE.finditer(q):
        _add(m.group(0), 'duration', 'low')
    return out


#: Indian numbering multipliers. An amount instructed as "Rs 70 lakh" is
#: routinely — and more properly — drafted as "Rs. 70,00,000/- (Rupees Seventy
#: Lakh only)". Folding both to the same key is what stops a compliant notice
#: being reported as having silently dropped the amount it is actually claiming.
_MULTIPLIERS = {'lakh': 100000, 'crore': 10000000}


def _normalize_literal(raw: str) -> str:
    """
    Collapse a literal to a comparable key.

    "₹96,000" / "Rs. 96,000/-" / "96000" all reduce to "96000"; "50:30:20" and
    "50 : 30 : 20" both reduce to "50:30:20".

    A lakh/crore amount is expanded to its digit value, so "70 lakh" and
    "70,00,000" agree. Without that expansion the check reported a draft
    claiming "Rs. 70,00,000/- (Rupees Seventy Lakh only)" as having dropped the
    instructed "Rs 70 lakh" — a false positive on the flagship
    silently-dropped-instruction check, on the very case it exists to measure.
    """
    s = (raw or '').lower()
    s = re.sub(r'(rs\.?|₹|inr|/-)', '', s)
    unit = ''
    m = re.search(r'(lakhs?|crores?|days?|months?|years?|%|per\s*cent|percent)', s)
    if m:
        unit = re.sub(r's$|\s+', '', m.group(1))
        unit = 'percent' if unit in ('%', 'percent', 'percen') else unit
    digits = re.sub(r'[^\d:.]', '', s).strip('.')
    if not digits:
        return ''

    if unit in _MULTIPLIERS and ':' not in digits:
        try:
            value = float(digits) * _MULTIPLIERS[unit]
        except ValueError:
            pass
        else:
            # Money only. A duration never carries these units, so nothing else
            # is affected by the fold.
            return f'{int(value)}|' if value == int(value) else f'{value}|'

    return f'{digits}|{unit}'


def find_dropped_literals(
    user_query: str,
    sections: list,
    notes_text: str = '',
    only: tuple[str, ...] = (),
) -> list[Literal]:
    """
    Return express numeric instructions that appear in neither the draft body
    nor the drafting notes.

    Flagging the omission in `drafting_notes` counts as honouring it — the
    failure mode we are guarding against is *silent* omission.

    `only` restricts the check to caller-supplied literals (the eval fixtures
    do this, so a golden case asserts exactly what it means to assert).
    """
    literals = ([Literal(raw=o, kind='explicit', confidence='high') for o in only]
                if only else extract_prompt_literals(user_query))

    text = sections_text(sections) + '\n' + strip_html(notes_text)
    hay_keys = {_normalize_literal(m) for m in _all_numeric_tokens(text)}
    hay_keys.discard('')

    dropped = []
    for lit in literals:
        if _normalize_literal(lit.raw) in hay_keys:
            continue
        if _ratio_honoured_as_percentages(lit.raw, text):
            continue
        dropped.append(lit)
    return dropped


_RATIO_ONLY_RE = re.compile(r'^\s*\d{1,3}(?:\s*[:：]\s*\d{1,3})+\s*$')


def _ratio_honoured_as_percentages(raw: str, text: str) -> bool:
    """
    A ratio may properly be drafted as separate percentages.

    An instruction of "50:30:20" is honoured by a clause reading "Aarav shall
    receive 50%, Rohan 30%, and Priya 20%" — arguably the clearer drafting.
    Demanding the literal colon form would report a compliant deed as having
    silently dropped the instruction, which is worse than not checking at all.

    Deliberately strict: EVERY component must appear as a percentage. Matching
    on bare numbers would accept an unrelated "20" elsewhere in the document.
    """
    if not _RATIO_ONLY_RE.match(raw or ''):
        return False
    parts = [p.strip() for p in re.split(r'[:：]', raw.strip()) if p.strip()]
    if len(parts) < 2:
        return False

    found = set()
    for m in _PERCENT_RE.finditer(text or ''):
        lead = re.match(r'\s*(\d+)', m.group(0))
        if lead:
            found.add(lead.group(1).lstrip('0') or '0')

    return all((p.lstrip('0') or '0') in found for p in parts)


def _all_numeric_tokens(text: str) -> list[str]:
    """Every ratio / percent / money / duration token appearing in `text`."""
    out: list[str] = []
    for rx in (_RATIO_RE, _PERCENT_RE, _MONEY_RE, _DURATION_RE):
        out.extend(m.group(0) for m in rx.finditer(text or ''))
    # Bare number runs too, so "50:30:20" in the prompt still matches a draft
    # that wrote "50 : 30 : 20" inside a table cell or split across tags.
    out.extend(m.group(0) for m in re.finditer(r'[\d,]{2,}(?:\.\d+)?', text or ''))
    return out


# ---------------------------------------------------------------------------
# Defect #4 support — placeholders and advisories
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r'\[([^\[\]]{1,80})\]')


@dataclass
class PlaceholderReport:
    tokens: list[str] = field(default_factory=list)
    lowercase: list[str] = field(default_factory=list)
    unclosed: int = 0


def inspect_placeholders(sections: list) -> PlaceholderReport:
    """Collect `[PLACEHOLDER]` tokens and flag malformed ones."""
    text = sections_text(sections)
    rep = PlaceholderReport()
    for m in _PLACEHOLDER_RE.finditer(text):
        tok = m.group(1).strip()
        if not tok:
            continue
        if tok not in rep.tokens:
            rep.tokens.append(tok)
        # A placeholder must be ALL CAPS so it is visually obvious in the draft.
        if re.search(r'[a-z]', tok) and tok not in rep.lowercase:
            rep.lowercase.append(tok)
    rep.unclosed = max(0, text.count('[') - text.count(']'))
    return rep
