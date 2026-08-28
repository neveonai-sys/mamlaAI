"""
tests/test_draft_async.py — Phase 3: async draft generation.

Covers the two halves of the flag:

  * `initiate_drafting_session` — creates the session without generating,
    enqueues the worker, answers 'generating', and falls back to synchronous
    generation if the broker is unreachable.
  * `backfill_initial_saved_draft` — the worker filling in the saved-draft
    snapshot that the request path created empty, without ever overwriting a
    revision the user saved in the meantime.

None of these call an LLM. The generation itself is covered by
test_draft_validator.py and the eval suite.
"""

import datetime
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId

from ai_draft.routes.creatupdateAIdrafts import CreateupdatefetchAIdrafts


# ---------------------------------------------------------------------------
# backfill_initial_saved_draft
# ---------------------------------------------------------------------------

def _engine_with_session(session):
    """A CreateupdatefetchAIdrafts whose Mongo handle returns `session`."""
    engine = CreateupdatefetchAIdrafts('user_1')
    collection = MagicMock()
    collection.find_one.return_value = session
    engine.get_mongo_client_db = MagicMock(return_value=collection)
    return engine, collection


def test_backfill_copies_sections_into_the_empty_first_snapshot():
    sections = [{'section_id': 's1', 'section_name': 'enc', 'content': 'enc'}]
    engine, collection = _engine_with_session({
        'saved_drafts': [{'draft_id': 'd1', 'sections': []}],
        'draft_sections': sections,
    })

    assert engine.backfill_initial_saved_draft('64' * 12) is True

    _filter, update = collection.update_one.call_args[0]
    assert update['$set']['saved_drafts.$.sections'] == sections
    assert _filter['saved_drafts.draft_id'] == 'd1'


def test_backfill_copies_the_encrypted_shape_verbatim():
    """
    `draft_sections` is already Fernet-wrapped and `saved_drafts[].sections` is
    read back through the same `_decrypt_sections`. The backfill must therefore
    copy, never re-encrypt — double-wrapping would make the saved draft
    undecryptable while the live session still looked fine.
    """
    ciphertext = [{'section_id': 's1', 'section_name': 'gAAAAA...', 'content': 'gAAAAA...'}]
    engine, collection = _engine_with_session({
        'saved_drafts': [{'draft_id': 'd1', 'sections': []}],
        'draft_sections': ciphertext,
    })

    engine.backfill_initial_saved_draft('64' * 12)

    stored = collection.update_one.call_args[0][1]['$set']['saved_drafts.$.sections']
    assert stored is ciphertext


def test_backfill_never_overwrites_a_snapshot_the_user_already_saved():
    """The generator must not clobber a revision the user saved while waiting."""
    engine, collection = _engine_with_session({
        'saved_drafts': [{'draft_id': 'd1', 'sections': [{'content': 'user edit'}]}],
        'draft_sections': [{'content': 'generated'}],
    })

    assert engine.backfill_initial_saved_draft('64' * 12) is False
    collection.update_one.assert_not_called()


def test_backfill_is_a_noop_when_generation_produced_nothing():
    engine, collection = _engine_with_session({
        'saved_drafts': [{'draft_id': 'd1', 'sections': []}],
        'draft_sections': [],
    })

    assert engine.backfill_initial_saved_draft('64' * 12) is False
    collection.update_one.assert_not_called()


def test_backfill_is_a_noop_when_there_is_no_saved_draft_row():
    engine, collection = _engine_with_session({
        'saved_drafts': [],
        'draft_sections': [{'content': 'generated'}],
    })

    assert engine.backfill_initial_saved_draft('64' * 12) is False
    collection.update_one.assert_not_called()


def test_backfill_swallows_errors_rather_than_failing_the_draft():
    """
    The session itself holds the sections and the workspace reads those, so a
    failed backfill is a degraded sidebar entry, not a lost draft.
    """
    engine = CreateupdatefetchAIdrafts('user_1')
    engine.get_mongo_client_db = MagicMock(side_effect=RuntimeError('mongo down'))

    assert engine.backfill_initial_saved_draft('64' * 12) is False


# ---------------------------------------------------------------------------
# initiate_drafting_session — flag behaviour
# ---------------------------------------------------------------------------

