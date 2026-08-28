"""
Tests for the repair ladder and the deterministic validator.

The parsing tests are not hypotheticals. Every rung below corresponds to a real
response that discarded a complete, correct draft before Phase 2:

  * an unclosed ``` fence on a truncated response
  * a raw newline inside a clause string (lost an otherwise perfect Will)
  * two paragraphs of prose above the JSON (the model had nowhere to put the
    assumptions it was asked for, so it wrote them as preamble)

`test_draft_evals.py` covers scoring; this covers the gate.
"""

import json

import pytest

from ai_draft.drafting import draft_validator as dv
from ai_draft.drafting.classify import DraftContext, classify


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _sections(*names):
    return [{'section_name': n, 'content': f'That the content of {n} is complete.'}
            for n in names]


def _legacy(*names):
    return json.dumps(_sections(*names))


# ===========================================================================
# The repair ladder
# ===========================================================================

def test_clean_legacy_array_parses_unrepaired():
    r = dv.parse_draft_payload(_legacy('FIRST', 'SECOND'))
    assert not r.fatal
    assert r.repaired == ''
    assert r.schema == 'legacy'
    assert [s['section_name'] for s in r.sections] == ['FIRST', 'SECOND']


def test_advisory_object_yields_sections_and_advisories():
    payload = json.dumps({
        'document_type': 'legal_notice.rent_arrears',
        'sections': _sections('NOTICE'),
        'assumptions': [{'assumption': 'Tenancy is oral', 'why': 'No deed supplied',
                         'confirm_with_client': True}],
        'drafting_notes': [{'issue': 'Limitation may have run', 'severity': 'high',
                            'recommendation': 'Confirm the date of default'}],
    })
    r = dv.parse_draft_payload(payload)
    assert not r.fatal
    assert r.schema == 'advisory'
    assert len(r.sections) == 1
    assert r.assumptions[0]['assumption'] == 'Tenancy is oral'
    assert r.drafting_notes[0]['severity'] == 'high'


def test_fences_are_stripped_independently_at_each_end():
    """A truncated response opens its fence and never closes it.

    The pre-Phase-2 check required both ends to match, so it failed on exactly
    the responses that most needed recovering.
    """
    assert not dv.parse_draft_payload('```json\n' + _legacy('A') + '\n```').fatal
    assert not dv.parse_draft_payload('```json\n' + _legacy('A')).fatal
    assert not dv.parse_draft_payload(_legacy('A') + '\n```').fatal


def test_raw_newline_inside_a_clause_does_not_discard_the_draft():
    """strict=False. This single character lost a complete Will."""
    raw = '[{"section_name": "CLAUSE", "content": "That the first line\nand the second."}]'
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)  # confirms the input really is strict-invalid
    r = dv.parse_draft_payload(raw)
    assert not r.fatal
    assert '\n' in r.sections[0]['content']


def test_prose_above_the_json_is_recovered():
    raw = (
        'Before the draft, I flag the material gaps I have filled with '
        'placeholders rather than invented facts.\n\n' + _legacy('A', 'B')
    )
    r = dv.parse_draft_payload(raw)
    assert not r.fatal
    assert r.repaired == 'extracted_from_prose'
    assert len(r.sections) == 2


def test_extraction_survives_brackets_inside_clause_text():
    """`[PROPERTY ADDRESS]` appears in almost every draft we produce.

    A naive find('[')..rfind(']') would cut the payload at the placeholder.
    """
    raw = 'Here is the draft:\n' + json.dumps([
        {'section_name': 'SCHEDULE', 'content': 'The property at [PROPERTY ADDRESS].'},
        {'section_name': 'DEMAND', 'content': 'Pay within [15] days.'},
    ])
    r = dv.parse_draft_payload(raw)
    assert len(r.sections) == 2
    assert '[PROPERTY ADDRESS]' in r.sections[0]['content']


def test_object_is_preferred_over_a_nested_array():
    """Extracting the array first would silently discard the advisories."""
    raw = 'Here you go:\n' + json.dumps({
        'sections': _sections('A'),
        'assumptions': [{'assumption': 'x', 'why': 'y'}],
        'drafting_notes': [],
    })
    r = dv.parse_draft_payload(raw)
    assert r.schema == 'advisory'
    assert r.assumptions


