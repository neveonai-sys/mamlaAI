"""
Classification tests.

The routing table below is the contract: these are the queries the product
actually receives, and a regression here silently sends a rent notice to the
lease-agreement playbook — which is exactly what the first implementation did.

Everything runs with `allow_llm=False`, so the whole file is free and offline.
That is also the point being asserted: real user phrasings should not need an
LLM round trip to classify.
"""

import pytest

from ai_draft.drafting import playbooks
from ai_draft.drafting.classify import (
    LLM,
    EXPLICIT,
    FALLBACK,
    KEYWORD,
    DraftContext,
    classify,
    normalize_type_hint,
    score_all,
)

# ---------------------------------------------------------------------------
# Free-text routing
# ---------------------------------------------------------------------------

ROUTING = [
    # The four benchmark prompts, in the shape the interns submitted them.
    ('Draft a legal notice from my client Karuna Anupam to Akriti Swaroop regarding '
     'unpaid rent under a lease agreement dated 15 January 2026 at a monthly rent of '
     'Rs 32,000. Akriti has failed to pay rent for May, June and July.',
     'legal_notice.rent_arrears'),
    ('Act as an experienced litigation lawyer. Draft a legal notice on behalf of my '
     'client ABC Infrastructure Pvt Ltd against XYZ Developers LLP for recovery of '
     'outstanding dues under a construction contract.',
     'legal_notice.demand'),
    ('Draft a legally comprehensive Last Will and Testament for an Indian Hindu '
     'individual. Mr Rajesh Mehra wishes to bequeath his flat to his wife.',
     'will'),
    ('Draft a Partnership Deed under the Indian Partnership Act 1932 for Mehta Sen & '
     'Associates. Profit/Loss Ratio: 50:30:20.',
     'partnership_deed'),

    # Ordinary phrasings.
    ('Draft a legal notice for dishonour of cheque no 4412 under section 138', 'legal_notice.cheque_138'),
    ('cheque bounce notice for Rs 2 lakh', 'legal_notice.cheque_138'),
    ('Prepare a rent agreement for my flat in Pune for 11 months', 'rent_lease_agreement'),
    ('draft a leave and licence agreement for commercial premises', 'rent_lease_agreement'),
    ('Draft a legal notice to my tenant who has not paid rent since March', 'legal_notice.rent_arrears'),
    ('I need a will for my father who owns property in Delhi', 'will'),
    ('File a bail application, my brother was arrested yesterday', 'bail'),
    ('anticipatory bail before the sessions court', 'anticipatory_bail'),
    ('Draft a plaint for recovery of Rs 5 lakh against a supplier', 'plaint'),
    ('prepare a written statement replying to the plaint in suit no 44 of 2026', 'written_statement'),
    ('writ petition under article 226 for a writ of mandamus', 'writ_petition'),
    ('consumer complaint against a builder for deficiency in service', 'consumer_complaint'),
    ('affidavit for change of name, deponent is my mother', 'affidavit'),
    ('vakalatnama for the district court at Nagpur', 'vakalatnama'),
    ('sale deed for a plot in Siliguri conveying title to the vendee', 'sale_deed'),
]


@pytest.mark.parametrize('query,expected', ROUTING, ids=[e for _, e in ROUTING])
def test_free_text_routing(query, expected):
    ctx = classify(query, allow_llm=False)
    assert ctx.doc_type == expected, (
        f'got {ctx.doc_type}; top candidates: '
        f'{[(s, p.doc_type) for s, p in score_all(query)[:4]]}'
    )
    assert ctx.confidence == KEYWORD


def test_a_notice_about_a_lease_is_a_notice_not_a_lease():
    """
    The regression that motivated the lead-window rule.

    Every notice recites the instrument it complains of, so "lease agreement"
    appears in a rent-arrears notice prompt more prominently than "legal notice".
    Scoring the whole text alone routed fixture 001 — our worst-performing
    document — to `rent_lease_agreement`.
    """
    query = (
        'Draft a legal notice from my client to the tenant regarding a lease '
        'agreement dated 15 January 2026. The lease agreement provides for rent '
        'of Rs 32,000. The tenant has breached the lease agreement.'
    )
    assert classify(query, allow_llm=False).doc_type == 'legal_notice.rent_arrears'