@pytest.fixture
def draft_request():
    """
    A real HttpRequest — DRF's @api_view asserts on the type, so a MagicMock
    cannot reach the view body.
    """
    from django.test import RequestFactory
    request = RequestFactory().post(
        '/aidrafts/initial_request/',
        data='{"user_query": "Draft a rent arrears notice", "document_type": "legal_notice"}',
        content_type='application/json',
    )
    request.supabase_user = {'user_id': 'user_1', 'user_type': 'Client'}
    # @supabase_required honours this and hands the request straight through,
    # keeping the `supabase_user` set above rather than verifying a real token.
    request.bypass_supabase_auth = True
    return request


def _patched_view(*, async_enabled, engine, enqueue):
    """
    Patch everything initiate_drafting_session touches except the branch under
    test. Returns a context manager stack already entered by the caller's `with`.
    """
    return patch.multiple(
        'ai_draft.views',
        CreateupdatefetchAIdrafts=MagicMock(return_value=engine),
        generate_draft_async=enqueue,
        _authorize_draft_feature=MagicMock(return_value={'allowed': True}),
        _finalize_draft_quota=MagicMock(return_value={}),
    )


def _stub_engine():
    engine = MagicMock()
    engine.start_new_session.return_value = ObjectId()
    engine.start_new_session_without_ai.return_value = ObjectId()
    engine.retrieve_sections_of_draft.return_value = {'mssg': []}
    engine.auto_save_initial_draft.return_value = {
        'draft_id': 'd1',
        'saved_at': datetime.datetime.now(datetime.timezone.utc),
        'last_updated_on': datetime.datetime.now(datetime.timezone.utc),
    }
    return engine


def _call_view(request):
    """
    Call the view through its real decorator stack.

    `request.supabase_user` is set by the fixture, so @supabase_required passes
    on the already-authenticated request; @ratelimit is disabled via settings in
    the tests below so repeated calls in one run do not trip the 5/m limit.
    """
    from ai_draft.views import initiate_drafting_session
    return initiate_drafting_session(request)


def test_async_off_generates_synchronously_and_reports_completed(draft_request, settings):
    settings.DRAFT_ASYNC_ENABLED = False
    engine, enqueue = _stub_engine(), MagicMock()

    with _patched_view(async_enabled=False, engine=engine, enqueue=enqueue):
        response = _call_view(draft_request)

    engine.start_new_session.assert_called_once()
    engine.start_new_session_without_ai.assert_not_called()
    enqueue.delay.assert_not_called()
    assert b'"status": "generating"' not in response.content


def test_async_on_enqueues_and_reports_generating(draft_request, settings):
    settings.DRAFT_ASYNC_ENABLED = True
    engine, enqueue = _stub_engine(), MagicMock()

    with _patched_view(async_enabled=True, engine=engine, enqueue=enqueue):
        response = _call_view(draft_request)

    engine.start_new_session_without_ai.assert_called_once()
    engine.start_new_session.assert_not_called()
    enqueue.delay.assert_called_once()
    assert b'"status": "generating"' in response.content


def test_async_on_still_creates_the_saved_draft_row(draft_request, settings):
    """
    The sidebar lists saved_drafts. Deferring this row until the worker
    finished would make a generating draft vanish from the user's list for
    minutes — so it is created empty and backfilled later.
    """
    settings.DRAFT_ASYNC_ENABLED = True
    engine, enqueue = _stub_engine(), MagicMock()

    with _patched_view(async_enabled=True, engine=engine, enqueue=enqueue):
        _call_view(draft_request)

    engine.auto_save_initial_draft.assert_called_once()
    assert engine.auto_save_initial_draft.call_args[0][2] == []   # empty snapshot


def test_unreachable_broker_falls_back_to_synchronous_generation(draft_request, settings):
    """
    Turning the flag on must not be able to take drafting offline. A broker that
    refuses the enqueue degrades latency, not the feature.
    """
    settings.DRAFT_ASYNC_ENABLED = True
    engine = _stub_engine()
    enqueue = MagicMock()
    enqueue.delay.side_effect = OSError('connection refused')

    with _patched_view(async_enabled=True, engine=engine, enqueue=enqueue):
        response = _call_view(draft_request)

    engine.generate_draft.assert_called_once()
    assert b'"status": "generating"' not in response.content
