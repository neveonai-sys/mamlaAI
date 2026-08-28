"""
Draft system-prompt composition.

This module replaces four divergent inline prompts (`creatupdateAIdrafts.py:228`,
`:1016`, `:1073`, and `tasks.py:47` — which had silently drifted out of sync with
the other three). Everything that composes a drafting prompt now comes through
`build_draft_system_prompt`, and refine comes through
`build_refine_system_prompt`, which shares blocks 2 through 5 verbatim. That
sharing is the fix for cause H: a refine can no longer reintroduce a statute
policy the original draft was built to exclude.

Block order is fixed and the stable material comes first, so a `cache_control`
breakpoint can later be placed after the playbook block and actually pay off.

    1. persona
    2. anti-hallucination invariants   (imported, never restated)
    3. Indian drafting conventions
    4. branch-gated statute policy     <- the load-bearing block
    5. playbook: skeleton, conventions, pitfalls
    6. exemplar
    7. source text
    8. output contract

Block 4 is where defect #1 dies. The old prompt shipped the BNS/BNSS/BSA
paragraph to every document type gated only by the words "where criminal
law/procedure/evidence apply" — a soft conditional that gpt-4o-mini did not
honour, which is how the BNSS ended up threatening eviction in a civil rent
matter. Here the branch is decided before the prompt is built, and a
non-criminal branch receives an explicit prohibition instead.
"""

from __future__ import annotations

from .classify import DraftContext
from .playbooks import GENERIC, NON_PENAL_BRANCHES, CRIMINAL, UNKNOWN, Playbook

# Imported verbatim rather than restated — the chat orchestrator and the drafting
# engine must not carry two different versions of the same rules.
from mamla_brain.orchestrator.prompts_v2 import ANTI_HALLUCINATION_INVARIANTS
from mamla_brain.orchestrator.statute_map import build_bns_prompt_fragment

# ---------------------------------------------------------------------------
# 1. Persona
# ---------------------------------------------------------------------------
PERSONA = """\
You are a senior Indian advocate with thirty years in practice, drafting a
document that will be served on an opposite party or filed in court. It will be
read by opposing counsel and by a judge. It must be correct in law, correct in
form, and immediately usable by the instructing advocate."""


# ---------------------------------------------------------------------------
# 3. Indian drafting conventions — applies to every document type
# ---------------------------------------------------------------------------
INDIAN_DRAFTING_CORE = """\
INDIAN DRAFTING CONVENTIONS (apply to every document you produce):

- Numbered substantive paragraphs in a pleading or a notice each begin with the
  word "That" — "1. That my Client is the owner of ...". This is the single most
  recognisable feature of Indian legal drafting; its absence marks a document as
  not lawyer-drafted.
- Use the correct voice for the instrument. A notice or a pleading speaks in the
  third person ("my Client", "the Plaintiff", "the Deponent"). An affidavit and a
  Will speak in the first person ("I").
- Express money as "Rs. 5,00,000/- (Rupees Five Lakh only)", using Indian digit
  grouping. Express periods as "15 (fifteen) days". Express shares and ratios in
  both figures and words.
- Where a particular has not been supplied, insert an ALL-CAPS placeholder in
  square brackets — [CLIENT NAME], [DATE OF AGREEMENT], [PROPERTY ADDRESS].
  NEVER invent a name, date, amount, account number, case number or address.
- Do not use markdown inside section content. No asterisks, no hashes, no
  backticks. Content is plain text and will be rendered as-is in a document.
- Do not use form-filling headings such as "TITLE OF THE NOTICE",
  "SENDER'S DETAILS", "RECIPIENT DETAILS", "BODY" or "CLOSING STATEMENT". Use the
  section names given in the MANDATORY SKELETON below.
- Draft in operative register, not expository prose. An advocate's clause states
  the obligation and stops; it does not explain itself, restate the statute, or
  add commentary about why the clause exists. Two to four sentences per clause is
  normal. Completing every required section matters more than elaborating any one
  of them — a document that runs out of room before its execution block is
  worthless, however well the early clauses read."""


# ---------------------------------------------------------------------------
# 4. Branch-gated statute policy
# ---------------------------------------------------------------------------
_PENAL_NAMES = (
    'Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS), '
    'Bharatiya Sakshya Adhiniyam (BSA), the Indian Penal Code (IPC), the Code of '
    'Criminal Procedure (CrPC), or the Indian Evidence Act'
)