def test_trailing_commas_and_smart_quotes_are_normalised():
    raw = '[{"section_name": "A", "content": "text",},]'
    r = dv.parse_draft_payload(raw)
    assert not r.fatal
    assert r.repaired == 'normalised_punctuation'


def test_truncation_salvage_returns_a_partial_draft_with_an_error():
    """Total loss becomes a partial draft the user can actually see."""
    raw = (
        '[{"section_name": "FIRST", "content": "That the first is complete."},'
        ' {"section_name": "SECOND", "content": "That the second is complete."},'
        ' {"section_name": "THIRD", "content": "That the third is cut off in the'
    )
    r = dv.parse_draft_payload(raw)
    assert not r.fatal
    assert r.repaired == 'truncation_salvage'
    assert [s['section_name'] for s in r.sections] == ['FIRST', 'SECOND']
    assert any(f.code == 'truncation' and f.is_error for f in r.findings)


def test_truncation_salvage_works_on_the_advisory_object():
    raw = (
        '{"document_type": "will", "sections": ['
        '{"section_name": "FIRST", "content": "That the first is complete."},'
        '{"section_name": "SECOND", "content": "That the second is cut'
    )
    r = dv.parse_draft_payload(raw)
    assert not r.fatal
    assert [s['section_name'] for s in r.sections] == ['FIRST']


def test_empty_and_none_are_fatal_not_crashes():
    for value in (None, '', '   ', '```json\n```'):
        r = dv.parse_draft_payload(value)
        assert r.fatal
        assert r.findings and r.findings[0].is_error


def test_unparseable_prose_is_fatal():
    r = dv.parse_draft_payload('I am unable to draft this document.')
    assert r.fatal
    assert r.findings[0].code == 'unparseable'


def test_sections_missing_a_name_or_body_are_dropped_not_fatal():
    raw = json.dumps([
        {'section_name': 'GOOD', 'content': 'That this is fine.'},
        {'section_name': 'EMPTY', 'content': '   '},
        {'content': 'orphan with no name'},
    ])
    r = dv.parse_draft_payload(raw)
    assert [s['section_name'] for s in r.sections] == ['GOOD']
    assert any(f.code == 'malformed_section' for f in r.findings)


def test_a_payload_with_no_usable_sections_is_fatal():
    r = dv.parse_draft_payload(json.dumps([{'section_name': 'A', 'content': ''}]))
    assert r.fatal


def test_content_supplied_as_a_list_of_paragraphs_is_joined():
    raw = json.dumps([{'section_name': 'A', 'content': ['That the first.', 'That the second.']}])
    r = dv.parse_draft_payload(raw)
    assert r.sections[0]['content'] == 'That the first.\nThat the second.'


def test_parse_never_raises_on_arbitrary_input():
    for value in (0, [], {}, 'null', '[]', '{"sections": "not a list"}', '[[[['):
        dv.parse_draft_payload(value)  # must not raise


# ===========================================================================
# Validation
# ===========================================================================

def _rent_ctx() -> DraftContext:
    ctx = classify('Draft a legal notice to a tenant for arrears of rent and eviction')
    assert ctx.doc_type == 'legal_notice.rent_arrears', ctx.doc_type
    return ctx


def _codes(result):
    return {f.code for f in result.findings}


def test_penal_statute_in_a_civil_notice_is_an_error():
    """Defect #1, the flagship. BNSS threatened for eviction in a rent matter."""
    ctx = _rent_ctx()
    r = dv.DraftResult(sections=[
        {'section_name': 'DEMAND',
         'content': 'Failing payment my Client shall proceed under Section 223 of the BNSS.'},
    ])
    dv.validate(r, ctx, user_query='rent arrears notice')
    hits = [f for f in r.findings if f.code == 'statute_misuse']
    assert hits and hits[0].is_error
    assert 'BNSS' in hits[0].message


def test_a_penal_reference_in_the_drafting_notes_is_caught_too():
    """A note recommending the BNSS is as wrong as a section citing it."""
    ctx = _rent_ctx()
    r = dv.DraftResult(
        sections=[{'section_name': 'DEMAND', 'content': 'That payment is demanded.'}],
        drafting_notes=[{'issue': 'Consider an FIR',
                         'recommendation': 'File under the Indian Penal Code',
                         'severity': 'low'}],
        schema='advisory',
    )
    dv.validate(r, ctx, user_query='rent notice')
    assert 'statute_misuse' in _codes(r)


