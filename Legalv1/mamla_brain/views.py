import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path

from bson import ObjectId
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view

from core.analytics import record_usage_event
from core.entitlements import authorize_feature_use, consume_feature_use
from core.init_clients import get_mongo_client, get_mongo_db
from core.chitchat_guard import CHITCHAT_LLM_STUB, _REPLY_ACK, check_chitchat, has_legal_signal
from core.input_sanitizer import PromptInjectionError, sanitize_user_input
from core.intent_gate import classify_intent, should_use_gate
from core.output_validator import parse_and_validate_json
from core.response_utils import error_response
from talkdoc.storage import upload_bytes
from talkdoc.tasks import ingest_document

from .auth import (
    brain_api_key_quota_payload,
    brain_api_key_required,
    charge_brain_api_key_quota,
    generate_api_key,
    is_supabase_admin,
)
from .llm_router import call_llm, get_tier_config, parse_json_response
from .prompts import (
    ISSUE_CLASSIFIER_SYSTEM,
    PROMPT_VERSION,
    QUERY_REWRITE_SYSTEM,
    build_case_companion_system,
    build_doc_qa_system,
    build_general_system,
    get_domain_profile,
)
from .retrieval import (
    knowledge_index_stats,
    merge_context,
    render_context,
    search_knowledge_base,
    search_user_docs,
)


def _db():
    return get_mongo_db()


def _json_body(request):
    try:
        return json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return {}


def _owner_id(request):
    brain_client = getattr(request, 'brain_client', {})
    return brain_client.get('owner_id')


def _app_name(request):
    return request.headers.get('X-App-Name', '').strip()


def _timestamped_filename(filename):
    original_name = Path(filename or 'document').name or 'document'
    stem = Path(original_name).stem or 'document'
    suffix = Path(original_name).suffix
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')
    return f'{stem}_{timestamp}{suffix}'


def _matter_list(matter, key):
    value = (matter or {}).get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    normalized = str(value).strip()
    return [normalized] if normalized else []


def _matter_metadata(matter):
    case_ids = _matter_list(matter, 'caseid')
    client_ids = _matter_list(matter, 'clientid')
    return {
        'case_ids': case_ids,
        'client_ids': client_ids,
        'primary_case_id': case_ids[0] if case_ids else '',
        'primary_client_id': client_ids[0] if client_ids else '',
    }


def _normalize_owned_doc_ids(owner_id, raw_doc_ids):
    ordered_ids = []
    seen_ids = set()
    for raw_doc_id in raw_doc_ids or []:
        try:
            object_id = ObjectId(raw_doc_id)
        except Exception:
            continue
        if object_id not in seen_ids:
            ordered_ids.append(object_id)
            seen_ids.add(object_id)

    if not ordered_ids:
        return []

    owned_docs = {
        doc['_id']
        for doc in _db()['rag_documents'].find(
            {'_id': {'$in': ordered_ids}, 'user_id': owner_id},
            {'_id': 1},
        )
    }
    return [object_id for object_id in ordered_ids if object_id in owned_docs]


def _serialize_doc(document):
    status = document.get('status', 'uploaded')
    doc_id = str(document['_id'])
    display_name = document.get('name_display') or document.get('name_stored') or document.get('name_original') or ''
    original_name = document.get('name_original') or display_name
    mimetype = document.get('mimetype') or mimetypes.guess_type(original_name or display_name)[0] or 'application/octet-stream'
    return {
        'id': doc_id,
        'doc_id': doc_id,
        'name': display_name,
        'original_name': original_name,
        'stored': document.get('name_stored', ''),
        'status': status,
        'ingest_stage': document.get('ingest_stage', 'queued'),
        'indexed': status == 'indexed',
        'mimetype': mimetype,
        'size': document.get('size', 0),
        'matter': document.get('matter', {}),
        'domain_key': document.get('domain_key', 'legal'),
        'created_at': str(document.get('created_at', '')),
        'updated_at': str(document.get('updated_at', '')),
    }


