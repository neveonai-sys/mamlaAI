"""
Prompt-composition tests.

The load-bearing assertion in this file is `test_non_criminal_prompts_forbid...`:
it is the difference between "we told the model to be careful" and "the model was
told, in terms, that these statutes do not exist for this document". Defect #1 —
the BNSS cited to threaten eviction in a civil rent matter — is a prompt bug, and
this is where the fix is pinned down.
"""

import pytest

from ai_draft.drafting import playbooks
from ai_draft.drafting.classify import classify
from ai_draft.drafting.playbooks import CRIMINAL, NON_PENAL_BRANCHES
from ai_draft.drafting.prompt_builder import (
    ANTI_HALLUCINATION_INVARIANTS,
    build_draft_system_prompt,
    build_location_string,
    build_playbook_block,
    build_refine_system_prompt,
    build_statute_policy,
    target_max_tokens,
)

ALL = playbooks.all_playbooks()
NON_PENAL = [p for p in ALL if p.branch in NON_PENAL_BRANCHES]
CRIMINAL_PBS = [p for p in ALL if p.branch == CRIMINAL]

PENAL_NAMES = ('BNS', 'BNSS', 'BSA', 'Indian Penal Code', 'Code of Criminal Procedure')


def ctx_for(doc_type):
    return classify('', doc_type, allow_llm=False)


# ---------------------------------------------------------------------------
# Statute policy — the fix for defect #1
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('pb', NON_PENAL, ids=lambda p: p.doc_type)
def test_non_criminal_prompts_forbid_the_penal_codes(pb):
    policy = build_statute_policy(ctx_for(pb.doc_type))
    assert 'MUST NOT' in policy
    for name in PENAL_NAMES:
        assert name in policy, f'{pb.doc_type} policy never names {name} as forbidden'
    assert 'NO application' in policy


@pytest.mark.parametrize('pb', NON_PENAL, ids=lambda p: p.doc_type)
def test_non_criminal_prompts_supply_a_closed_allow_list(pb):
    """A prohibition alone leaves the model with nothing to cite."""
    policy = build_statute_policy(ctx_for(pb.doc_type))
    assert 'You may cite ONLY from the following' in policy
    assert pb.statutes_allow[0][:30] in policy


@pytest.mark.parametrize('pb', NON_PENAL, ids=lambda p: p.doc_type)
def test_non_criminal_prompts_forbid_criminal_characterisation(pb):
    """
    Removing the citation is not enough — the benchmark draft also described a
    defaulting tenant in the register of a criminal accused.
    """
    policy = build_statute_policy(ctx_for(pb.doc_type))
    assert '"offence"' in policy
    assert '"accused"' in policy
    assert 'FIR' in policy


@pytest.mark.parametrize('pb', CRIMINAL_PBS, ids=lambda p: p.doc_type)
def test_criminal_prompts_receive_the_verified_correspondence_table(pb):
    """
    The table has existed in statute_map.py all along but reached only the chat
    path. Drafting got the "use the 2023 codes" instruction without the map —
    an invitation to guess section numbers.
    """
    policy = build_statute_policy(ctx_for(pb.doc_type))
    assert 'IPC 302→BNS 103' in policy
    assert 'CrPC 438→BNSS 482' in policy
    assert 'to be confirmed' in policy
    assert 'MUST NOT' not in policy, 'a bail application may cite the penal codes'


def test_generic_still_carries_a_conditional_but_is_explicit_about_scope():
    policy = build_statute_policy(ctx_for('generic'))
    assert 'ONLY where criminal law' in policy
    assert 'NO application to a civil' in policy


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_every_policy_bans_guessing_section_numbers(pb):
    policy = build_statute_policy(ctx_for(pb.doc_type))
    assert 'to be confirmed' in policy


# ---------------------------------------------------------------------------
# Playbook block
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_playbook_block_lists_every_required_section(pb):
    block = build_playbook_block(ctx_for(pb.doc_type))
    for name in pb.required_sections:
        assert name in block, f'{pb.doc_type} block omits required section {name}'


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_playbook_block_carries_the_pitfalls(pb):
    block = build_playbook_block(ctx_for(pb.doc_type))
    if pb.pitfalls:
        assert 'AVOID THESE SPECIFIC DEFECTS' in block
        assert pb.pitfalls[0][:40] in block


def test_must_contain_alternatives_render_as_alternatives():
    block = build_playbook_block(ctx_for('legal_notice.demand'))
    assert '"NOW THEREFORE" or "call upon you"' in block


def test_optional_sections_are_marked_optional():
    block = build_playbook_block(ctx_for('legal_notice.demand'))
    assert 'include only if the facts call for it' in block


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

# Distinctive *opening lines* of each block. Deliberately not bare phrases:
# INDIAN_DRAFTING_CORE forward-references "the MANDATORY SKELETON below", so
# matching on the bare phrase would compare a cross-reference against a heading.
BLOCK_HEADINGS = (
    'NON-NEGOTIABLE RULES',
    'INDIAN DRAFTING CONVENTIONS (apply to every document',
    'STATUTE POLICY',
    'MANDATORY SKELETON — produce these sections',
    'OUTPUT FORMAT — follow exactly',
)


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_full_prompt_contains_every_block_in_order(pb):
    prompt = build_draft_system_prompt(ctx_for(pb.doc_type))
    assert 'senior Indian advocate' in prompt
    for heading in BLOCK_HEADINGS:
        assert heading in prompt, f'{pb.doc_type} prompt missing {heading!r}'

    positions = [prompt.index(h) for h in BLOCK_HEADINGS]
    assert positions == sorted(positions), 'blocks are out of order'