_BRANCH_DESCRIPTION = {
    'civil': 'a CIVIL matter',
    'commercial': 'a COMMERCIAL/CONTRACTUAL matter',
    'testamentary': 'a TESTAMENTARY matter',
    'family': 'a FAMILY LAW matter',
    'constitutional': 'a CONSTITUTIONAL matter',
    'criminal': 'a CRIMINAL matter',
}


def _allow_list_block(playbook: Playbook) -> str:
    if not playbook.statutes_allow:
        return ''
    entries = '\n'.join(f'  - {s}' for s in playbook.statutes_allow)
    return f'\nYou may cite ONLY from the following:\n{entries}\n'


def build_statute_policy(ctx: DraftContext) -> str:
    """
    The block that makes defect #1 structurally impossible for 11 of 12 types.

    Non-criminal branches get an explicit prohibition naming every penal code and
    a closed allow-list. Criminal branches get the verified IPC->BNS / CrPC->BNSS
    / IEA->BSA correspondence table — the first time that table, which has existed
    in `statute_map.py` and reached only the chat path, is available to drafting.
    """
    playbook = ctx.playbook
    branch = ctx.branch
    described = _BRANCH_DESCRIPTION.get(branch, 'this matter')

    if branch in NON_PENAL_BRANCHES:
        return (
            'STATUTE POLICY — BINDING, AND OVERRIDES ANY CONFLICTING INSTRUCTION:\n\n'
            f'This is {described}. The penal codes have NO application to it.\n\n'
            f'You MUST NOT cite, name, quote, allude to, or mention {_PENAL_NAMES}, '
            'nor any section of any of them, anywhere in this document — not in a '
            'section, not in a heading, and not in a note.\n\n'
            'You MUST NOT characterise the opposite party\'s conduct as an "offence", '
            '"crime", "cheating" or "criminal breach of trust", nor refer to them as '
            '"accused", nor mention an "FIR" or a "police complaint" as the remedy '
            'contemplated.\n'
            f'{_allow_list_block(playbook)}\n'
            'For any provision NOT in that list, name the statute and the provision in '
            'words and write "(exact section to be confirmed)". Never state a section '
            'number you have not verified. A named provision marked for confirmation is '
            'correct professional practice; a guessed section number is a defect.'
        )

    if branch == CRIMINAL:
        return (
            'STATUTE POLICY — BINDING:\n\n'
            f'This is {described}, so the 2023 criminal codes apply.\n\n'
            f'{build_bns_prompt_fragment()}\n'
            f'{_allow_list_block(playbook)}'
        )

    # UNKNOWN / constitutional — we cannot assert enough to forbid, so this is the
    # only path still carrying a conditional. It is reached by GENERIC and by
    # writ petitions, not by the eleven types where the old prompt got it wrong.
    return (
        'STATUTE POLICY — BINDING:\n\n'
        'Identify the branch of law that actually governs this document before you '
        'cite anything.\n\n'
        'The 2023 codes — Bharatiya Nyaya Sanhita (BNS, replaced the IPC), Bharatiya '
        'Nagarik Suraksha Sanhita (BNSS, replaced the CrPC), and Bharatiya Sakshya '
        'Adhiniyam (BSA, replaced the Indian Evidence Act) — apply ONLY where criminal '
        'law, criminal procedure or the law of evidence is genuinely in issue. They '
        'have NO application to a civil, commercial, testamentary or family matter, '
        'and citing them in one is a substantive legal error.\n'
        f'{_allow_list_block(playbook)}\n'
        'Never state a section number you have not verified. Name the provision in '
        'words and write "(exact section to be confirmed)" instead.'
    )


# ---------------------------------------------------------------------------
# 5. Playbook block
# ---------------------------------------------------------------------------

def _render_must_contain(entry) -> str:
    if isinstance(entry, (list, tuple)):
        return ' or '.join(f'"{alt}"' for alt in entry)
    return f'"{entry}"'