def _serialize_session(session):
    doc_ids = [str(doc_id) for doc_id in session.get('doc_ids', [])]
    return {
        'id': str(session['_id']),
        'title': session.get('title', ''),
        'mode': session.get('mode', 'doc_qa'),
        'domain_key': session.get('domain_key', 'legal'),
        'doc_ids': doc_ids,
        'doc_count': len(doc_ids),
        'has_docs': bool(doc_ids),
        'matter': session.get('matter', {}),
        'case_type': session.get('case_type', ''),
        'party_role': session.get('party_role', ''),
        'created_at': str(session.get('created_at', '')),
        'last_message_at': str(session.get('last_message_at', '')),
    }


def _serialize_message(message):
    payload = {
        'id': str(message['_id']),
        'role': message.get('role', ''),
        'content': message.get('content', ''),
        'citations': message.get('citations', []),
        'tier_used': message.get('tier_used', ''),
        'tokens_used': message.get('tokens_used', 0),
        'created_at': str(message.get('created_at', '')),
    }
    if 'structured_response' in message:
        payload['structured_response'] = message.get('structured_response')
    return payload


def _create_session_document(owner_id, data, app_name=''):
    domain_key = (data.get('domain_key') or 'legal').strip().lower() or 'legal'
    mode = (data.get('mode') or 'doc_qa').strip().lower() or 'doc_qa'
    matter = data.get('matter', {}) or {}
    doc_ids = _normalize_owned_doc_ids(owner_id, data.get('doc_ids', []))
    title = data.get('title') or _default_session_title(mode, doc_ids, domain_key, matter)
    return {
        'owner_id': owner_id,
        'title': title,
        'mode': mode,
        'domain_key': domain_key,
        'doc_ids': doc_ids,
        'has_docs': bool(doc_ids),
        'matter': matter,
        'case_type': data.get('case_type', ''),
        'party_role': data.get('party_role', ''),
        'metadata': data.get('metadata', {}),
        'app_name': app_name,
        'created_at': datetime.utcnow(),
        'last_message_at': datetime.utcnow(),
        'deleted': False,
    }


def _default_session_title(mode, doc_ids, domain_key, matter=None):
    profile = get_domain_profile(domain_key)
    if mode == 'case_companion':
        scope = profile['companion_name']
    elif doc_ids:
        scope = f"{profile['label']} Document Q&A"
    else:
        scope = f"{profile['label']} General Reasoning"
    if matter and matter.get('caseid'):
        case_id = matter['caseid'][0] if isinstance(matter['caseid'], list) else matter['caseid']
        scope = f'{scope} · {case_id}'
    timestamp = datetime.utcnow().strftime('%d %b %Y, %I:%M %p UTC')
    return f'{scope} · {timestamp}'


def _session_lookup(owner_id, session_id):
    try:
        object_id = ObjectId(session_id)
    except Exception:
        return None
    return _db()['brain_sessions'].find_one({'_id': object_id, 'owner_id': owner_id, 'deleted': False})


def _quota_error_response(message, quota, status):
    return JsonResponse({'error': message, 'quota': quota}, status=status)


def _authorize_internal_feature(request, feature_code):
    if getattr(request, 'brain_client', {}).get('auth_type') != 'supabase':
        return None
    return authorize_feature_use(getattr(request, 'supabase_user', None), feature_code)


def _finalize_quota(request, feature_code, decision=None):
    auth_type = getattr(request, 'brain_client', {}).get('auth_type')
    if auth_type == 'api_key':
        charge_brain_api_key_quota(request)
        return brain_api_key_quota_payload(request, feature_code)
    if auth_type == 'supabase' and decision:
        return consume_feature_use(getattr(request, 'supabase_user', None), feature_code, decision)
    return None


def _store_user_message(session, text, metadata=None):
    payload = {
        'session_id': session['_id'],
        'role': 'user',
        'content': text,
        'tier_used': 'user',
        'tokens_used': 0,
        'app_name': metadata.get('app_name', '') if metadata else '',
        'created_at': datetime.utcnow(),
    }
    if metadata:
        payload.update(metadata)
    _db()['brain_messages'].insert_one(payload)


