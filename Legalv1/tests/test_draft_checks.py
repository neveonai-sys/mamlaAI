"""
Unit tests for the deterministic drafting checks.

Every test here maps to a defect the law interns actually found. These run
offline, in milliseconds, with no Django settings, no Mongo and no API key.
"""

import pytest

from ai_draft.drafting import checks as C
from ai_draft.evals.benchmark_drafts import (
    JHANA_RENT_NOTICE,
    MAMLA_PARTNERSHIP_DEED_TAIL,
    MAMLA_RENT_NOTICE,
)


# ---------------------------------------------------------------------------
# Defect #1 — penal codes in a civil matter
# ---------------------------------------------------------------------------

def test_finds_bnss_in_civil_rent_notice():
    """The headline defect: BNSS threatened for eviction in a rent dispute."""
    hits = C.find_statute_misuse(MAMLA_RENT_NOTICE)
    tokens = {h.token for h in hits}
    assert 'BNSS' in tokens
    assert all(h.section_name == 'CONSEQUENCES OF NON-COMPLIANCE' for h in hits)


def test_clean_civil_notice_has_no_statute_hits():
    assert C.find_statute_misuse(JHANA_RENT_NOTICE) == []


@pytest.mark.parametrize('text,expected', [
    ('proceedings under the Bharatiya Nyaya Sanhita 2023', 'Bharatiya Nyaya Sanhita'),
    ('an offence under IPC 420', 'IPC'),
    ('as provided in Cr.P.C. 482', 'CrPC'),
    ('under the Indian Evidence Act, 1872', 'Indian Evidence Act'),
    ('BNS 318 applies', 'BNS'),
])
def test_penal_token_variants_are_caught(text, expected):
    hits = C.find_statute_misuse([{'section_name': 'X', 'content': text}])
    assert expected in {h.token for h in hits}


def test_bns_inside_bnss_does_not_double_report_as_bns():
    """Word boundaries: 'BNSS' must not also register as a bare 'BNS'."""
    hits = C.find_statute_misuse([{'section_name': 'X', 'content': 'under BNSS alone'}])
    assert 'BNS' not in {h.token for h in hits}
    assert 'BNSS' in {h.token for h in hits}


def test_correct_disclaimer_is_not_flagged():
    """Saying the penal codes do NOT apply is right, not wrong."""
    ok = [{'section_name': 'NOTE',
           'content': 'This is a civil matter; the BNSS is not applicable to it.'}]
    assert C.find_statute_misuse(ok) == []


def test_disclaimer_exemption_is_sentence_scoped():
    """A disclaimer in one sentence must not licence a real citation in the next."""
    sneaky = [{'section_name': 'X', 'content': (
        'This is a civil matter and no criminal law applies. '
        'Proceedings shall be initiated under BNSS Section 163.'
    )}]
    assert 'BNSS' in {h.token for h in C.find_statute_misuse(sneaky)}


def test_statute_sweep_covers_advisory_notes():
    """A note recommending a wrong statute is as bad as a section citing one."""
    hits = C.find_statute_misuse(
        [{'section_name': 'X', 'content': 'clean text'}],
        extra_text='Consider invoking BNSS 163 for urgent relief.',
    )
    assert 'BNSS' in {h.token for h in hits}


# ---------------------------------------------------------------------------
# Defect #2 — missing Indian drafting conventions
# ---------------------------------------------------------------------------

def test_detects_missing_operative_clauses():
    missing = C.find_missing_phrases(
        MAMLA_RENT_NOTICE, ('NOW THEREFORE', 'TAKE NOTICE', 'Yours faithfully'))
    assert set(missing) == {'NOW THEREFORE', 'TAKE NOTICE', 'Yours faithfully'}


def test_phrase_alternatives_accept_recognised_variants():
    """'I, therefore, call upon you' is a proper demand, not a defect."""
    assert C.find_missing_phrases(
        JHANA_RENT_NOTICE, (['NOW THEREFORE', 'call upon you'],)) == []


def test_phrase_check_is_html_safe():
    """Section content is stored as editor HTML; tags must not hide a phrase."""
    html = [{'section_name': 'D', 'content': '<p><strong>NOW THEREFORE</strong>, I ...</p>'}]
    assert C.find_missing_phrases(html, ('NOW THEREFORE',)) == []


