"""
Parse, repair and validate a generated draft.

Two jobs, in order:

1.  **Get a document out of the response at all.** `parse_draft_payload` is a
    repair ladder. Before Phase 2 a single stray character discarded the entire
    draft (`return []` -> empty session -> perpetual spinner), and Phase 1 found
    three separate real-world responses that hit exactly that: a truncated
    response whose ``` fence never closed, a raw newline inside a clause string,
    and a complete Will preceded by two paragraphs of prose. Each rung below is
    a defect that actually occurred, not a hypothetical.

2.  **Say what is wrong with it.** `validate` runs the deterministic checks in
    `checks.py` — the same functions the eval rubric scores with, so what guards
    production is what the golden set measures — and returns findings the caller
    turns into one correction turn.

The module is pure: no Mongo, no Django, no LLM. `generate_draft` owns the
retry policy; this owns the verdict.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import checks
from .classify import DraftContext

# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

ERROR = 'error'
WARNING = 'warning'


@dataclass(frozen=True)
class Finding:
    """One thing wrong with a draft.

    `code` is stable and machine-readable (the evals group on it). `message` is
    written to be pasted verbatim into a correction turn — it names the defect
    and what to do, because "your draft has a statute_misuse finding" does not
    tell a model what to change.
    """
    code: str
    severity: str
    message: str
    section_name: str = ''

    @property
    def is_error(self) -> bool:
        return self.severity == ERROR


@dataclass
class DraftResult:
    """The outcome of parsing and validating one generation."""
    sections: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    drafting_notes: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    #: which rung of the repair ladder produced `sections` ('' when clean)
    repaired: str = ''
    #: nothing usable came back — no sections at all
    fatal: bool = False
    #: the schema the model actually answered in: 'advisory' | 'legacy'
    schema: str = 'legacy'

    @property
    def errors(self) -> list:
        return [f for f in self.findings if f.is_error]

    @property
    def warnings(self) -> list:
        return [f for f in self.findings if not f.is_error]

    def summary(self) -> str:
        """One line for the structured production log."""
        codes = ','.join(sorted({f.code for f in self.findings})) or 'clean'
        return (f'sections={len(self.sections)} assumptions={len(self.assumptions)} '
                f'notes={len(self.drafting_notes)} repaired={self.repaired or "no"} '
                f'fatal={self.fatal} findings={codes}')


# ---------------------------------------------------------------------------
# The repair ladder
#
# Every rung is tried in order and the first that yields a list of sections
# wins. `repaired` records which one, so the production log distinguishes "the
# model returned clean JSON" from "we salvaged a truncated response" — the
# second is a prompt or token-budget problem worth seeing in aggregate.
# ---------------------------------------------------------------------------

_FENCE_OPEN_RE = re.compile(r'^\s*```[a-zA-Z0-9_-]*\s*\n?')
_FENCE_CLOSE_RE = re.compile(r'\n?\s*```\s*$')

#: `"key": "value",}` and `[1,2,]` — models emit these under length pressure.
_TRAILING_COMMA_RE = re.compile(r',(\s*[}\]])')

_SMART_QUOTES = {
    '“': '"', '”': '"', '„': '"',
    '‘': "'", '’': "'", '‚': "'",
}


def _strip_fences(text: str) -> str:
    """Remove a markdown fence at either end, independently.

    Independence matters: a response truncated mid-array opens its fence and
    never closes it. The pre-Phase-2 check required both ends to match and so
    failed on precisely the responses that most needed recovering.
    """
    out = _FENCE_OPEN_RE.sub('', text or '')
    out = _FENCE_CLOSE_RE.sub('', out)
    return out.strip()


def _normalise_punctuation(text: str) -> str:
    """Straighten smart quotes used as JSON syntax and drop trailing commas.

    Only touches quotes that a model substituted for JSON's own delimiters;
    curly quotes *inside* clause text are legitimate and are left alone by
    running this rung last, on a string that has already failed to parse.
    """
    out = text
    for bad, good in _SMART_QUOTES.items():
        out = out.replace(bad, good)
    return _TRAILING_COMMA_RE.sub(r'\1', out)


def _scan_balanced(text: str, opener: str, closer: str) -> str | None:
    """Return the first balanced `opener…closer` span, respecting string literals.

    A naive `find('[') … rfind(']')` breaks on a clause that contains a bracket
    — "[PROPERTY ADDRESS]" appears in almost every draft we produce — so the
    scanner tracks whether it is inside a JSON string and skips escaped
    characters.
    """
    start = text.find(opener)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _balanced_spans(text: str) -> list[str]:
    """Balanced JSON spans embedded in prose, outermost container first.

    Ordered by which delimiter actually opens first, not by a fixed preference.
    An advisory object must be tried before the `sections` array nested inside
    it, or the advisories are silently discarded — but a legacy top-level array
    must be tried before its own first element object, or the draft is reduced
    to one section. Only the position in the text distinguishes the two cases.
    """
    found: list[tuple[int, str | None]] = []
    for opener, closer in (('{', '}'), ('[', ']')):
        idx = text.find(opener)
        if idx != -1:
            found.append((idx, _scan_balanced(text, opener, closer)))
    found.sort(key=lambda pair: pair[0])

    spans: list[str] = []
    for _idx, span in found:
        if span is None:
            # The outermost container opened and never closed: the response was
            # cut off. Anything nested inside it is a fragment, not an embedded
            # payload — returning the first complete element here would hand
            # back a one-section draft and stop the truncation salvage rung from
            # ever running, which is the rung that recovers the rest.
            break
        if span != text:
            spans.append(span)
    return spans


def _salvage_truncated(text: str) -> str | None:
    """Rewind a cut-off response to its last complete section object.

    This is the rung that converts total loss into a partial draft. The model
    stopped mid-clause; everything before the last complete `}` is intact and
    usable, so close the containers by hand and parse that. The caller flags the
    result as truncated, so the user sees a short draft with a warning rather
    than an empty one with a spinner.
    """
    last = text.rfind('}')
    if last == -1:
        return None
    head = text[:last + 1]

    # Drop a partial object the model had started after the last complete one.
    trailing = head.rfind('{')
    if trailing > head.rfind('}'):
        head = head[:trailing].rstrip().rstrip(',')

    head = head.rstrip().rstrip(',')

    # Close whatever is still open, outermost last.
    stack: list[str] = []
    in_string = False
    escaped = False
    for ch in head:
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in '[{':
            stack.append(ch)
        elif ch in ']}' and stack:
            stack.pop()

    if in_string:
        head += '"'
    for opener in reversed(stack):
        head += ']' if opener == '[' else '}'
    return head


def _loads(text: str):
    # strict=False tolerates literal newlines and tabs inside string values.
    # Legal clause content is inherently multi-line and models routinely emit a
    # raw newline where the spec wants \n; strict parsing discarded an otherwise
    # complete and correct Will over one such character.
    return json.loads(text, strict=False)


def _coerce_payload(parsed):
    """Accept either schema, and reject anything that is neither.

    Returns `(sections, assumptions, drafting_notes, schema)` or None.
    Backward compatibility lives here and nowhere else: the legacy top-level
    array and the Phase 2 advisory object both reduce to the same tuple, so no
    storage or read path needs to know which one the model answered in.
    """
    if isinstance(parsed, list):
        return parsed, [], [], 'legacy'

    if isinstance(parsed, dict):
        sections = parsed.get('sections')
        if isinstance(sections, list):
            return (
                sections,
                _as_list(parsed.get('assumptions')),
                _as_list(parsed.get('drafting_notes')),
                'advisory',
            )
        # A single bare section object, which some responses degrade to.
        if 'section_name' in parsed and 'content' in parsed:
            return [parsed], [], [], 'legacy'
    return None


def _as_list(value) -> list:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return []


def _clean_sections(raw) -> list:
    """Keep the well-formed sections and drop the rest.

    Deliberately lenient about extra keys and about `content` arriving as a
    number or a list of paragraphs — a section with a usable name and body is
    worth keeping even when the model decorated it. Deliberately strict about
    the two keys the storage and render paths require.
    """
    out = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        name = item.get('section_name') or item.get('name') or item.get('title')
        content = item.get('content')
        if isinstance(content, list):
            content = '\n'.join(str(c) for c in content if c is not None)
        if content is not None and not isinstance(content, str):
            content = str(content)
        if not name or not (content or '').strip():
            continue
        section = dict(item)
        section['section_name'] = str(name).strip()
        section['content'] = content
        section.pop('name', None)
        section.pop('title', None)
        out.append(section)
    return out


def parse_draft_payload(raw_content) -> DraftResult:
    """Turn a raw model response into sections + advisories, repairing as needed.

    Never raises. A `DraftResult` with `fatal=True` and an explanatory finding
    is the failure mode — the caller writes `status='failed'` from it, which is
    what stops the perpetual spinner.
    """
    result = DraftResult()

    if raw_content is None or not str(raw_content).strip():
        result.fatal = True
        result.findings.append(Finding(
            code='empty_response',
            severity=ERROR,
            message=(
                'The model returned no content. On a reasoning model this usually '
                'means the entire token budget went to reasoning; check '
                'finish_reason and the reasoning-token setting.'
            ),
        ))
        return result

    text = _strip_fences(str(raw_content).strip())
    if not text:
        result.fatal = True
        result.findings.append(Finding(
            code='empty_response', severity=ERROR,
            message='The response contained only a markdown fence and no JSON.',
        ))
        return result

    # Rung 1 — it parses as-is.
    attempts: list[tuple[str, str]] = [('', text)]

    # Rung 2 — a balanced object or array embedded in prose.
    attempts.extend(('extracted_from_prose', s) for s in _balanced_spans(text))

    # Rung 3 — smart quotes and trailing commas.
    normalised = _normalise_punctuation(text)
    if normalised != text:
        attempts.append(('normalised_punctuation', normalised))
        attempts.extend(('normalised_punctuation', s) for s in _balanced_spans(normalised))

    # Rung 4 — truncation salvage, last because it is lossy by construction.
    for candidate in (text, normalised):
        salvaged = _salvage_truncated(candidate)
        if salvaged and salvaged != candidate:
            attempts.append(('truncation_salvage', salvaged))

    last_error = ''
    for label, candidate in attempts:
        try:
            parsed = _loads(candidate)
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = str(exc)
            continue

        coerced = _coerce_payload(parsed)
        if coerced is None:
            last_error = f'parsed as {type(parsed).__name__}, not a draft payload'
            continue

        raw_sections, assumptions, notes, schema = coerced
        sections = _clean_sections(raw_sections)
        if not sections:
            last_error = 'payload parsed but contained no well-formed sections'
            continue

        dropped = len(raw_sections) - len(sections)
        result.sections = sections
        result.assumptions = assumptions
        result.drafting_notes = notes
        result.schema = schema
        result.repaired = label

        if label == 'truncation_salvage':
            result.findings.append(Finding(
                code='truncation', severity=ERROR,
                message=(
                    'The response was cut off mid-document and was salvaged to the last '
                    'complete section. Re-draft the document completely, and keep every '
                    'clause to the two-to-four sentences an operative clause needs so '
                    'the whole skeleton fits.'
                ),
            ))
        elif label:
            result.findings.append(Finding(
                code='malformed_json', severity=WARNING,
                message=f'The response needed repair before it parsed ({label}).',
            ))
        if dropped > 0:
            result.findings.append(Finding(
                code='malformed_section', severity=WARNING,
                message=f'{dropped} element(s) were dropped for missing a name or body.',
            ))
        return result

    result.fatal = True
    result.findings.append(Finding(
        code='unparseable', severity=ERROR,
        message=(
            'The response could not be parsed as a draft after every repair attempt '
            f'({last_error}). Return ONLY the JSON described in the output format, '
            'with no prose before or after it.'
        ),
    ))
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _fmt_list(items, limit: int = 6) -> str:
    items = list(items)
    shown = '; '.join(str(i) for i in items[:limit])
    return shown + (f' (and {len(items) - limit} more)' if len(items) > limit else '')


def validate(
    result: DraftResult,
    ctx: DraftContext,
    *,
    user_query: str = '',
    finish_reason: str | None = None,
) -> DraftResult:
    """Run every deterministic check and append findings in place.

    Errors are the ones worth spending a correction turn on: a statute the
    branch forbids, a missing mandatory section, an express instruction dropped
    without a word. Warnings are recorded and logged but never block — a
    lowercase placeholder is not worth a second API call.
    """
    playbook = ctx.playbook
    sections = result.sections
    notes_text = _advisory_text(result)

    # --- defect #1: penal statutes in a non-criminal instrument --------------
    for hit in checks.find_statute_misuse(sections, playbook.deny_patterns, notes_text):
        result.findings.append(Finding(
            code='statute_misuse', severity=ERROR, section_name=hit.section_name,
            message=(
                f'"{hit.token}" appears in section "{hit.section_name}", but this is a '
                f'{ctx.branch} matter to which the penal codes have no application. '
                f'Remove it and every other reference to BNS, BNSS, BSA, IPC, CrPC or '
                f'the Indian Evidence Act. Offending text: "{hit.sentence}"'
            ),
        ))

    # --- defect #2: skeleton compliance -------------------------------------
    missing_sections = checks.find_missing_sections(sections, playbook.required_sections)
    if missing_sections:
        result.findings.append(Finding(
            code='missing_section', severity=ERROR,
            message=(
                f'These mandatory sections of a {playbook.label} are absent: '
                f'{_fmt_list(missing_sections)}. Add each one, under that exact name, '
                'in the position given in the skeleton.'
            ),
        ))

    missing_phrases = checks.find_missing_phrases(sections, playbook.required_phrases)
    if missing_phrases:
        result.findings.append(Finding(
            code='missing_phrase', severity=ERROR,
            message=(
                f'A {playbook.label} must contain: {_fmt_list(missing_phrases)}. '
                'These are structural conventions of Indian drafting, not stylistic '
                'preferences; a document without them does not read as lawyer-drafted.'
            ),
        ))

    if len(sections) < (playbook.min_sections or 0):
        result.findings.append(Finding(
            code='too_few_sections', severity=ERROR,
            message=(
                f'The draft has {len(sections)} sections; a {playbook.label} needs at '
                f'least {playbook.min_sections}. Draft the remaining sections of the '
                'skeleton.'
            ),
        ))

    # --- defect #3a: truncation ---------------------------------------------
    # Skip when the salvage rung already reported it; one finding per defect.
    if not any(f.code == 'truncation' for f in result.findings):
        for hit in checks.detect_truncation(sections, finish_reason):
            result.findings.append(Finding(
                code='truncation', severity=ERROR, section_name=hit.section_name,
                message=(
                    f'Section "{hit.section_name}" ends mid-thought ({hit.reason}): '
                    f'"...{hit.tail}". Complete it and every section after it.'
                ),
            ))

    # --- defect #3b: silently dropped instructions ---------------------------
    for lit in checks.find_dropped_literals(user_query, sections, notes_text):
        severity = ERROR if lit.confidence == 'high' else WARNING
        result.findings.append(Finding(
            code='instruction_dropped', severity=severity,
            message=(
                f'The instructions specified "{lit.raw}" ({lit.kind}), which appears '
                'nowhere in the draft. Either give it effect in the operative clause '
                'or record why you could not in the drafting notes. Dropping it '
                'silently is a defect.'
            ),
        ))

    # --- defect #4: advisories ----------------------------------------------
    # Warnings only. The model is being asked for professional judgement, and a
    # correction turn spent demanding an assumptions list on a draft that
    # genuinely needed no assumptions would be worse than the omission.
    if result.schema == 'advisory':
        if not result.assumptions and _has_placeholders(sections):
            result.findings.append(Finding(
                code='advisory_missing', severity=WARNING,
                message=(
                    'The draft carries placeholders for facts that were not supplied '
                    'but records no assumptions.'
                ),
            ))
        if not result.drafting_notes:
            result.findings.append(Finding(
                code='advisory_missing', severity=WARNING,
                message='The draft records no drafting notes.',
            ))

    # --- placeholders --------------------------------------------------------
    report = checks.inspect_placeholders(sections)
    if report.lowercase:
        result.findings.append(Finding(
            code='placeholder', severity=WARNING,
            message=(
                f'Placeholders must be ALL CAPS so they are visually obvious in the '
                f'draft: {_fmt_list(report.lowercase)}'
            ),
        ))

    return result


def _has_placeholders(sections) -> bool:
    return bool(checks.inspect_placeholders(sections).tokens)


def _advisory_text(result: DraftResult) -> str:
    """Flatten assumptions and notes so the checks can sweep them as text.

    A note that *recommends* citing the BNSS in a civil matter is as wrong as a
    section that does, and an instruction flagged in the notes counts as
    honoured — both require the advisories to be visible to `checks`.
    """
    parts: list[str] = []
    for a in result.assumptions or []:
        parts.extend(str(a.get(k, '')) for k in ('assumption', 'why'))
    for n in result.drafting_notes or []:
        parts.extend(str(n.get(k, '')) for k in ('issue', 'recommendation'))
    return '\n'.join(p for p in parts if p)


def build_correction_message(result: DraftResult, ctx: DraftContext) -> str:
    """The user-turn for the single correction call.

    Names the specific defects rather than asking for a general improvement.
    "You cited BNSS in a civil rent matter — remove every penal-code reference"
    is actionable; "please improve the draft" invites a rewrite that loses the
    parts that were already right.
    """
    errors = result.errors
    lines = [
        f'The {ctx.playbook.label} you produced has defects that must be corrected '
        'before it can be served or filed:',
        '',
    ]
    lines.extend(f'{i}. {f.message}' for i, f in enumerate(errors, 1))
    lines.extend([
        '',
        'Return the COMPLETE corrected document in the same output format. Keep '
        'everything that was already correct — do not re-word or re-order sections '
        'that are not named above.',
    ])
    return '\n'.join(lines)