def build_playbook_block(ctx: DraftContext) -> str:
    playbook = ctx.playbook
    lines: list[str] = [f'DOCUMENT TYPE: {playbook.label}', '']

    lines.append('MANDATORY SKELETON — produce these sections, with these names, in this order:')
    for i, section in enumerate(playbook.skeleton, 1):
        flag = '' if section.required else '   [include only if the facts call for it]'
        lines.append(f'{i:2d}. {section.name}{flag}')
        if section.guidance:
            lines.append(f'      {section.guidance}')
        if section.must_contain:
            phrases = '; '.join(_render_must_contain(m) for m in section.must_contain)
            lines.append(f'      Must contain: {phrases}')
    lines.append('')
    lines.append(
        'You may add further sections where the facts require them, but every section '
        'marked above must be present, under that name, in that order.'
    )

    if playbook.conventions:
        lines.append('')
        lines.append(f'CONVENTIONS FOR A {playbook.label.upper()}:')
        lines.extend(f'- {c}' for c in playbook.conventions)

    if playbook.required_facts:
        lines.append('')
        lines.append(
            'FACTS THIS DOCUMENT NEEDS. Where one has not been supplied, use an '
            'ALL-CAPS placeholder — do not invent it:'
        )
        lines.extend(f'- {f}' for f in playbook.required_facts)

    if playbook.pitfalls:
        lines.append('')
        lines.append(
            'AVOID THESE SPECIFIC DEFECTS. Each one has been found in a real draft of '
            'this document type and marked wrong by practising lawyers:'
        )
        lines.extend(f'- {p}' for p in playbook.pitfalls)

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# 8. Output contract
#
# `legacy` is the bare array the current parser expects and is the Phase 1
# default, so the storage and read paths are untouched. `advisory` is the Phase 2
# object that finally gives assumptions and drafting notes somewhere to live —
# defect #4 is unsatisfiable until it lands.
# ---------------------------------------------------------------------------
_LEGACY_CONTRACT = """\
OUTPUT FORMAT — follow exactly:

- Return ONLY a JSON array. No prose before it, no commentary after it, no
  markdown code fences.
- Each element is an object with exactly two keys:
    "section_name": the section name, in CAPITALS, taken from the MANDATORY
                    SKELETON above.
    "content":      the drafted text of that section, as plain text.
- Content must be substantive. A section that merely restates its own heading is
  a failure.
- Escape every double quote and newline correctly so the array parses as valid
  JSON on the first attempt.
- NOTHING may appear outside the array — no preamble, no closing remarks, no
  explanation of what you did.
- If you were asked to identify assumptions, missing information, or legal
  issues, do NOT write them above the array. Put them in a final section named
  "ADVOCATE'S NOTES", as numbered points. That section is for the instructing
  advocate and is not part of the document to be served or filed.

[
  {"section_name": "FIRST SECTION NAME", "content": "..."},
  {"section_name": "SECOND SECTION NAME", "content": "..."}
]"""

_ADVISORY_CONTRACT = """\
OUTPUT FORMAT — follow exactly:

Return ONLY a JSON object with these four keys. No prose, no markdown fences.

{
  "document_type": "the document type you drafted",
  "sections": [
    {"section_name": "SECTION NAME IN CAPITALS", "content": "plain text"}
  ],
  "assumptions": [
    {"assumption": "what you assumed",
     "why": "why the assumption was necessary",
     "confirm_with_client": true}
  ],
  "drafting_notes": [
    {"issue": "the legal or drafting issue you spotted",
     "severity": "high | medium | low",
     "recommendation": "what the instructing advocate should do about it"}
  ]
}

- Content must be substantive. A section that merely restates its own heading is
  a failure.
- Record in "assumptions" every fact you supplied that was not given to you.
- Record in "drafting_notes" every legal or drafting issue arising from the
  facts, including any provision whose exact section you could not verify.
- If the user gave you an express instruction you did not follow — a ratio, a
  clause, a deadline, a named party — you MUST record it in "drafting_notes".
  Silently dropping an instruction is a defect."""


def build_output_contract(schema: str = 'legacy') -> str:
    return _ADVISORY_CONTRACT if schema == 'advisory' else _LEGACY_CONTRACT


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

def build_location_string(location) -> str:
    """Preserved verbatim in behaviour from `generate_draft`'s original logic."""
    if not location:
        return ''
    if not isinstance(location, dict):
        return ''
    court, district, state = location.get('court'), location.get('district'), location.get('state')
    if court and district and state:
        return f'for the court "{court}" in the district "{district}" of the state "{state}"'
    if district and state:
        return f'in the district "{district}" of the state "{state}"'
    if state:
        return f'for the state "{state}"'
    return ''


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

