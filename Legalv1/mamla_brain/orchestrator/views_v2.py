"""
MamlaAI Chat (v2) HTTP views — the unified chat surface.

Endpoints (all under /api/brain/v2/):
  POST sessions/                      create a chat thread
  GET  sessions/list/                 list threads
  GET  sessions/<id>/messages/        full transcript
  POST sessions/<id>/chat/            one turn, non-streaming (JSON)
  POST sessions/<id>/chat/stream/     one turn, streamed as Server-Sent Events

Both chat paths share the same guardrail prelude (prompt-injection sanitiser →
chitchat guard → intent gate) and the same orchestration loop; the only
difference is whether events are collected into one JSON response or forwarded
as SSE. Capability routing, the draft tool, and chat-wide citation grounding
live in the loop (`orchestrator/loop.py`).
"""
import json
import logging

from django.http import JsonResponse, StreamingHttpResponse
from django_ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view

from core.chitchat_guard import (
    CHITCHAT_LLM_STUB,
    _REPLY_ACK,
    check_chitchat,
    has_legal_signal,
)
from core.input_sanitizer import PromptInjectionError, sanitize_user_input
from core.intent_gate import classify_intent, should_use_gate
from core.response_utils import error_response

from ..auth import brain_api_key_required
from ..llm_router import get_tier_config
from ..views import _authorize_internal_feature, _finalize_quota
from . import loop, store

logger = logging.getLogger('django')

# Metering: reuse existing entitlement feature codes rather than adding a new
# per-plan key. A premium turn (top OpenRouter model) bills the expensive
# case_companion bucket; a normal turn bills general_legal_chat. Per-capability
# billing (draft/doc_qa) is a future refinement the product owner can tune.
def _feature_code_for(selection):
    return 'case_companion' if selection.get('premium') else 'general_legal_chat'


# Wallet overage cost by model tier, reflecting real per-token OpenRouter cost
# differences (t1 llama ~free, t2 haiku-4.5, t3 sonnet-5, premium opus-4.8).
# Only overrides the WALLET charge once included-quota is exhausted — included
# quota itself still counts 1 message per turn regardless of tier.
CHAT_TIER_OVERAGE_CREDIT_COST = {'t1': 1, 't2': 2, 't3': 3, 'premium': 6}


def _owner_id(request):
    return getattr(request, 'brain_client', {}).get('owner_id')


def _json_body(request):
    try:
        return json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return {}


def _app_name(request):
    return request.headers.get('X-App-Name', '').strip()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@api_view(['POST'])
@brain_api_key_required(scopes=['doc_qa'])
def create_session(request):
    session = store.create_session(_owner_id(request), _json_body(request), _app_name(request))
    return JsonResponse(store.serialize_session(session))


@api_view(['GET'])
@brain_api_key_required(scopes=['doc_qa'])
def list_sessions(request):
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    total, items = store.list_sessions(_owner_id(request), page, page_size)
    return JsonResponse({'count': total, 'results': items})


@api_view(['GET'])
@brain_api_key_required(scopes=['doc_qa'])
def get_messages(request, session_id):
    session = store.lookup_session(_owner_id(request), session_id)
    if not session:
        return error_response('session not found', status=404)
    return JsonResponse({'results': store.list_messages(session)})


@api_view(['PATCH', 'DELETE'])
@brain_api_key_required(scopes=['doc_qa'])
def session_detail(request, session_id):
    """Rename (PATCH {title}) or soft-delete (DELETE) a chat thread."""
    owner_id = _owner_id(request)
    if request.method == 'DELETE':
        if not store.soft_delete_session(owner_id, session_id):
            return error_response('session not found', status=404)
        return JsonResponse({'status': 'deleted', 'id': session_id})

    title = (_json_body(request).get('title') or '').strip()
    if not title:
        return error_response('title is required', status=400)
    session = store.rename_session(owner_id, session_id, title)
    if not session:
        return error_response('session not found', status=404)
    return JsonResponse(store.serialize_session(session))