def test_missing_sections_tolerates_decorated_headings():
    sections = [{'section_name': 'NOW THEREFORE — DEMAND', 'content': 'x'}]
    assert C.find_missing_sections(sections, ('NOW THEREFORE',)) == []
    assert C.find_missing_sections(sections, ('TAKE NOTICE',)) == ['TAKE NOTICE']


# ---------------------------------------------------------------------------
# Defect #3a — truncation
# ---------------------------------------------------------------------------

def test_detects_the_partnership_deed_truncation():
    """'...shall sign below in the presence of the' — the real 4000-token cut."""
    hits = C.detect_truncation([MAMLA_PARTNERSHIP_DEED_TAIL])
    assert [h.reason for h in hits] == ['dangling_connective']


def test_signature_block_is_not_truncation():
    """'Yours faithfully, [ADVOCATE'S NAME], Advocate' ends correctly."""
    assert C.detect_truncation(JHANA_RENT_NOTICE) == []


def test_finish_reason_length_is_authoritative():
    clean = [{'section_name': 'X', 'content': 'A properly terminated sentence.'}]
    assert C.detect_truncation(clean) == []
    hits = C.detect_truncation(clean, finish_reason='length')
    assert [h.reason for h in hits] == ['finish_reason_length']


def test_properly_terminated_draft_passes():
    ok = [{'section_name': 'X',
           'content': 'The partners shall sign below in the presence of the witnesses.'}]
    assert C.detect_truncation(ok) == []


# ---------------------------------------------------------------------------
# Defect #3b — silently dropped instructions
# ---------------------------------------------------------------------------

PROMPT_WITH_RATIO = 'Profit/Loss Ratio: 50:30:20 respectively. Capital Rs 10 lakh. Pay in 15 days.'


def test_extracts_express_numeric_instructions():
    kinds = {l.kind for l in C.extract_prompt_literals(PROMPT_WITH_RATIO)}
    assert {'ratio', 'money', 'duration'} <= kinds


def test_ratio_is_high_confidence_money_is_not():
    """Money varies too much in representation to assert; ratios do not."""
    by_kind = {l.kind: l.confidence for l in C.extract_prompt_literals(PROMPT_WITH_RATIO)}
    assert by_kind['ratio'] == 'high'
    assert by_kind['money'] == 'low'


def test_detects_the_dropped_profit_ratio():
    deed = [MAMLA_PARTNERSHIP_DEED_TAIL]
    dropped = C.find_dropped_literals(PROMPT_WITH_RATIO, deed, only=('50:30:20',))
    assert [l.raw for l in dropped] == ['50:30:20']


def test_ratio_written_with_spaces_still_counts_as_honoured():
    honoured = [{'section_name': 'PROFITS',
                 'content': 'shared in the ratio 50 : 30 : 20 respectively.'}]
    assert C.find_dropped_literals(PROMPT_WITH_RATIO, honoured, only=('50:30:20',)) == []


def test_flagging_an_omission_in_notes_counts_as_honouring_it():
    """The failure mode is *silent* omission — an explicit flag is compliance."""
    deed = [MAMLA_PARTNERSHIP_DEED_TAIL]
    assert C.find_dropped_literals(
        PROMPT_WITH_RATIO, deed,
        notes_text='The 50:30:20 ratio could not be applied; confirm with the partners.',
        only=('50:30:20',),
    ) == []


def test_ratio_drafted_as_separate_percentages_counts_as_honoured():
    """
    The live baseline produced "Aarav shall receive 50%, Rohan 30%, Priya 20%"
    for an instruction of "50:30:20". Demanding the literal colon form reported
    a compliant deed as having silently dropped the instruction — a false
    positive on the flagship check, which would wrongly gate a release.
    """
    deed = [{'section_name': 'PROFIT AND LOSS SHARING', 'content':
             'shared among the Partners in the following ratio: Aarav Mehta shall receive '
             '50%, Rohan Sen shall receive 30%, and Priya Kapoor shall receive 20%.'}]
    assert C.find_dropped_literals(PROMPT_WITH_RATIO, deed, only=('50:30:20',)) == []