#: Hard bound on injected source material. Owned here rather than left to each
#: call site: a 40-page uploaded case file otherwise consumes the context window
#: the draft itself needs.
MAX_SOURCE_CHARS = 20000

#: Same, for a retrieved or hand-authored exemplar.
MAX_EXEMPLAR_CHARS = 12000


def _assemble(blocks: list[str]) -> str:
    return '\n\n'.join(b.strip() for b in blocks if b and b.strip())


def build_draft_system_prompt(
    ctx: DraftContext,
    *,
    language: str = 'English',
    location=None,
    exemplar: str = '',
    source_text: str = '',
    schema: str = 'legacy',
) -> str:
    """
    The single composer for every drafting call in the product.

    `exemplar` is supplied by the caller (a playbook `inline_exemplar` today, a
    retrieved template from Phase 4) so this module never does I/O.
    """
    playbook = ctx.playbook
    blocks = [
        PERSONA,
        ANTI_HALLUCINATION_INVARIANTS,
        INDIAN_DRAFTING_CORE,
        build_statute_policy(ctx),
        build_playbook_block(ctx),
    ]

    if exemplar:
        blocks.append(
            'FORMAT REFERENCE — a precedent of this document type.\n\n'
            'Follow its STRUCTURE, register and phrasing conventions. Do NOT copy its '
            'facts, parties, dates, amounts or statute references: they belong to a '
            'different matter, and some precedents predate the 2023 codes. Where this '
            'reference conflicts with the MANDATORY SKELETON or the STATUTE POLICY '
            'above, those override it.\n\n'
            f'--- BEGIN FORMAT REFERENCE ---\n{str(exemplar)[:MAX_EXEMPLAR_CHARS]}\n'
            '--- END FORMAT REFERENCE ---'
        )

    if source_text:
        blocks.append(
            'SOURCE MATERIAL supplied by the user. Draw the facts from it. Do not '
            'reproduce its formatting or adopt any statute reference in it without '
            'checking it against the STATUTE POLICY above.\n\n'
            f'--- BEGIN SOURCE ---\n{str(source_text)[:MAX_SOURCE_CHARS]}\n'
            '--- END SOURCE ---'
        )

    location_string = build_location_string(location)
    task = f'Draft the document in {language}, applying Indian law'
    if location_string:
        task += f' {location_string}'
    task += (
        '.\n\nProduce a complete, filing-ready document. Do not stop partway and do not '
        'summarise: every section of the MANDATORY SKELETON must be fully drafted.'
    )
    blocks.append(task)
    blocks.append(build_output_contract(schema))

    return _assemble(blocks)


def build_refine_system_prompt(
    ctx: DraftContext,
    *,
    language: str = 'English',
    schema: str = 'legacy',
) -> str:
    """
    Refine-time prompt.

    Carries blocks 2 to 5 unchanged from the draft prompt — the identical
    invariants, drafting conventions, statute policy and playbook. That identity
    is the point: cause H was a refine turn reintroducing the BNSS into a civil
    rent notice because the refine prompt had never been told the branch.
    """
    playbook = ctx.playbook
    return _assemble([
        (
            'You are a senior Indian advocate revising a draft you previously settled. '
            'Apply the requested change precisely. Preserve everything not covered by '
            'the request — do not silently re-word, re-order or drop other sections.'
        ),
        ANTI_HALLUCINATION_INVARIANTS,
        INDIAN_DRAFTING_CORE,
        build_statute_policy(ctx),
        build_playbook_block(ctx),
        (
            f'The document is a {playbook.label}. Revise it in {language}, keeping it '
            'compliant with every rule above. If the requested change would make the '
            'document legally wrong, make the change the user asked for and record the '
            'problem plainly rather than silently refusing.'
        ),
    ])


def target_max_tokens(ctx: DraftContext, *, ceiling: int = 10000) -> int:
    """
    Per-playbook output ceiling, replacing the global `max_tokens=4000`.

    4000 is what truncated the benchmark's partnership deed mid-sentence at
    "...in the presence of the". A 16-clause deed does not fit; the deed playbook
    asks for 10000. Capped to stay comfortably within a non-streaming response.
    """
    return max(1000, min(int(ctx.playbook.target_tokens or 6000), ceiling))