# ---------------------------------------------------------------------------
# Usage summary — per-tier token/credit breakdown for the Wallet page.
# ---------------------------------------------------------------------------
@api_view(['GET'])
@brain_api_key_required(scopes=['doc_qa'])
def usage_summary(request):
    if getattr(request, 'brain_client', {}).get('auth_type') != 'supabase':
        return error_response('not available for this client', status=403)

    from core.init_clients import get_mongo_db

    owner_id = _owner_id(request)
    pipeline = [
        {'$match': {'owner_id': owner_id, 'role': 'assistant'}},
        {'$group': {
            '_id': {'tier': '$tier_used', 'premium': '$premium', 'model': '$model'},
            'messages': {'$sum': 1},
            'tokens': {'$sum': '$tokens_used'},
            'credits_charged': {'$sum': '$credits_charged'},
        }},
    ]
    rows = list(get_mongo_db()[store.MESSAGES].aggregate(pipeline))
    by_tier = [
        {
            'tier': row['_id'].get('tier', ''),
            'premium': bool(row['_id'].get('premium')),
            'model': row['_id'].get('model', ''),
            'messages': row['messages'],
            'tokens': row['tokens'],
            'credits_charged': row['credits_charged'],
        }
        for row in rows
    ]
    totals = {
        'messages': sum(r['messages'] for r in by_tier),
        'tokens': sum(r['tokens'] for r in by_tier),
        'credits_charged': sum(r['credits_charged'] for r in by_tier),
    }
    return JsonResponse({'by_tier': by_tier, 'totals': totals})


# ---------------------------------------------------------------------------
# Mid-chat document upload — reuses the talkdoc storage + ingest pipeline and
# attaches the doc to this thread so the doc_qa tool can scope to it.
# ---------------------------------------------------------------------------
@api_view(['POST'])
@brain_api_key_required(scopes=['doc_qa'])
def upload_doc(request, session_id):
    from datetime import datetime
    from pathlib import Path
    from talkdoc.storage import upload_bytes
    from talkdoc.tasks import ingest_document

    owner_id = _owner_id(request)
    session = store.lookup_session(owner_id, session_id)
    if not session:
        return error_response('session not found', status=404)

    file = request.FILES.get('file')
    if not file:
        return error_response('file missing', status=400)

    matter = session.get('matter', {}) or {}
    domain_key = session.get('domain_key', 'legal')
    stem = Path(file.name or 'document').stem or 'document'
    suffix = Path(file.name or '').suffix
    display_name = f"{stem}_{datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}{suffix}"
    storage = upload_bytes(owner_id, matter, display_name, file.read())
    document = {
        'user_id': owner_id, 'domain_key': domain_key, 'matter': matter,
        'name_original': file.name, 'name_display': display_name,
        'name_stored': storage['filename'], 'mimetype': file.content_type,
        'size': file.size, 'storage': storage, 'status': 'uploaded',
        'ingest_stage': 'queued', 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow(),
    }
    from core.init_clients import get_mongo_db
    result = get_mongo_db()['rag_documents'].insert_one(document)
    doc_id = str(result.inserted_id)
    ingest_document.delay(doc_id)
    store.attach_doc(session['_id'], doc_id)
    return JsonResponse({
        'doc_id': doc_id, 'name': file.name, 'status': 'uploaded',
        'ingest_stage': 'queued',
        'note': 'Indexing in progress — ask about this document in a few seconds.',
    })


# ---------------------------------------------------------------------------
# In-chat draft canvas — read/re-sync + write-through a single section to the
# ai_draft engine. The engine's section methods are keyed by draft session id
# only (no owner check), so we verify ownership here before touching anything.
# ---------------------------------------------------------------------------
def _owned_draft_engine(owner_id, draft_session_id):
    """Return (engine, error_response|None). Ownership-guards the draft."""
    from bson import ObjectId
    from bson.errors import InvalidId
    from ai_draft.routes.creatupdateAIdrafts import CreateupdatefetchAIdrafts

    engine = CreateupdatefetchAIdrafts(owner_id)
    try:
        object_id = ObjectId(draft_session_id)
    except (InvalidId, TypeError):
        return None, error_response('draft not found', status=404)
    collection = engine.get_mongo_client_db()
    if collection == '' or not collection.find_one({'_id': object_id, 'user_id': owner_id}, {'_id': 1}):
        return None, error_response('draft not found', status=404)
    return engine, None