def test_an_actual_lease_request_still_routes_to_the_lease_playbook():
    """The counterpart: the lead-window rule must not break the ordinary case."""
    assert classify(
        'Draft a lease agreement for my shop, 3 year term, rent Rs 40,000',
        allow_llm=False,
    ).doc_type == 'rent_lease_agreement'


def test_branch_is_read_off_the_playbook_never_guessed():
    for query, expected in ROUTING:
        ctx = classify(query, allow_llm=False)
        assert ctx.branch == playbooks.get(expected).branch


def test_unclassifiable_query_falls_back_without_calling_the_llm():
    ctx = classify('write something legal for me', allow_llm=False)
    assert ctx.doc_type == 'generic'
    assert ctx.confidence == FALLBACK
    assert ctx.is_generic


def test_empty_query_is_generic():
    assert classify('', allow_llm=False).doc_type == 'generic'
    assert classify(None, allow_llm=False).doc_type == 'generic'


# ---------------------------------------------------------------------------
# Explicit hints
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('hint,expected', [
    ('legal_notice.rent_arrears', 'legal_notice.rent_arrears'),
    ('Rent Agreement', 'rent_lease_agreement'),
    ('rent-agreement', 'rent_lease_agreement'),
    ('will', 'will'),
    ('Last Will and Testament', 'will'),
    ('vakalatnama', 'vakalatnama'),
    ('cheque bounce notice', 'legal_notice.cheque_138'),
    ('anticipatory bail', 'anticipatory_bail'),
    ({'document_type': 'partnership_deed'}, 'partnership_deed'),
    (['plaint'], 'plaint'),
])
def test_explicit_hint_wins(hint, expected):
    ctx = classify('', hint, allow_llm=False)
    assert ctx.doc_type == expected
    assert ctx.confidence == EXPLICIT


def test_explicit_hint_beats_conflicting_query_text():
    """A user who picked a type in the UI has said what they want."""
    ctx = classify('something about a will and a testament', 'affidavit', allow_llm=False)
    assert ctx.doc_type == 'affidavit'


def test_unrecognised_hint_falls_through_to_the_query():
    ctx = classify('draft a vakalatnama for the high court', 'some-unknown-label', allow_llm=False)
    assert ctx.doc_type == 'vakalatnama'


def test_unrecognised_hint_alone_is_generic():
    assert classify('', 'some-unknown-label', allow_llm=False).doc_type == 'generic'


# ---------------------------------------------------------------------------
# Cause C-prime: `draft_for` is case/client association, NOT a document type
# ---------------------------------------------------------------------------

ASSOCIATION_PAYLOADS = [
    [{'case_id': 'abc', 'client_id': 'x', 'client_name': 'Ramesh Kumar'}],
    {'caseid': '123'},
    {'clientid': '9', 'client_name': 'Priya Sharma'},
    {'caseid_with_clientid': 'a::b'},
    ['personal'],
    'personal',
    'clientid',
    'caseid',
]


@pytest.mark.parametrize('payload', ASSOCIATION_PAYLOADS, ids=lambda p: str(p)[:36])
def test_case_client_payloads_are_refused_as_type_hints(payload):
    """
    Threading `draft_for` into the prompt would inject a client's NAME where a
    document type belongs. The refusal is by shape, because the chat path passes
    a genuine type label through the same argument.
    """
    assert normalize_type_hint(payload) == ''


@pytest.mark.parametrize('payload', ASSOCIATION_PAYLOADS, ids=lambda p: str(p)[:36])
def test_classification_ignores_association_payloads(payload):
    ctx = classify('draft a will for my father', payload, allow_llm=False)
    assert ctx.doc_type == 'will', 'the query should decide, not the association payload'


def test_client_name_never_becomes_a_type_hint():
    assert normalize_type_hint({'client_name': 'Rent Agreement'}) == ''


def test_chat_style_string_label_is_still_accepted():
    """tools.py passes a real label through the same argument — do not over-refuse."""
    assert normalize_type_hint('Rent Agreement') == 'Rent Agreement'
    assert classify('', 'Rent Agreement', allow_llm=False).doc_type == 'rent_lease_agreement'


@pytest.mark.parametrize('junk', [None, '', '   ', 123456, {}, [], 'x' * 200])
def test_normalize_type_hint_tolerates_junk(junk):
    assert isinstance(normalize_type_hint(junk), str)


# ---------------------------------------------------------------------------
# DraftContext round-tripping — the session stores this and refine reads it back
# ---------------------------------------------------------------------------

