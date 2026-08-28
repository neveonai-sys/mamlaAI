"""
Golden-case schema and loader.

A golden case is a prompt plus the things a competent Indian advocate would
insist on in the answer. Expectations are deliberately *structural* — phrases,
section names, forbidden statutes, express instructions — because those can be
asserted without a model in the loop and without arguing about style.

Fixtures live in `fixtures/*.yaml` so the legal team can edit expectations
without touching Python.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

FIXTURES_DIR = Path(__file__).parent / 'fixtures'

DEFAULT_RUBRIC_WEIGHTS = {
    'format': 0.30,
    'statute': 0.25,
    'completeness': 0.25,
    'compliance': 0.20,
}


@dataclass(frozen=True)
class ExpectSpec:
    """What the draft must and must not contain."""

    # Classification (asserted from Phase 1 onward; informational before that).
    doc_type: str = ''
    branch: str = ''

    # Structural conventions — the fix for defect #2. Scored as a checklist
    # fraction under `format`: does this read like the right kind of document.
    must_contain: tuple[str, ...] = ()
    must_contain_section_names: tuple[str, ...] = ()
    must_not_contain: tuple[str, ...] = ()

    # Load-bearing operative provisions, scored under `completeness` with a
    # heavy per-miss penalty.
    #
    # Kept separate from `must_contain` deliberately. A will that omits the
    # contingency for the wife predeceasing the testator is an INCOMPLETE
    # instrument, not a badly formatted one — and averaging that omission into
    # a checklist alongside "contains the word witness" dilutes it to nothing.
    # The baseline run scored 8.1 on exactly such a draft.
    must_contain_clauses: tuple[str, ...] = ()

    # Statute discipline — the fix for defect #1.
    forbid_penal_statutes: bool = True
    must_not_match: tuple[str, ...] = ()   # bespoke regexes, e.g. future-will revocation

    # Express instructions the draft must honour or explicitly flag — defect #3b.
    literals_from_prompt: tuple[str, ...] = ()

    # Completeness — defect #3a.
    min_sections: int = 5

    # Advisory output — defect #4.
    require_assumptions: bool = False
    require_drafting_notes: bool = False

    rubric_weights: dict = field(default_factory=lambda: dict(DEFAULT_RUBRIC_WEIGHTS))

    def __post_init__(self):
        for pattern in self.must_not_match:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f'must_not_match regex {pattern!r} does not compile: {exc}')
        total = sum(self.rubric_weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f'rubric_weights must sum to 1.0, got {total}')


@dataclass(frozen=True)
class GoldenCase:
    id: str
    prompt: str
    expect: ExpectSpec
    notes: str = ''
    language: str = 'English'

    @property
    def slug(self) -> str:
        return self.id


def _tup(value) -> tuple:
    """
    Normalise a YAML scalar-or-sequence into a tuple.

    Nested sequences are preserved as tuples, so `must_contain` entries can be
    lists of accepted alternatives (see `checks.find_missing_phrases`).
    """
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(tuple(v) if isinstance(v, (list, tuple)) else v for v in value)
    return (value,)


def load_case(path: Path) -> GoldenCase:
    raw = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    expect_raw = raw.get('expect') or {}

    weights = expect_raw.get('rubric_weights') or dict(DEFAULT_RUBRIC_WEIGHTS)

    expect = ExpectSpec(
        doc_type=expect_raw.get('doc_type', '') or '',
        branch=expect_raw.get('branch', '') or '',
        must_contain=_tup(expect_raw.get('must_contain')),
        must_contain_section_names=_tup(expect_raw.get('must_contain_section_names')),
        must_not_contain=_tup(expect_raw.get('must_not_contain')),
        must_contain_clauses=_tup(expect_raw.get('must_contain_clauses')),
        forbid_penal_statutes=bool(expect_raw.get('forbid_penal_statutes', True)),
        must_not_match=_tup(expect_raw.get('must_not_match')),
        literals_from_prompt=_tup(expect_raw.get('literals_from_prompt')),
        min_sections=int(expect_raw.get('min_sections', 5)),
        require_assumptions=bool(expect_raw.get('require_assumptions', False)),
        require_drafting_notes=bool(expect_raw.get('require_drafting_notes', False)),
        rubric_weights=dict(weights),
    )

    case_id = raw.get('id') or path.stem
    prompt = (raw.get('prompt') or '').strip()
    if not prompt:
        raise ValueError(f'{path.name}: golden case has no prompt')

    return GoldenCase(
        id=case_id,
        prompt=prompt,
        expect=expect,
        notes=(raw.get('notes') or '').strip(),
        language=raw.get('language') or 'English',
    )


def load_suite(ids: tuple[str, ...] = ()) -> list[GoldenCase]:
    """Load every fixture, or just the ids given. Sorted by filename."""
    cases = [load_case(p) for p in sorted(FIXTURES_DIR.glob('*.yaml'))]
    if ids:
        wanted = set(ids)
        cases = [c for c in cases if c.id in wanted or c.id.split('_')[0] in wanted]
    return cases