def test_criminal_branch_may_cite_the_penal_codes():
    ctx = classify('Draft a bail application for the accused in a criminal case')
    assert ctx.branch == 'criminal'
    r = dv.DraftResult(sections=[
        {'section_name': 'GROUNDS', 'content': 'The applicant is charged under the BNS.'},
    ])
    dv.validate(r, ctx, user_query='bail application')
    assert 'statute_misuse' not in _codes(r)


def test_missing_mandatory_sections_are_an_error():
    ctx = _rent_ctx()
    r = dv.DraftResult(sections=_sections('SOMETHING ELSE'))
    dv.validate(r, ctx, user_query='rent notice')
    assert 'missing_section' in _codes(r)
    assert all(f.is_error for f in r.findings if f.code == 'missing_section')


def test_dropped_ratio_is_an_error_and_flagging_it_in_the_notes_is_not():
    """Defect #3b: the deed silently omitted the instructed 50:30:20."""
    ctx = classify('Draft a partnership deed for three partners')
    query = 'Profits shall be shared in the ratio 50:30:20 between the partners.'

    silent = dv.DraftResult(sections=_sections('PROFIT SHARING'))
    dv.validate(silent, ctx, user_query=query)
    dropped = [f for f in silent.findings if f.code == 'instruction_dropped']
    assert dropped and dropped[0].is_error

    flagged = dv.DraftResult(
        sections=_sections('PROFIT SHARING'),
        drafting_notes=[{'issue': 'The 50:30:20 ratio was not allocated to named partners',
                         'severity': 'high', 'recommendation': 'Confirm the split'}],
        schema='advisory',
    )
    dv.validate(flagged, ctx, user_query=query)
    assert 'instruction_dropped' not in _codes(flagged)


def test_finish_reason_length_is_authoritative_truncation():
    ctx = _rent_ctx()
    r = dv.DraftResult(sections=_sections('NOTICE'))
    dv.validate(r, ctx, user_query='q', finish_reason='length')
    assert 'truncation' in _codes(r)


def test_truncation_is_reported_once_not_twice():
    """The salvage rung already filed it; validate must not duplicate."""
    raw = ('[{"section_name": "FIRST", "content": "That the first is complete."},'
           ' {"section_name": "SECOND", "content": "That the second is cut off in the')
    r = dv.parse_draft_payload(raw)
    dv.validate(r, _rent_ctx(), user_query='q', finish_reason='length')
    assert len([f for f in r.findings if f.code == 'truncation']) == 1


def test_advisory_omissions_are_warnings_never_errors():
    """A correction turn spent demanding notes on a draft that needed none
    would cost more than the omission."""
    ctx = _rent_ctx()
    r = dv.DraftResult(sections=_sections('NOTICE'), schema='advisory')
    dv.validate(r, ctx, user_query='q')
    advisory = [f for f in r.findings if f.code == 'advisory_missing']
    assert advisory
    assert all(not f.is_error for f in advisory)


def test_lowercase_placeholder_is_a_warning():
    ctx = _rent_ctx()
    r = dv.DraftResult(sections=[
        {'section_name': 'PARTIES', 'content': 'Served upon [tenant name] at [PROPERTY].'},
    ])
    dv.validate(r, ctx, user_query='q')
    ph = [f for f in r.findings if f.code == 'placeholder']
    assert ph and not ph[0].is_error


def test_correction_message_names_the_specific_defects():
    """"Please improve the draft" invites a rewrite that loses what was right."""
    ctx = _rent_ctx()
    r = dv.DraftResult(sections=[
        {'section_name': 'DEMAND', 'content': 'Proceedings under the BNSS will follow.'},
    ])
    dv.validate(r, ctx, user_query='q')
    msg = dv.build_correction_message(r, ctx)
    assert 'BNSS' in msg
    assert 'Keep everything that was already correct' in msg


def test_errors_and_warnings_partition_the_findings():
    r = dv.DraftResult(findings=[
        dv.Finding('a', dv.ERROR, 'e'), dv.Finding('b', dv.WARNING, 'w'),
    ])
    assert len(r.errors) == 1 and len(r.warnings) == 1


def test_summary_is_loggable_for_any_result():
    assert 'sections=0' in dv.DraftResult().summary()
    assert 'clean' in dv.DraftResult().summary()
