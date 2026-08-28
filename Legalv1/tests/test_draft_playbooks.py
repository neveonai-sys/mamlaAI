"""
Structural invariants over the playbook registry.

These are cheap assertions about data, not behaviour, and they exist because
every one of them is a silent production failure if it breaks: a duplicate alias
mis-routes drafts, an empty deny-list re-opens defect #1 for that type, and a
skeleton with no required sections makes the Phase 2 validator vacuous.
"""

import re

import pytest

from ai_draft.drafting import playbooks
from ai_draft.drafting.playbooks import (
    CRIMINAL,
    NON_PENAL_BRANCHES,
    UNKNOWN,
    base,
)

ALL = playbooks.all_playbooks()


def test_registry_is_not_empty():
    assert len(ALL) >= 12, 'the approved scope is ~12 document types plus generic'


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_keyword_regexes_compile(pb):
    for pattern, weight in pb.keywords:
        re.compile(pattern)
        assert isinstance(weight, int)


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_every_skeleton_has_a_required_section(pb):
    assert pb.required_sections, f'{pb.doc_type} has no required sections'


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_branch_is_known(pb):
    assert pb.branch in base.BRANCHES


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_non_criminal_branches_deny_penal_statutes(pb):
    """
    The core guarantee of Phase 1.

    Every civil/commercial/testamentary/family type must carry a non-empty
    deny-list, because that tuple is simultaneously what the prompt states as a
    prohibition and what `find_statute_misuse` enforces afterwards.
    """
    if pb.branch in NON_PENAL_BRANCHES:
        assert pb.deny_patterns, f'{pb.doc_type} ({pb.branch}) has an empty deny-list'
    else:
        assert pb.branch in (CRIMINAL, UNKNOWN, 'constitutional')


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_criminal_branches_do_not_deny_penal_statutes(pb):
    """The penal codes belong in a bail application; denying them there is the mirror bug."""
    if pb.branch == CRIMINAL:
        assert pb.deny_patterns == ()


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_non_criminal_types_have_an_allow_list(pb):
    """A prohibition without an allow-list leaves the model nothing to cite."""
    if pb.branch in NON_PENAL_BRANCHES:
        assert pb.statutes_allow, f'{pb.doc_type} forbids the penal codes but allows nothing'


@pytest.mark.parametrize('pb', ALL, ids=lambda p: p.doc_type)
def test_target_tokens_exceeds_the_old_global_ceiling(pb):
    """
    4000 truncated the benchmark's partnership deed mid-sentence. Nothing should
    silently inherit that ceiling again.
    """
    if len(pb.skeleton) >= 10:
        assert pb.target_tokens >= 7000, f'{pb.doc_type} has {len(pb.skeleton)} sections but only {pb.target_tokens} tokens'


def test_aliases_are_unique_across_the_registry():
    """Enforced at import; asserted here so the failure is legible."""
    seen: dict[str, str] = {}
    for pb in playbooks.all_playbooks(include_generic=True):
        for alias in (pb.doc_type,) + pb.aliases:
            key = alias.strip().lower()
            assert key not in seen or seen[key] == pb.doc_type, (
                f'alias {alias!r} claimed by {seen.get(key)} and {pb.doc_type}'
            )
            seen[key] = pb.doc_type


def test_doc_types_are_unique():
    types = [pb.doc_type for pb in playbooks.all_playbooks(include_generic=True)]
    assert len(types) == len(set(types))


def test_get_falls_back_to_generic():
    assert playbooks.get('no-such-type').doc_type == 'generic'
    assert playbooks.get(None).doc_type == 'generic'
    assert playbooks.get('').doc_type == 'generic'


def test_get_is_case_insensitive():
    assert playbooks.get('WILL').doc_type == 'will'
    assert playbooks.get('  Vakalatnama  ').doc_type == 'vakalatnama'


def test_required_phrases_are_flattened_for_the_validator():
    pb = playbooks.get('legal_notice.rent_arrears')
    phrases = pb.required_phrases
    assert phrases, 'rent-arrears notice must assert its conventions'
    flat = [p for entry in phrases for p in (entry if isinstance(entry, tuple) else (entry,))]
    assert 'TAKE NOTICE' in flat
    assert any('NOW THEREFORE' in p for p in flat)


# ---------------------------------------------------------------------------
# The notice family — the types the benchmark scored worst
# ---------------------------------------------------------------------------

NOTICE_TYPES = ('legal_notice.demand', 'legal_notice.rent_arrears', 'legal_notice.cheque_138')


@pytest.mark.parametrize('doc_type', NOTICE_TYPES)
def test_notices_have_a_hand_authored_exemplar(doc_type):
    """
    The corpus has no notice precedent at all — the only Notice/ file is an
    arbitrator-appointment notice. These exemplars are the substitute and must
    not silently disappear.
    """
    pb = playbooks.get(doc_type)
    assert len(pb.inline_exemplar) > 800, f'{doc_type} has no usable inline exemplar'


@pytest.mark.parametrize('doc_type', NOTICE_TYPES)
def test_notice_exemplars_carry_indian_conventions(doc_type):
    """The exemplar must itself demonstrate what defect #2 said was missing."""
    text = playbooks.get(doc_type).inline_exemplar
    assert 'TAKE NOTICE' in text
    assert 'Yours faithfully' in text
    assert 'Advocate' in text
    assert re.search(r'^\s*1\.\s+That ', text, re.MULTILINE), 'no numbered "That" recital'
    assert 'NOW THEREFORE' in text


@pytest.mark.parametrize('doc_type', NOTICE_TYPES)
def test_notice_exemplars_cite_no_penal_statute(doc_type):
    """
    An exemplar that cited the BNSS would teach the exact defect we are fixing.
    Uses the production checker, not a bespoke regex.
    """
    from ai_draft.drafting.checks import find_statute_misuse

    pb = playbooks.get(doc_type)
    hits = find_statute_misuse(
        [{'section_name': 'exemplar', 'content': pb.inline_exemplar}],
        deny_patterns=pb.deny_patterns,
    )
    assert not hits, f'{doc_type} exemplar cites {[h.token for h in hits]}'


@pytest.mark.parametrize('doc_type', NOTICE_TYPES)
def test_notice_exemplars_use_placeholders_not_invented_facts(doc_type):
    text = playbooks.get(doc_type).inline_exemplar
    assert '[' in text and ']' in text
    # A specimen with a real-looking party name would get copied into drafts.
    assert 'ADVOCATE NAME' in text


def test_ui_categories_shape():
    cats = playbooks.ui_categories()
    assert cats
    seen_types = set()
    for entry in cats:
        assert set(entry) == {'category', 'types'}
        assert entry['types']
        for t in entry['types']:
            assert set(t) == {'value', 'label'}
            assert playbooks.exists(t['value'])
            seen_types.add(t['value'])
    # Every non-generic playbook must be selectable in the UI.
    assert seen_types == {pb.doc_type for pb in ALL}


def test_ui_categories_excludes_generic():
    values = {t['value'] for c in playbooks.ui_categories() for t in c['types']}
    assert 'generic' not in values
