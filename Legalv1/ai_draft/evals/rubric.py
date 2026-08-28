"""
Scoring a generated draft against a golden case.

`score_deterministic` is the load-bearing one. It is pure functions over the
parsed draft — no model, no network, no cost — and it catches all four defect
classes the intern benchmark documented, because each is a structural fact
about the text rather than a matter of taste:

    statute       defect #1  penal codes in a civil/commercial/testamentary draft
    format        defect #2  missing recitals / NOW THEREFORE / TAKE NOTICE
    completeness  defect #3a truncation, thin section coverage
    compliance    defect #3b dropped express instructions, #4 missing advisories

`score_judge` handles what deterministic checks cannot: whether the thing reads
like an advocate wrote it. One model call, strict JSON, opt-in.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from ai_draft.drafting import checks as C

from .schema import GoldenCase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalising whatever the engine handed back
# ---------------------------------------------------------------------------

@dataclass
class ParsedDraft:
    """
    Engine output in a shape the scorer understands.

    Accepts both the legacy bare list (today's engine) and the Phase 2 object
    with advisories, so the same scorer measures before and after — which is
    the whole point of recording a baseline.
    """
    sections: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    drafting_notes: list = field(default_factory=list)
    document_type: str = ''
    finish_reason: str | None = None
    raw_error: str = ''

    @property
    def notes_text(self) -> str:
        """Advisories flattened to text, for the dropped-literal sweep."""
        bits = []
        for a in self.assumptions:
            bits.append(a if isinstance(a, str) else ' '.join(str(v) for v in a.values()))
        for n in self.drafting_notes:
            bits.append(n if isinstance(n, str) else ' '.join(str(v) for v in n.values()))
        return '\n'.join(bits)


def normalize_draft(raw, finish_reason: str | None = None) -> ParsedDraft:
    """Coerce engine output into a ParsedDraft. Never raises."""
    if raw is None:
        return ParsedDraft(raw_error='engine returned None')
    if isinstance(raw, list):
        # Legacy shape: a bare array of sections, no advisory channel.
        return ParsedDraft(sections=[s for s in raw if isinstance(s, dict)],
                           finish_reason=finish_reason)
    if isinstance(raw, dict):
        sections = raw.get('sections')
        if not isinstance(sections, list):
            sections = [raw] if 'section_name' in raw else []
        return ParsedDraft(
            sections=[s for s in sections if isinstance(s, dict)],
            assumptions=raw.get('assumptions') or [],
            drafting_notes=raw.get('drafting_notes') or [],
            document_type=raw.get('document_type') or '',
            finish_reason=finish_reason or raw.get('finish_reason'),
        )
    return ParsedDraft(raw_error=f'unexpected engine output type {type(raw).__name__}')


# ---------------------------------------------------------------------------
# Scores
# ---------------------------------------------------------------------------

@dataclass
class SubScore:
    name: str
    score: float          # 0-10
    weight: float
    findings: list[str] = field(default_factory=list)

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass
class CaseScore:
    case_id: str
    overall: float
    subscores: list[SubScore]
    section_count: int
    document_type: str = ''
    judge: dict | None = None
    error: str = ''

    @property
    def hard_failures(self) -> list[str]:
        """Sub-scores at zero — the ones that make a draft unusable, not merely weak."""
        return [s.name for s in self.subscores if s.score <= 0.0]

    def as_dict(self) -> dict:
        return {
            'case_id': self.case_id,
            'overall': round(self.overall, 2),
            'section_count': self.section_count,
            'document_type': self.document_type,
            'error': self.error,
            'hard_failures': self.hard_failures,
            'subscores': [
                {'name': s.name, 'score': round(s.score, 2),
                 'weight': s.weight, 'findings': s.findings}
                for s in self.subscores
            ],
            'judge': self.judge,
        }


def _clamp(v: float) -> float:
    return max(0.0, min(10.0, v))


def score_deterministic(draft: ParsedDraft, case: GoldenCase) -> CaseScore:
    exp = case.expect
    w = exp.rubric_weights

    if draft.raw_error or not draft.sections:
        # Nothing usable came back. Today this is silent — the session is written
        # with an empty section list and the UI spins forever (cause G).
        subs = [SubScore(n, 0.0, w.get(n, 0.0), ['no usable draft produced'])
                for n in ('format', 'statute', 'completeness', 'compliance')]
        return CaseScore(case.id, 0.0, subs, 0,
                         error=draft.raw_error or 'engine returned zero sections')

    subs = [
        _score_statute(draft, exp, w.get('statute', 0.0)),
        _score_format(draft, exp, w.get('format', 0.0)),
        _score_completeness(draft, exp, w.get('completeness', 0.0)),
        _score_compliance(draft, case, w.get('compliance', 0.0)),
    ]
    overall = sum(s.weighted for s in subs)
    return CaseScore(case.id, overall, subs, len(draft.sections),
                     document_type=draft.document_type)


def _score_statute(draft: ParsedDraft, exp, weight: float) -> SubScore:
    """
    Binary by design. A penal-code citation in a civil rent notice is not a
    partial-credit situation — the reviewers called it "a substantive legal
    error [that] would damage the notice's credibility". It either happened or
    it did not.
    """
    findings: list[str] = []

    if exp.forbid_penal_statutes:
        for hit in C.find_statute_misuse(draft.sections, extra_text=draft.notes_text):
            findings.append(
                f'{hit.token} cited in "{hit.section_name}": {hit.sentence[:120]}'
            )

    text = C.sections_text(draft.sections) + '\n' + draft.notes_text
    for pattern in exp.must_not_match:
        m = re.search(pattern, text)
        if m:
            findings.append(f'forbidden pattern matched: {m.group(0)[:120]!r}')

    return SubScore('statute', 0.0 if findings else 10.0, weight, findings)


def _score_format(draft: ParsedDraft, exp, weight: float) -> SubScore:
    """Indian drafting conventions — the fix for defect #2."""
    findings: list[str] = []

    missing_phrases = C.find_missing_phrases(draft.sections, exp.must_contain)
    missing_sections = C.find_missing_sections(draft.sections, exp.must_contain_section_names)

    required = len(exp.must_contain) + len(exp.must_contain_section_names)
    satisfied = required - len(missing_phrases) - len(missing_sections)
    base = (satisfied / required * 10.0) if required else 10.0

    for p in missing_phrases:
        findings.append(f'missing required phrase: {p!r}')
    for s in missing_sections:
        findings.append(f'missing required section: {s!r}')

    hay = C.sections_text(draft.sections).lower()
    penalty = 0.0
    for banned in exp.must_not_contain:
        if banned.lower() in hay:
            findings.append(f'form-like heading present: {banned!r}')
            penalty += 3.0

    return SubScore('format', _clamp(base - penalty), weight, findings)


_MISSING_CLAUSE_PENALTY = 3.0


def _score_completeness(draft: ParsedDraft, exp, weight: float) -> SubScore:
    """
    Does the document actually contain its operative provisions, does it cover
    the expected ground, and does it terminate properly (defect #3a).

    Missing a load-bearing clause is penalised heavily and per-occurrence — two
    omissions take a full-coverage document below passing, which is the right
    verdict on an instrument that cannot be executed as drafted.
    """
    findings: list[str] = []

    n = len(draft.sections)
    base = min(1.0, n / exp.min_sections) * 10.0 if exp.min_sections else 10.0
    if n < exp.min_sections:
        findings.append(f'{n} sections, expected at least {exp.min_sections}')

    for clause in C.find_missing_phrases(draft.sections, exp.must_contain_clauses):
        findings.append(f'missing operative provision: {clause}')
        base -= _MISSING_CLAUSE_PENALTY

    truncations = C.detect_truncation(draft.sections, draft.finish_reason)
    if truncations:
        for t in truncations:
            findings.append(f'truncated ({t.reason}) in "{t.section_name}": ...{t.tail[-70:]!r}')
        # A document that stops mid-clause is not filable regardless of length.
        base = min(base, 3.0)

    empty = [s.get('section_name', '?') for s in draft.sections
             if not C.strip_html(s.get('content') or '').strip()]
    if empty:
        findings.append(f'empty sections: {empty}')
        base -= 1.5 * len(empty)

    return SubScore('completeness', _clamp(base), weight, findings)


def _score_compliance(draft: ParsedDraft, case: GoldenCase, weight: float) -> SubScore:
    """
    Did it honour what it was expressly told — defect #3b — and did it produce
    the assumptions / issue list it was asked for — defect #4.
    """
    exp = case.expect
    findings: list[str] = []
    parts: list[float] = []

    if exp.literals_from_prompt:
        dropped = C.find_dropped_literals(
            case.prompt, draft.sections,
            notes_text=draft.notes_text,
            only=exp.literals_from_prompt,
        )
        for lit in dropped:
            findings.append(
                f'express instruction {lit.raw!r} appears nowhere in the draft '
                f'and is not flagged in drafting_notes'
            )
        honoured = len(exp.literals_from_prompt) - len(dropped)
        parts.append(honoured / len(exp.literals_from_prompt) * 10.0)

    if exp.require_assumptions:
        if draft.assumptions:
            parts.append(10.0)
        else:
            findings.append('no assumptions returned, though the prompt asked for them')
            parts.append(0.0)

    if exp.require_drafting_notes:
        if draft.drafting_notes:
            parts.append(10.0)
        else:
            findings.append('no drafting_notes returned, though the prompt asked '
                            'it to identify legal/drafting issues')
            parts.append(0.0)

    ph = C.inspect_placeholders(draft.sections)
    if ph.unclosed:
        findings.append(f'{ph.unclosed} unclosed placeholder bracket(s)')
    if ph.lowercase:
        findings.append(f'placeholders not in ALL CAPS: {ph.lowercase[:5]}')

    base = sum(parts) / len(parts) if parts else 10.0
    if ph.unclosed or ph.lowercase:
        base -= 1.0

    return SubScore('compliance', _clamp(base), weight, findings)


# ---------------------------------------------------------------------------
# LLM judge — for the qualities a regex cannot see
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = """You are a senior Indian advocate reviewing an AI-generated legal draft \
for a law firm's quality panel. Score it honestly and strictly — this is used to decide \
whether the tool is fit to put in front of practising lawyers.

Score each dimension 0-10:

- format: Does it follow Indian drafting convention for this instrument? A legal notice \
needs an advocate's letterhead/reference block, numbered recitals opening "That ...", a \
distinct "NOW THEREFORE" operative demand, and a closing "TAKE NOTICE" clause. A document \
that reads like a generic business letter with headings such as "TITLE OF THE NOTICE" or \
"SENDER'S DETAILS" scores 3 or below, however fluent its prose.
- statute_accuracy: Are the statutes cited actually applicable? Citing criminal law \
(BNS/BNSS/BSA/IPC/CrPC) in a civil, contractual or testamentary matter is a substantive \
legal error and scores 0 for this dimension. Confidently asserting a section number that \
does not exist also scores 0.
- completeness: Are all required clauses present, and does the document end properly \
rather than mid-sentence?
- instruction_compliance: Did it do what it was told, including any express ratio, amount, \
deadline, or request to state assumptions and identify legal issues? Silently dropping an \
express instruction is a serious failure.
- drafting_quality: Precision of operative language, internal consistency, absence of \
invented facts, appropriate contingency planning.

An advisory notes section is a strength ONLY if its statements are legally correct; \
penalise confident but wrong advisory notes as heavily as a wrong citation in the body.

Respond with ONLY this JSON, no other text:
{"format": <0-10>, "statute_accuracy": <0-10>, "completeness": <0-10>,
 "instruction_compliance": <0-10>, "drafting_quality": <0-10>, "overall": <0-10>,
 "rationale": "<3-4 sentences naming the specific defects you found>"}"""

_JUDGE_KEYS = ('format', 'statute_accuracy', 'completeness',
               'instruction_compliance', 'drafting_quality', 'overall')


def score_judge(draft: ParsedDraft, case: GoldenCase) -> dict | None:
    """
    One model call against the rubric. Returns None if the call or parse fails —
    a judge outage must never take down a deterministic run.
    """
    from core.llm_client import chat_complete

    body = '\n\n'.join(
        f"SECTION: {s.get('section_name', '')}\n{C.strip_html(s.get('content') or '')}"
        for s in draft.sections
    )
    if draft.notes_text:
        body += f'\n\nADVISORY NOTES RETURNED:\n{draft.notes_text}'

    user = (
        f'THE INSTRUCTION GIVEN TO THE DRAFTER:\n{case.prompt}\n\n'
        f'--- THE DRAFT PRODUCED ---\n{body[:24000]}'
    )

    try:
        raw = chat_complete(
            messages=[{'role': 'system', 'content': _JUDGE_SYSTEM},
                      {'role': 'user', 'content': user}],
            app_scenario='brain:t3',
            temperature=0.0,
            max_tokens=800,
        )
    except Exception as exc:
        logger.warning('[evals.judge] %s: call failed: %s', case.id, exc)
        return None

    try:
        text = (raw or '').strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        payload = json.loads(m.group(0) if m else text)
    except Exception as exc:
        logger.warning('[evals.judge] %s: unparseable response: %s', case.id, exc)
        return None

    out = {}
    for k in _JUDGE_KEYS:
        try:
            out[k] = max(0.0, min(10.0, float(payload.get(k, 0))))
        except (TypeError, ValueError):
            out[k] = 0.0
    out['rationale'] = str(payload.get('rationale', ''))[:1200]
    return out