def _store_assistant_message(session, response_text, citations, llm_response, structured_response=None):
    payload = {
        'session_id': session['_id'],
        'role': 'assistant',
        'content': response_text,
        'citations': citations,
        'tier_used': llm_response.get('tier', ''),
        'tokens_used': llm_response.get('usage', {}).get('total_tokens', 0),
        'prompt_tokens': llm_response.get('usage', {}).get('prompt_tokens', 0),
        'completion_tokens': llm_response.get('usage', {}).get('completion_tokens', 0),
        'latency_ms': llm_response.get('latency_ms', 0),
        'model': llm_response.get('model', ''),
        'provider': llm_response.get('provider', ''),
        'prompt_version': PROMPT_VERSION,
        'app_name': session.get('app_name', ''),
        'created_at': datetime.utcnow(),
    }
    if structured_response is not None:
        payload['structured_response'] = structured_response
    _db()['brain_messages'].insert_one(payload)
    _db()['brain_sessions'].update_one(
        {'_id': session['_id']},
        {'$set': {'last_message_at': datetime.utcnow()}},
    )


def _citations_from_context(context_items):
    citations = []
    for item in (context_items or [])[:5]:
        citation = item.get('citation', {}).copy()
        citation['source_type'] = item.get('source_type')
        if item.get('source_type') == 'knowledge_base':
            citation['act'] = item.get('act', '')
            citation['section'] = item.get('section_number', '')
        citations.append(citation)
    return citations


def _rewrite_query(text, domain_key):
    rewrite_messages = [
        {'role': 'system', 'content': QUERY_REWRITE_SYSTEM},
        {'role': 'user', 'content': f'Domain: {domain_key}\nQuery: {text}'},
    ]
    try:
        response = call_llm(rewrite_messages, tier='t1')
        rewritten = (response.get('text') or '').strip()
        return rewritten or text, response
    except Exception:
        return text, {'tier': 't1', 'usage': {'total_tokens': 0}, 'model': '', 'provider': ''}


def _history_messages(session, limit=None):
    history_limit = limit or get_tier_config('t2')['history_limit']
    messages = list(
        _db()['brain_messages']
        .find({'session_id': session['_id']}, {'role': 1, 'content': 1, '_id': 0})
        .sort('created_at', -1)
        .limit(history_limit)
    )
    messages.reverse()
    return messages


def _apply_doc_filters(owner_id, request):
    filt = {'user_id': owner_id}
    domain_key = request.GET.get('domain_key', '').strip()
    if domain_key:
        filt['domain_key'] = domain_key
    q = request.GET.get('q', '').strip()
    if q:
        filt['$or'] = [
            {'name_original': {'$regex': q, '$options': 'i'}},
            {'name_display': {'$regex': q, '$options': 'i'}},
            {'name_stored': {'$regex': q, '$options': 'i'}},
        ]
    return filt


@api_view(['GET'])
def health(request):
    domains = {}
    for domain_key in ('legal', 'banking', 'markets'):
        domains[domain_key] = knowledge_index_stats(domain_key)
    return JsonResponse({
        'status': 'ok',
        'service': 'mamla_brain',
        'default_provider': os.getenv('LLM_DEFAULT_PROVIDER', 'openai'),
        'tiers': {
            't1': os.getenv('BRAIN_T1_MODEL', 'meta-llama/llama-3.1-8b-instruct'),
            't2': os.getenv('BRAIN_T2_MODEL', 'anthropic/claude-3-haiku'),
            't3': os.getenv('BRAIN_T3_MODEL', 'anthropic/claude-sonnet-4-5'),
        },
        'knowledge_bases': domains,
    })


@api_view(['POST'])
@brain_api_key_required(scopes=['doc_qa'])
def upload_doc(request):
    owner_id = _owner_id(request)
    file = request.FILES.get('file')
    if not file:
        return error_response('file missing', status=400)

    matter = {}
    if request.POST.get('matter'):
        try:
            matter = json.loads(request.POST['matter'])
        except json.JSONDecodeError:
            matter = {}

    domain_key = (request.POST.get('domain_key') or 'legal').strip().lower() or 'legal'
    display_name = _timestamped_filename(file.name)
    storage = upload_bytes(owner_id, matter, display_name, file.read())
    metadata = _matter_metadata(matter)
    document = {
        'user_id': owner_id,
        'domain_key': domain_key,
        'matter': matter or {},
        'name_original': file.name,
        'name_display': display_name,
        'name_stored': storage['filename'],
        'mimetype': file.content_type,
        'size': file.size,
        'storage': storage,
        'status': 'uploaded',
        'ingest_stage': 'queued',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        **metadata,
    }
    result = _db()['rag_documents'].insert_one(document)
    ingest_document.delay(str(result.inserted_id))
    document['_id'] = result.inserted_id
    return JsonResponse(_serialize_doc(document))


