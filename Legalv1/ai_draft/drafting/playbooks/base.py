"""
Playbook data model.

A playbook is the per-document-type legal specification that the generic prompt
never had: which sections an instrument must carry, in what order, in what
register, citing which statutes — and, critically, which statutes it must NOT
cite.

Two properties matter more than anything else here:

1. `skeleton[].must_contain` turns defect #2 from a hope into an assertion. The
   prompt asks for `NOW THEREFORE`; the validator then *checks* for it against
   this same tuple. Prompt and linter read the same source, so they cannot drift.

2. `branch` drives the statute gate. Eleven of the twelve types are
   civil/commercial/testamentary, where BNS/BNSS/BSA have no application at all.
   For those, `deny_patterns` is non-empty and the prompt carries an explicit
   negative instruction — which is the whole fix for defect #1.

Nothing here does I/O or imports Django, so playbooks stay unit-testable and
cheap to import from a management command.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..checks import PENAL_TOKEN_PATTERNS

# --- Legal branches ---------------------------------------------------------
# `criminal` is the ONLY branch permitted to cite the penal codes. Everything
# else gets the negative statute instruction.
CIVIL = 'civil'
CRIMINAL = 'criminal'
COMMERCIAL = 'commercial'
TESTAMENTARY = 'testamentary'
FAMILY = 'family'
CONSTITUTIONAL = 'constitutional'
UNKNOWN = 'unknown'

BRANCHES = frozenset({
    CIVIL, CRIMINAL, COMMERCIAL, TESTAMENTARY, FAMILY, CONSTITUTIONAL, UNKNOWN,
})

#: Branches for which penal-code citations are a defect, not a style choice.
NON_PENAL_BRANCHES = frozenset({CIVIL, COMMERCIAL, TESTAMENTARY, FAMILY})


@dataclass(frozen=True)
class Section:
    """One mandated section of an instrument."""

    name: str
    guidance: str = ''
    #: Phrases the section's content must carry. Accepts a nested tuple of
    #: alternatives, matching `checks.find_missing_phrases` semantics — e.g.
    #: `(('NOW THEREFORE', 'call upon you'),)` is satisfied by either.
    must_contain: tuple = ()
    required: bool = True


@dataclass(frozen=True)
class Playbook:
    doc_type: str
    label: str
    branch: str
    category: str

    #: Exact type hints the frontend/chat may send. Matched case-insensitively
    #: after normalisation; must be unique across the whole registry.
    aliases: tuple[str, ...] = ()

    #: `(regex, weight)` scored against the user's query. Weights are relative;
    #: sub-variants should outweigh their parent (a rent-arrears notice must beat
    #: the generic demand notice on "arrears of rent").
    keywords: tuple[tuple[str, int], ...] = ()

    skeleton: tuple[Section, ...] = ()
    conventions: tuple[str, ...] = ()

    #: Statutes this instrument may cite. Rendered into the prompt as a closed
    #: list; anything outside it must be named in words and marked
    #: "(exact section to be confirmed)".
    statutes_allow: tuple[str, ...] = ()

    #: Reviewer-sourced defects, injected under `AVOID THESE SPECIFIC DEFECTS`.
    pitfalls: tuple[str, ...] = ()

    #: Facts the drafter must have. Absent ones become `assumptions`, never
    #: invented values.
    required_facts: tuple[str, ...] = ()

    #: `draft_type` folder names in the corpus this type may retrieve from
    #: (Phase 4 / §10.5). Empty means "no corpus coverage" — see `inline_exemplar`.
    kb_doc_types: tuple[str, ...] = ()

    #: Hand-authored worked example, used when the corpus has no precedent.
    #: Legal work product: carries the same advocate sign-off gate as the
    #: playbook itself.
    inline_exemplar: str = ''

    min_sections: int = 5
    target_tokens: int = 6000

    def __post_init__(self):
        if self.branch not in BRANCHES:
            raise ValueError(f'{self.doc_type}: unknown branch {self.branch!r}')
        if not self.skeleton:
            raise ValueError(f'{self.doc_type}: skeleton is empty')
        if not any(s.required for s in self.skeleton):
            raise ValueError(f'{self.doc_type}: no required sections')
        for pattern, _weight in self.keywords:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f'{self.doc_type}: keyword {pattern!r} does not compile: {exc}')

    # -- derived ------------------------------------------------------------

    @property
    def deny_patterns(self) -> tuple[tuple[str, str], ...]:
        """
        Penal-token deny list for this type.

        Empty for `criminal` (where the codes belong) and for `unknown` (where we
        cannot assert enough to forbid). Non-empty everywhere else — that tuple
        is what `find_statute_misuse` enforces and what the prompt states as a
        negative.
        """
        if self.branch in NON_PENAL_BRANCHES:
            return PENAL_TOKEN_PATTERNS
        return ()

    @property
    def required_sections(self) -> tuple[str, ...]:
        return tuple(s.name for s in self.skeleton if s.required)

    @property
    def required_phrases(self) -> tuple:
        """Flattened `must_contain` across required sections, for the validator."""
        out: list = []
        for section in self.skeleton:
            if section.required:
                out.extend(section.must_contain)
        return tuple(out)

    def score(self, text: str) -> int:
        """Summed weight of every keyword pattern present in `text`."""
        if not text:
            return 0
        return sum(
            weight for pattern, weight in self.keywords
            if re.search(pattern, text, re.IGNORECASE)
        )