def test_context_round_trips_through_a_dict():
    ctx = classify('draft a legal notice for cheque bounce', allow_llm=False)
    restored = DraftContext.from_dict(ctx.to_dict())
    assert restored == ctx


def test_from_dict_rejects_unusable_payloads():
    assert DraftContext.from_dict(None) is None
    assert DraftContext.from_dict({}) is None
    assert DraftContext.from_dict({'doc_type': ''}) is None


def test_from_dict_rejects_a_type_we_no_longer_recognise():
    """A renamed playbook must force reclassification, not silently become generic."""
    assert DraftContext.from_dict({'doc_type': 'retired_type_v1'}) is None


def test_from_dict_repairs_branch_from_the_registry():
    """Branch always comes from the playbook, even if a stale one was stored."""
    restored = DraftContext.from_dict({'doc_type': 'will', 'branch': 'criminal'})
    assert restored.branch == 'testamentary'


# ---------------------------------------------------------------------------
# LLM fallback behaviour
# ---------------------------------------------------------------------------

def test_llm_is_not_called_when_keywords_suffice(monkeypatch):
    called = []
    monkeypatch.setattr(
        'ai_draft.drafting.classify._llm_classify',
        lambda q: called.append(q),
    )
    classify('draft a vakalatnama for the district court')
    assert not called, 'keyword hit should short-circuit before any LLM call'


def _patch_llm(monkeypatch, responder):
    """
    Patch chat_complete where `_llm_classify` actually resolves it.

    It does `from core import llm_client` and then `llm_client.chat_complete(...)`
    — an attribute lookup at call time — so patching the attribute on the real
    module is what intercepts it. Patching `sys.modules['core.llm_client']` does
    NOT work here, because `from core import llm_client` reads the attribute off
    the already-imported `core` package.
    """
    import core.llm_client as real

    monkeypatch.setattr(real, 'chat_complete', responder)


def test_llm_provider_failure_falls_back_to_generic(monkeypatch):
    """Classification must never be fatal — a provider outage degrades, not crashes."""
    def boom(**_kwargs):
        raise RuntimeError('provider down')

    _patch_llm(monkeypatch, boom)
    ctx = classify('an entirely ambiguous request with no routing signal', allow_llm=True)
    assert ctx.doc_type == 'generic'
    assert ctx.confidence == FALLBACK


def test_out_of_enum_llm_response_is_discarded(monkeypatch):
    """A hallucinated document type must not become a playbook lookup."""
    _patch_llm(monkeypatch, lambda **_k: '{"doc_type": "not_a_real_type"}')
    ctx = classify('an entirely ambiguous request with no routing signal', allow_llm=True)
    assert ctx.doc_type == 'generic'
    assert ctx.confidence == FALLBACK


def test_unparseable_llm_response_is_discarded(monkeypatch):
    _patch_llm(monkeypatch, lambda **_k: 'I think this is probably a will, actually.')
    ctx = classify('an entirely ambiguous request with no routing signal', allow_llm=True)
    assert ctx.doc_type == 'generic'


def test_valid_llm_response_is_accepted(monkeypatch):
    _patch_llm(monkeypatch, lambda **_k: '{"doc_type": "consumer_complaint"}')
    ctx = classify('an entirely ambiguous request with no routing signal', allow_llm=True)
    assert ctx.doc_type == 'consumer_complaint'
    assert ctx.confidence == LLM
    assert ctx.branch == 'civil'


def test_llm_response_wrapped_in_prose_is_still_parsed(monkeypatch):
    _patch_llm(monkeypatch, lambda **_k: 'Sure!\n```json\n{"doc_type": "affidavit"}\n```')
    ctx = classify('an entirely ambiguous request with no routing signal', allow_llm=True)
    assert ctx.doc_type == 'affidavit'


def test_llm_is_asked_with_a_closed_enum(monkeypatch):
    """The enum is what keeps the fallback from inventing types."""
    seen = {}

    def capture(**kwargs):
        seen.update(kwargs)
        return '{"doc_type": "generic"}'

    _patch_llm(monkeypatch, capture)
    classify('an entirely ambiguous request with no routing signal', allow_llm=True)

    system = seen['messages'][0]['content']
    for pb in playbooks.all_playbooks():
        assert pb.doc_type in system
    assert seen['app_scenario'] == 'brain:t1'
    assert seen['temperature'] == 0