@api_view(['GET'])
@brain_api_key_required(scopes=['doc_qa'])
def list_docs(request):
    owner_id = _owner_id(request)
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    pipeline = [
        {'$match': _apply_doc_filters(owner_id, request)},
        {'$sort': {'created_at': -1}},
        {'$facet': {
            'total': [{'$count': 'count'}],
            'items': [{'$skip': (page - 1) * page_size}, {'$limit': page_size}],
        }},
    ]
    out = list(_db()['rag_documents'].aggregate(pipeline))[0]
    total = out['total'][0]['count'] if out['total'] else 0
    items = [_serialize_doc(item) for item in out['items']]
    return JsonResponse({'count': total, 'results': items})


@api_view(['POST'])
@brain_api_key_required(scopes=['doc_qa'])
def create_session(request):
    owner_id = _owner_id(request)
    data = _json_body(request)
    session = _create_session_document(owner_id, data, _app_name(request))
    result = _db()['brain_sessions'].insert_one(session)
    session['_id'] = result.inserted_id
    return JsonResponse(_serialize_session(session))


@api_view(['GET'])
@brain_api_key_required(scopes=['doc_qa'])
def list_sessions(request):
    owner_id = _owner_id(request)
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    filt = {'owner_id': owner_id, 'deleted': False}
    q = request.GET.get('q', '').strip()
    if q:
        filt['title'] = {'$regex': q, '$options': 'i'}
    domain_key = request.GET.get('domain_key', '').strip()
    if domain_key:
        filt['domain_key'] = domain_key
    pipeline = [
        {'$match': filt},
        {'$sort': {'last_message_at': -1}},
        {'$facet': {
            'total': [{'$count': 'count'}],
            'items': [{'$skip': (page - 1) * page_size}, {'$limit': page_size}],
        }},
    ]
    out = list(_db()['brain_sessions'].aggregate(pipeline))[0]
    total = out['total'][0]['count'] if out['total'] else 0
    items = [_serialize_session(item) for item in out['items']]
    return JsonResponse({'count': total, 'results': items})


@api_view(['GET'])
@brain_api_key_required(scopes=['doc_qa'])
def get_messages(request, session_id):
    session = _session_lookup(_owner_id(request), session_id)
    if not session:
        return error_response('session not found', status=404)
    messages = list(_db()['brain_messages'].find({'session_id': session['_id']}).sort('created_at', 1))
    return JsonResponse({'results': [_serialize_message(message) for message in messages]})


@api_view(['DELETE'])
@brain_api_key_required(scopes=['doc_qa'])
def delete_session(request, session_id):
    session = _session_lookup(_owner_id(request), session_id)
    if not session:
        return error_response('session not found', status=404)
    _db()['brain_sessions'].update_one({'_id': session['_id']}, {'$set': {'deleted': True}})
    return JsonResponse({'message': 'deleted'})