def _serialize_sections(raw):
    """Normalise engine section output to [{section_id, section_name, content}]."""
    raw_list = raw.get('mssg') if isinstance(raw, dict) else raw
    if not isinstance(raw_list, list):
        return []
    return [
        {'section_id': s.get('section_id', ''), 'section_name': s.get('section_name', ''),
         'content': s.get('content', '')}
        for s in raw_list if isinstance(s, dict)
    ]


@api_view(['GET'])
@brain_api_key_required(scopes=['doc_qa'])
def get_draft_sections(request, draft_session_id):
    """Live sections for a chat-created draft — used to re-sync the canvas."""
    engine, err = _owned_draft_engine(_owner_id(request), draft_session_id)
    if err is not None:
        return err
    sections = _serialize_sections(engine.retrieve_sections_of_draft(draft_session_id))
    return JsonResponse({'draft_session_id': draft_session_id, 'sections': sections})


@api_view(['POST'])
@brain_api_key_required(scopes=['doc_qa'])
def update_draft_section(request, draft_session_id):
    """Write-through one edited section from the in-chat canvas."""
    engine, err = _owned_draft_engine(_owner_id(request), draft_session_id)
    if err is not None:
        return err
    body = _json_body(request)
    section_id = (body.get('section_id') or '').strip()
    if not section_id:
        return error_response('section_id is required', status=400)
    result = engine.update_specific_section_of_the_draft(
        draft_session_id, section_id,
        body.get('section_name', ''), body.get('content', ''),
    )
    if not (result or {}).get('mssg'):
        return error_response('section not found', status=404)
    sections = _serialize_sections(engine.retrieve_sections_of_draft(draft_session_id))
    return JsonResponse({'status': 'saved', 'draft_session_id': draft_session_id, 'sections': sections})


# ---------------------------------------------------------------------------
# Shared guardrail prelude
# ---------------------------------------------------------------------------
class _Prelude:
    """Outcome of the shared prelude: a ready turn, a chitchat short-circuit,
    or an early error response."""
    def __init__(self, session=None, text=None, selection=None, tier_cfg=None,
                 history=None, chitchat=None, error=None, feature_code=None, decision=None):
        self.session = session
        self.text = text
        self.selection = selection
        self.tier_cfg = tier_cfg
        self.history = history
        self.chitchat = chitchat
        self.error = error
        self.feature_code = feature_code
        self.decision = decision


def _prelude(request, session_id):
    owner_id = _owner_id(request)
    session = store.lookup_session(owner_id, session_id)
    if not session:
        return _Prelude(error=error_response('session not found', status=404))

    data = _json_body(request)
    raw_text = (data.get('text') or data.get('query') or '').strip()
    if not raw_text:
        return _Prelude(error=error_response('message is empty', status=400))

    selection = store.resolve_model_selection(
        level=data.get('model_level') or session.get('model_level'),
        premium=bool(data.get('premium')),
    )
    try:
        text = sanitize_user_input(raw_text, tier=selection['tier'])
    except PromptInjectionError as exc:
        return _Prelude(error=error_response(str(exc), status=400))

    # Entitlement gate (supabase users only; api-key callers metered separately)
    feature_code = _feature_code_for(selection)
    decision = _authorize_internal_feature(request, feature_code)
    if decision and decision.get('charge_source') == 'wallet':
        decision['wallet_credits_charged'] = CHAT_TIER_OVERAGE_CREDIT_COST.get(
            selection['tier'], decision['wallet_credits_charged'],
        )
    if decision and not decision.get('allowed'):
        return _Prelude(error=JsonResponse(
            {'error': decision['message'], 'quota': decision['quota']},
            status=decision['status_code'],
        ))

    store.store_user_message(session, text, _app_name(request))
    # Name a still-default thread after its first substantive message so the
    # sidebar is readable without a manual rename (no-op once renamed).
    store.set_title_if_default(session['_id'], text)

    # A reply to a pending draft confirmation ("yes", "use placeholders", or the
    # details themselves) must always reach the loop — the chitchat guard has no
    # notion of conversation state and would otherwise swallow a bare "yes" as an
    # acknowledgement ("Got it...") and silently drop the draft flow.
    if not session.get('pending_draft'):
        is_cc, cc_reply = check_chitchat(text)
        if not is_cc and should_use_gate(text) and not has_legal_signal(text):
            if classify_intent(text) == 'chitchat':
                is_cc, cc_reply = True, _REPLY_ACK
        if is_cc:
            stub = {**CHITCHAT_LLM_STUB, 'text': cc_reply}
            store.store_assistant_message(session, cc_reply, stub)
            return _Prelude(chitchat=cc_reply)

    tier_cfg = get_tier_config(selection['tier'])
    # history_messages already includes the just-stored user turn; drop it (the
    # loop appends the current user message itself).
    history = store.history_messages(session, limit=tier_cfg['history_limit'])[:-1]
    return _Prelude(session=session, text=text, selection=selection, tier_cfg=tier_cfg,
                    history=history, feature_code=feature_code, decision=decision)