def test_partial_percentage_coverage_is_still_a_drop():
    """Every component must appear — two out of three is a dropped instruction."""
    deed = [{'section_name': 'P', 'content': 'Aarav 50% and Rohan 30%.'}]
    dropped = C.find_dropped_literals(PROMPT_WITH_RATIO, deed, only=('50:30:20',))
    assert [l.raw for l in dropped] == ['50:30:20']


def test_ratio_components_must_be_percentages_not_stray_numbers():
    """A bare '20' elsewhere in the deed must not satisfy the 20 in 50:30:20."""
    deed = [{'section_name': 'P', 'content':
             'Aarav 50%, Rohan 30%. The firm has 20 employees at 20 Park Street.'}]
    dropped = C.find_dropped_literals(PROMPT_WITH_RATIO, deed, only=('50:30:20',))
    assert [l.raw for l in dropped] == ['50:30:20']


def test_indian_numeral_then_words_convention_is_understood():
    """'15 (fifteen) days' honours an instruction that said '15 days'."""
    draft = [{'section_name': 'D', 'content':
              'within a period of 15 (fifteen) days from receipt.'}]
    assert C.find_dropped_literals('pay within 15 days', draft, only=('15 days',)) == []


def test_rupee_amount_with_words_in_parentheses_is_matched():
    draft = [{'section_name': 'D', 'content':
              'Rs 96,000/- (Rupees Ninety-Six Thousand only)'}]
    assert C.find_dropped_literals('dues of Rs 96,000', draft, only=('96,000',)) == []


# --- lakh / crore folding --------------------------------------------------
# A fifth fixture false positive, and on the flagship check: a notice properly
# claiming "Rs. 70,00,000/- (Rupees Seventy Lakh only)" was reported as having
# silently dropped the instructed "Rs 70 lakh", because the two representations
# normalised to different keys.

@pytest.mark.parametrize('instructed,drafted', [
    ('Rs 70 lakh', 'Rs. 70,00,000/- (Rupees Seventy Lakh only)'),
    ('Rs 2.8 crore', 'Rs. 2,80,00,000/- (Rupees Two Crore Eighty Lakh only)'),
    ('Rs 1.5 crore', 'Rs. 1,50,00,000/-'),
    # And the identity direction: unexpanded on both sides still agrees.
    ('Rs 70 lakh', 'a sum of Rs. 70 lakh'),
])
def test_lakh_and_crore_amounts_match_their_expanded_form(instructed, drafted):
    draft = [{'section_name': 'DEMAND', 'content': f'pay {drafted} forthwith.'}]
    assert C.find_dropped_literals(f'claim {instructed}', draft) == []


def test_a_genuinely_different_amount_is_still_reported():
    """Folding must not blunt: 70 lakh is not satisfied by 50 lakh."""
    draft = [{'section_name': 'DEMAND', 'content': 'pay Rs. 50,00,000/- forthwith.'}]
    dropped = C.find_dropped_literals('claim Rs 70 lakh', draft)
    assert [d.raw for d in dropped] == ['Rs 70 lakh']


def test_durations_are_untouched_by_the_multiplier_fold():
    draft = [{'section_name': 'D', 'content': 'within 15 (fifteen) days.'}]
    assert C.find_dropped_literals('pay within 15 days', draft, only=('15 days',)) == []
    assert C.find_dropped_literals('pay within 30 days', draft, only=('30 days',))


# ---------------------------------------------------------------------------
# Placeholders
# ---------------------------------------------------------------------------

def test_placeholder_inspection():
    rep = C.inspect_placeholders([{'section_name': 'X', 'content':
                                   'To [AKRITI SWAROOP] at [address of tenant] and [UNCLOSED'}])
    assert 'AKRITI SWAROOP' in rep.tokens
    assert 'address of tenant' in rep.lowercase   # not ALL CAPS
    assert rep.unclosed == 1


# ---------------------------------------------------------------------------
# HTML handling
# ---------------------------------------------------------------------------

def test_strip_html_preserves_block_boundaries():
    out = C.strip_html('<p>First para.</p><p>Second para.</p>')
    assert 'First para.' in out and 'Second para.' in out
    assert '<p>' not in out


def test_strip_html_decodes_entities():
    assert C.strip_html('Rs&nbsp;96,000 &amp; costs') == 'Rs 96,000 & costs'