@api_view(['POST'])
@brain_api_key_required(scopes=['doc_qa'])
@ratelimit(key='user', rate='30/m', block=True)
def send_message(request, session_id):
    owner_id = _owner_id(request)
    session = _session_lookup(owner_id, session_id)
    if not session:
        return error_response('session not found', status=404)

    data = _json_body(request)
    raw_text = (data.get('text') or data.get('query') or '').strip()
    if not raw_text:
        return error_response('query is empty', status=400)

    try:
        text = sanitize_user_input(raw_text, tier='t2')
    except PromptInjectionError as exc:
        return error_response(str(exc), status=400)

    decision = _authorize_internal_feature(request, 'brain_doc_analysis')
    if decision and not decision.get('allowed'):
        return _quota_error_response(decision['message'], decision['quota'], decision['status_code'])

    _store_user_message(session, text, {'app_name': _app_name(request)})

    # --- Tier-0 chitchat guard (zero LLM cost) ---
    is_cc, cc_reply = check_chitchat(text)
    if not is_cc and should_use_gate(text) and not has_legal_signal(text):
        # Ambiguous short input — use free model to classify intent
        if classify_intent(text) == 'chitchat':
            is_cc, cc_reply = True, _REPLY_ACK
    if is_cc:
        stub = {**CHITCHAT_LLM_STUB, 'text': cc_reply}
        _store_assistant_message(session, cc_reply, [], stub)
        return JsonResponse({
            'message': cc_reply,
            'answer': cc_reply,
            'citations': [],
            'rewritten_query': text,
            'quota': None,
        })

    rewritten_query, rewrite_response = _rewrite_query(text, session.get('domain_key', 'legal'))
    doc_ids = [str(doc_id) for doc_id in session.get('doc_ids', [])]
    doc_hits = search_user_docs(rewritten_query, owner_id, doc_ids=doc_ids, matter=session.get('matter'), k=10) if doc_ids else []
    use_knowledge_base = bool(data.get('include_knowledge_base')) or session.get('mode') == 'case_companion'
    kb_hits = search_knowledge_base(rewritten_query, session.get('domain_key', 'legal'), k=8) if use_knowledge_base else []
    merged_context = merge_context(kb_hits, doc_hits, max_items=get_tier_config('t2')['context_items'])
    context_text = render_context(merged_context, max_items=get_tier_config('t2')['context_items'])
    history_messages = _history_messages(session, limit=get_tier_config('t2')['history_limit'])

    system_prompt = build_doc_qa_system(session.get('domain_key', 'legal')) if (doc_hits or kb_hits) else build_general_system(session.get('domain_key', 'legal'))
    messages = [{'role': 'system', 'content': system_prompt}]
    for history in history_messages[:-1]:
        messages.append({'role': history['role'], 'content': history['content']})
    if context_text:
        messages.append({'role': 'user', 'content': f'Context:\n{context_text}\n\nQuestion:\n{text}'})
    else:
        messages.append({'role': 'user', 'content': text})

    llm_response = call_llm(messages, tier='t2')
    llm_response['usage']['total_tokens'] += rewrite_response.get('usage', {}).get('total_tokens', 0)
    record_usage_event(
        request, 'mamla_brain', llm_response.get('model', ''),
        llm_response['usage']['prompt_tokens'],
        llm_response['usage']['completion_tokens'],
    )
    citations = _citations_from_context(merged_context)
    _store_assistant_message(session, llm_response['text'], citations, llm_response)
    quota = _finalize_quota(request, 'brain_doc_analysis', decision)
    return JsonResponse({
        'message': llm_response['text'],
        'answer': llm_response['text'],
        'citations': citations,
        'rewritten_query': rewritten_query,
        'quota': quota,
    })


@api_view(['POST'])
@brain_api_key_required(scopes=['case_companion'])
def start_case_companion(request):
    owner_id = _owner_id(request)
    data = _json_body(request)
    payload = {
        'domain_key': (data.get('domain_key') or 'legal').strip().lower() or 'legal',
        'mode': 'case_companion',
        'doc_ids': data.get('doc_ids', []),
        'matter': data.get('matter', {}),
        'case_type': data.get('case_type', ''),
        'party_role': data.get('party_role', ''),
        'metadata': data.get('metadata', {}),
        'title': data.get('title', ''),
    }
    session = _create_session_document(owner_id, payload, _app_name(request))
    result = _db()['brain_sessions'].insert_one(session)
    session['_id'] = result.inserted_id
    return JsonResponse(_serialize_session(session))