def test_invariants_are_imported_not_restated():
    """One source of truth shared with the chat orchestrator."""
    prompt = build_draft_system_prompt(ctx_for('will'))
    assert ANTI_HALLUCINATION_INVARIANTS in prompt


def test_prompt_bans_the_form_headings_the_reviewers_named():
    prompt = build_draft_system_prompt(ctx_for('legal_notice.rent_arrears'))
    assert 'TITLE OF THE NOTICE' in prompt
    assert "SENDER'S DETAILS" in prompt
    assert 'Do not use form-filling headings' in prompt


def test_prompt_no_longer_shows_a_pleading_skeleton_as_the_example():
    """
    The old prompt's only worked example was TITLE OF THE SUIT / PRELIMINARY
    STATEMENT — a pleading skeleton the model copied into notices and wills.
    """
    for doc_type in ('legal_notice.rent_arrears', 'will', 'partnership_deed'):
        prompt = build_draft_system_prompt(ctx_for(doc_type))
        assert 'PRELIMINARY STATEMENT' not in prompt


def test_exemplar_is_injected_with_an_override_warning():
    pb = playbooks.get('legal_notice.rent_arrears')
    prompt = build_draft_system_prompt(ctx_for(pb.doc_type), exemplar=pb.inline_exemplar)
    assert 'FORMAT REFERENCE' in prompt
    assert 'Do NOT copy its facts' in prompt
    assert 'those override it' in prompt
    assert prompt.index('MANDATORY SKELETON') < prompt.index('BEGIN FORMAT REFERENCE')


def test_source_text_is_bounded_and_labelled():
    """A 40-page upload must not blow the context window."""
    prompt = build_draft_system_prompt(ctx_for('will'), source_text='X' * 50000)
    assert 'BEGIN SOURCE' in prompt
    body = prompt.split('--- BEGIN SOURCE ---')[1].split('--- END SOURCE ---')[0]
    assert len(body.strip()) == 20000


def test_no_exemplar_block_when_none_supplied():
    assert 'FORMAT REFERENCE' not in build_draft_system_prompt(ctx_for('plaint'))


@pytest.mark.parametrize('language', ['English', 'Hindi', 'Marathi'])
def test_language_is_threaded(language):
    assert language in build_draft_system_prompt(ctx_for('affidavit'), language=language)


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------

def test_legacy_schema_is_the_phase_one_default():
    """Storage and the read path are untouched until Phase 2."""
    prompt = build_draft_system_prompt(ctx_for('will'))
    assert 'Return ONLY a JSON array' in prompt
    assert 'drafting_notes' not in prompt


def test_advisory_schema_is_available_for_phase_two():
    prompt = build_draft_system_prompt(ctx_for('will'), schema='advisory')
    assert 'drafting_notes' in prompt
    assert 'assumptions' in prompt
    assert 'Silently dropping an instruction is a defect' in prompt


# ---------------------------------------------------------------------------
# Refine parity — cause H
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('pb', NON_PENAL, ids=lambda p: p.doc_type)
def test_refine_carries_the_identical_statute_policy(pb):
    """
    A refine turn reintroducing the BNSS into a civil notice is cause H. The
    only way to guarantee it cannot is for both prompts to render the same block.
    """
    ctx = ctx_for(pb.doc_type)
    assert build_statute_policy(ctx) in build_refine_system_prompt(ctx)


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_refine_carries_the_playbook_and_invariants(pb):
    ctx = ctx_for(pb.doc_type)
    refine = build_refine_system_prompt(ctx)
    assert ANTI_HALLUCINATION_INVARIANTS in refine
    assert build_playbook_block(ctx) in refine


def test_refine_preserves_unrelated_sections():
    refine = build_refine_system_prompt(ctx_for('will'))
    assert 'Preserve everything not covered by the request' in refine


# ---------------------------------------------------------------------------
# Token ceilings — defect #3a
# ---------------------------------------------------------------------------

def test_partnership_deed_gets_far_more_than_the_old_ceiling():
    """4000 is what truncated it at '...in the presence of the'."""
    assert target_max_tokens(ctx_for('partnership_deed')) >= 9000


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_token_ceilings_are_sane(pb):
    tokens = target_max_tokens(ctx_for(pb.doc_type))
    assert 1000 <= tokens <= 10000


def test_ceiling_is_enforced():
    ctx = ctx_for('partnership_deed')
    assert target_max_tokens(ctx, ceiling=5000) == 5000


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('location,expected', [
    ({}, ''),
    (None, ''),
    ('not a dict', ''),
    ({'state': 'West Bengal'}, 'for the state "West Bengal"'),
    ({'district': 'Kolkata', 'state': 'West Bengal'},
     'in the district "Kolkata" of the state "West Bengal"'),
    ({'court': 'City Civil Court', 'district': 'Kolkata', 'state': 'West Bengal'},
     'for the court "City Civil Court" in the district "Kolkata" of the state "West Bengal"'),
])
def test_location_string(location, expected):
    assert build_location_string(location) == expected