def _persist_done(prelude, done):
    """Store the assistant message from a loop 'done' event."""
    store.store_assistant_message(
        prelude.session,
        done.get('text', ''),
        {'tier': prelude.selection['tier'],
         'model': done.get('model') or prelude.selection.get('model') or '',
         'provider': prelude.selection.get('provider') or ''},
        citations=done.get('citations', []),
        tool_trace=done.get('tool_trace', []),
        artifacts=done.get('artifacts', []),
        capability=done.get('capability', ''),
        premium=bool(done.get('premium', prelude.selection.get('premium'))),
        credits_charged=(prelude.decision or {}).get('wallet_credits_charged', 0),
    )


# ---------------------------------------------------------------------------
# Chat turn — non-streaming (collects the loop's events into one JSON payload)
# ---------------------------------------------------------------------------
@api_view(['POST'])
@brain_api_key_required(scopes=['doc_qa'])
@ratelimit(key='user', rate='30/m', block=True)
def chat(request, session_id):
    pre = _prelude(request, session_id)
    if pre.error is not None:
        return pre.error
    if pre.chitchat is not None:
        return JsonResponse({'message': pre.chitchat, 'answer': pre.chitchat,
                             'citations': [], 'tool_trace': [], 'artifacts': []})

    done = None
    error_msg = None
    for event in loop.run_turn(pre.session, pre.text, pre.selection, pre.history, pre.tier_cfg):
        if event['type'] == 'done':
            done = event
        elif event['type'] == 'error':
            error_msg = event['message']

    if done is None:
        return error_response(error_msg or 'the assistant is temporarily unavailable, please retry', status=503)

    _persist_done(pre, done)
    quota = _finalize_quota(request, pre.feature_code, pre.decision)
    return JsonResponse({
        'message': done['text'], 'answer': done['text'],
        'citations': done.get('citations', []),
        'tool_trace': done.get('tool_trace', []),
        'artifacts': done.get('artifacts', []),
        'capability': done.get('capability', ''),
        'model': done.get('model', ''),
        'premium': bool(done.get('premium', False)),
        'model_level': pre.selection['level'],
        'quota': quota,
    })


# ---------------------------------------------------------------------------
# Chat turn — streaming (Server-Sent Events)
# ---------------------------------------------------------------------------
def _sse(event: dict) -> str:
    return f'data: {json.dumps(event, ensure_ascii=False)}\n\n'


@api_view(['POST'])
@brain_api_key_required(scopes=['doc_qa'])
@ratelimit(key='user', rate='30/m', block=True)
def chat_stream(request, session_id):
    pre = _prelude(request, session_id)
    if pre.error is not None:
        return pre.error

    def event_stream():
        if pre.chitchat is not None:
            yield _sse({'type': 'token', 'text': pre.chitchat})
            yield _sse({'type': 'done', 'text': pre.chitchat, 'tool_trace': [], 'citations': [], 'artifacts': []})
            return
        try:
            for event in loop.run_turn(pre.session, pre.text, pre.selection, pre.history, pre.tier_cfg):
                yield _sse(event)
                if event['type'] == 'done':
                    _persist_done(pre, event)
                    _finalize_quota(request, pre.feature_code, pre.decision)
        except Exception as exc:  # never leave the stream hanging
            logger.error('[MamlaAI-CHAT][stream] %s', exc)
            yield _sse({'type': 'error', 'message': 'the assistant is temporarily unavailable, please retry'})

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # disable nginx buffering so tokens flush
    return response