@api_view(['POST'])
@brain_api_key_required(scopes=['case_companion'])
@ratelimit(key='user', rate='30/m', block=True)
def case_companion_advise(request, session_id):
    owner_id = _owner_id(request)
    session = _session_lookup(owner_id, session_id)
    if not session:
        return error_response('session not found', status=404)
    if session.get('mode') != 'case_companion':
        return error_response('session is not a case companion session', status=400)

    data = _json_body(request)
    raw_text = (data.get('text') or data.get('query') or data.get('facts') or '').strip()
    if not raw_text:
        return error_response('facts are required', status=400)

    try:
        text = sanitize_user_input(raw_text, tier='t3')
    except PromptInjectionError as exc:
        return error_response(str(exc), status=400)

    decision = _authorize_internal_feature(request, 'case_companion')
    if decision and not decision.get('allowed'):
        return _quota_error_response(decision['message'], decision['quota'], decision['status_code'])

    session['app_name'] = _app_name(request)
    _store_user_message(session, text, {'app_name': session['app_name']})

    # --- Tier-0 chitchat guard (zero LLM cost) ---
    is_cc, cc_reply = check_chitchat(text)
    if not is_cc and should_use_gate(text) and not has_legal_signal(text):
        if classify_intent(text) == 'chitchat':
            is_cc, cc_reply = True, _REPLY_ACK
    if is_cc:
        stub = {**CHITCHAT_LLM_STUB, 'text': cc_reply}
        _store_assistant_message(session, cc_reply, [], stub)
        quota = _finalize_quota(request, 'case_companion', decision)
        return JsonResponse({
            'message': cc_reply,
            'answer': cc_reply,
            'citations': [],
            'quota': quota,
        })

    classifier_messages = [
        {'role': 'system', 'content': ISSUE_CLASSIFIER_SYSTEM},
        {
            'role': 'user',
            'content': json.dumps({
                'domain_key': session.get('domain_key', 'legal'),
                'case_type': session.get('case_type', ''),
                'party_role': session.get('party_role', ''),
                'matter': session.get('matter', {}),
                'question': text,
            }),
        },
    ]
    t1_response = call_llm(classifier_messages, tier='t1')
    classifier_payload = parse_json_response(t1_response['text'], fallback={}) or {}
    search_query = classifier_payload.get('recommended_search_query') or text

    doc_ids = [str(doc_id) for doc_id in session.get('doc_ids', [])]
    doc_hits = search_user_docs(search_query, owner_id, doc_ids=doc_ids, matter=session.get('matter'), k=10) if doc_ids else []
    kb_hits = search_knowledge_base(search_query, session.get('domain_key', 'legal'), k=8)
    merged_context = merge_context(kb_hits, doc_hits, max_items=get_tier_config('t3')['context_items'])
    context_text = render_context(merged_context, max_items=get_tier_config('t3')['context_items'])
    citations = _citations_from_context(merged_context)

    reasoning_messages = [
        {'role': 'system', 'content': build_case_companion_system(session.get('domain_key', 'legal'))},
        {
            'role': 'user',
            'content': json.dumps({
                'session': {
                    'case_type': session.get('case_type', ''),
                    'party_role': session.get('party_role', ''),
                    'domain_key': session.get('domain_key', 'legal'),
                    'matter': session.get('matter', {}),
                },
                'classifier': classifier_payload,
                'context': context_text,
                'question': text,
            }),
        },
    ]
    t3_response = call_llm(reasoning_messages, tier='t3')
    structured = parse_and_validate_json(t3_response['text'], scenario='brain:t3', fallback=None)
    if structured is None:
        structured = {
            'summary': t3_response['text'],
            'applicable_law': [],
            'arguments_for': [],
            'arguments_against': [],
            'weaknesses': [],
            'recommended_steps': [],
            'citations': citations,
        }
    else:
        structured['citations'] = citations

    total_tokens = t1_response.get('usage', {}).get('total_tokens', 0) + t3_response.get('usage', {}).get('total_tokens', 0)
    t3_response['usage']['total_tokens'] = total_tokens
    record_usage_event(
        request, 'mamla_brain_case_companion', t3_response.get('model', ''),
        t1_response['usage']['prompt_tokens'] + t3_response['usage']['prompt_tokens'],
        t1_response['usage']['completion_tokens'] + t3_response['usage']['completion_tokens'],
    )
    _store_assistant_message(
        session,
        json.dumps(structured),
        citations,
        t3_response,
        structured_response=structured,
    )
    structured['quota'] = _finalize_quota(request, 'case_companion', decision)
    return JsonResponse(structured)


@api_view(['GET'])
@brain_api_key_required
def usage_stats(request):
    """
    Return aggregated token usage for the authenticated owner.

    Query params:
      period=daily|monthly  (default: monthly)
      feature=<str>         (optional — filter by app_name/feature)

    Response:
      {
        "period": "monthly",
        "total_tokens": 12400,
        "prompt_tokens": 8000,
        "completion_tokens": 4400,
        "avg_latency_ms": 820,
        "message_count": 42,
        "breakdown": [{"date": "2026-05-01", "tokens": 1200}, ...]
      }
    """
    from datetime import timedelta
    from core.circuit_breaker import get_circuit_breaker, PROVIDER_OPENAI, PROVIDER_OPENROUTER

    owner_id = _owner_id(request)
    period   = request.GET.get('period', 'monthly')
    feature  = request.GET.get('feature', '').strip()

    now   = datetime.utcnow()
    if period == 'daily':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    match_stage = {
        'owner_id': owner_id,
        'role': 'assistant',
        'created_at': {'$gte': start},
    }
    if feature:
        match_stage['app_name'] = feature

    # aggregate via session join
    pipeline = [
        {'$match': {'owner_id': owner_id, 'deleted': False}},
        {'$lookup': {
            'from': 'brain_messages',
            'localField': '_id',
            'foreignField': 'session_id',
            'as': 'messages',
        }},
        {'$unwind': '$messages'},
        {'$match': {
            'messages.role': 'assistant',
            'messages.created_at': {'$gte': start},
            **({'messages.app_name': feature} if feature else {}),
        }},
        {'$group': {
            '_id': None,
            'total_tokens':      {'$sum': '$messages.tokens_used'},
            'prompt_tokens':     {'$sum': '$messages.prompt_tokens'},
            'completion_tokens': {'$sum': '$messages.completion_tokens'},
            'avg_latency_ms':    {'$avg': '$messages.latency_ms'},
            'message_count':     {'$sum': 1},
        }},
    ]
    results = list(_db()['brain_sessions'].aggregate(pipeline))
    agg = results[0] if results else {}

    total_tokens  = agg.get('total_tokens', 0)
    message_count = agg.get('message_count', 0)

    # Cost warning: check against entitlement quota (rough heuristic: tokens > 75 % of 100k default)
    WARN_THRESHOLD = int(os.getenv('BRAIN_USAGE_WARN_TOKENS', '75000'))
    if total_tokens >= WARN_THRESHOLD:
        logger.warning(
            '[USAGE] owner_id=%s period=%s total_tokens=%d exceeds warn threshold=%d',
            owner_id, period, total_tokens, WARN_THRESHOLD,
        )

    return JsonResponse({
        'period':            period,
        'since':             start.isoformat() + 'Z',
        'total_tokens':      total_tokens,
        'prompt_tokens':     agg.get('prompt_tokens', 0),
        'completion_tokens': agg.get('completion_tokens', 0),
        'avg_latency_ms':    round(agg.get('avg_latency_ms') or 0),
        'message_count':     message_count,
        'usage_warning':     total_tokens >= WARN_THRESHOLD,
    })


@api_view(['POST'])
@brain_api_key_required
def generate_admin_api_key(request):
    supabase_user = getattr(request, 'supabase_user', None)
    if not supabase_user or not is_supabase_admin(supabase_user):
        return error_response('admin access required', status=403)

    data = _json_body(request)
    owner_name = (data.get('owner_name') or '').strip()
    owner_email = (data.get('owner_email') or '').strip()
    if not owner_name or not owner_email:
        return error_response('owner_name and owner_email are required', status=400)

    api_key = generate_api_key(
        owner_name=owner_name,
        owner_email=owner_email,
        plan=(data.get('plan') or 'free').strip() or 'free',
        scopes=data.get('scopes') or ['doc_qa', 'case_companion'],
        quota_monthly=data.get('quota_monthly'),
    )
    return JsonResponse({
        'id': str(api_key['_id']),
        'key_prefix': api_key['key_prefix'],
        'raw_key': api_key['raw_key'],
        'owner_id': api_key['owner_id'],
        'owner_name': api_key['owner_name'],
        'owner_email': api_key['owner_email'],
        'plan': api_key['plan'],
        'scopes': api_key['scopes'],
        'quota_monthly': api_key['quota_monthly'],
    })
