import io, json, mimetypes, os
from pathlib import Path
from datetime import datetime
from bson import ObjectId
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view
from django_ratelimit.decorators import ratelimit
from supabase_required import supabase_required  # your decorator
from core.init_clients import get_mongo_client
from core.llm_client import chat_complete
from .storage import upload_bytes
from .tasks import ingest_document, embed_texts
from .search import ensure_index, knn_search
import logging
from gridfs import GridFS

logger = logging.getLogger('django')

def _db():
    return get_mongo_client()['legaldb']


def _build_matter_filter(request):
    filt = {}
    for key in ('personal',):
        if request.GET.get(key):
            filt[f"matter.{key}"] = request.GET.get(key)
    for key in ('caseid', 'clientid'):
        vals = request.GET.getlist(key)
        if vals:
            filt[f"matter.{key}"] = {"$in": vals}
    return filt


def _friendly_doc_error(error_text):
    message = (error_text or '').strip()
    if not message:
        return ''

    lowered = message.lower()
    if 'no extractable text' in lowered:
        return 'No readable text was found in this document.'
    if 'objectid' in lowered or 'gridfs' in lowered or 'file with id' in lowered:
        return 'The stored file could not be retrieved for processing.'
    if 'extract' in lowered:
        return 'Text extraction failed for this document.'
    if 'chunk' in lowered:
        return 'The extracted text could not be prepared for indexing.'
    if 'embed' in lowered:
        return 'Embedding failed while preparing this document.'
    if 'index' in lowered:
        return 'Search indexing failed for this document.'
    return 'Document processing failed. Please try uploading it again.'


def _normalize_owned_doc_ids(user_id, raw_doc_ids):
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
            {"_id": {"$in": ordered_ids}, "user_id": user_id},
            {"_id": 1},
        )
    }
    return [object_id for object_id in ordered_ids if object_id in owned_docs]


def _serialize_session(session):
    doc_ids = [str(doc_id) for doc_id in session.get('doc_ids', [])]
    return {
        'id': str(session['_id']),
        'title': session.get('title', ''),
        'has_docs': bool(doc_ids),
        'doc_ids': doc_ids,
        'doc_count': len(doc_ids),
        'matter': session.get('matter', {}),
        'created_at': str(session.get('created_at', '')),
        'last_message_at': str(session.get('last_message_at', '')),
    }


def _default_session_title(doc_ids, matter):
    scope = 'Document Chat' if doc_ids else 'General Legal Chat'
    if matter and matter.get('caseid'):
        case_id = matter['caseid'][0] if isinstance(matter['caseid'], list) else matter['caseid']
        scope = f'Case {case_id}'
    timestamp = datetime.utcnow().strftime('%d %b %Y, %I:%M %p UTC')
    return f'{scope} · {timestamp}'


def _matter_list(matter, key):
    value = (matter or {}).get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    normalized = str(value).strip()
    return [normalized] if normalized else []


def _timestamped_filename(filename):
    original_name = Path(filename or 'document').name or 'document'
    stem = Path(original_name).stem or 'document'
    suffix = Path(original_name).suffix
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')
    return f'{stem}_{timestamp}{suffix}'


def _matter_metadata(matter):
    case_ids = _matter_list(matter, 'caseid')
    client_ids = _matter_list(matter, 'clientid')
    return {
        'case_ids': case_ids,
        'client_ids': client_ids,
        'primary_case_id': case_ids[0] if case_ids else '',
        'primary_client_id': client_ids[0] if client_ids else '',
    }


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
        'filename': display_name,
        'original_name': original_name,
        'stored': document.get('name_stored', ''),
        'status': status,
        'indexed': status == 'indexed',
        'ingest_stage': document.get('ingest_stage', 'indexed' if status == 'indexed' else 'queued'),
        'error': _friendly_doc_error(document.get('error', '')),
        'size': document.get('size', 0),
        'mimetype': mimetype,
        'matter': document.get('matter', {}),
        'primary_case_id': document.get('primary_case_id', ''),
        'primary_client_id': document.get('primary_client_id', ''),
        'case_ids': document.get('case_ids', []),
        'client_ids': document.get('client_ids', []),
        'preview_url': f'/api/talkdoc/documents/{doc_id}/file/',
        'created_at': str(document.get('created_at', '')),
        'updated_at': str(document.get('updated_at', '')),
    }


# ---------- Rename Session ----------

@api_view(['POST'])
@supabase_required
def rename_session(request, session_id: str):
    """
    body: { title: "new name" }
    """
    user_id = request.supabase_user.get('user_id')
    data = json.loads(request.body or b"{}")
    title = data.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "empty title"}, status=400)
    res = _db()['rag_chat_sessions'].update_one({"_id": ObjectId(session_id), "user_id": user_id}, {"$set": {"title": title}})
    if res.matched_count:
        return JsonResponse({"message": "renamed", "title": title})
    return JsonResponse({"error": "not found"}, status=404)

# ---------- Documents ----------

@api_view(['POST'])
@supabase_required
def upload_doc(request):
    """
    multipart form:
      file: <file>
      matter: <json string of draft_for dict (optional)>
    """
    user = request.supabase_user
    user_id = user.get('user_id')
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({"error": "file missing"}, status=400)

    matter = {}
    if request.POST.get('matter'):
        try:
            matter = json.loads(request.POST['matter'])
        except Exception:
            pass

    display_name = _timestamped_filename(file.name)
    metadata = _matter_metadata(matter)
    logger.info(f"[TALKDOC][UPLOAD] Upload requested by user={user_id} file={file.name}")
    storage = upload_bytes(user_id, matter, display_name, file.read())
    name_stored = storage["filename"]
    doc = {
        "user_id": user_id,
        "matter": matter or {},
        "name_original": file.name,
        "name_display": display_name,
        "name_stored": name_stored,
        "mimetype": file.content_type,
        "size": file.size,
        "storage": storage,
        "status": "uploaded",
        "ingest_stage": "queued",
        **metadata,
        "pages": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    res = _db()['rag_documents'].insert_one(doc)
    doc_id = str(res.inserted_id)

    ingest_document.delay(doc_id)
    logger.info(f"[TALKDOC][UPLOAD] Queued ingest for doc_id={doc_id}")

    return JsonResponse({
        "doc_id": doc_id,
        "id": doc_id,
        "name": display_name,
        "filename": display_name,
        "original_name": file.name,
        "stored": name_stored,
        "status": "uploaded",
        "ingest_stage": "queued",
        "error": "",
        "mimetype": file.content_type or mimetypes.guess_type(file.name)[0] or 'application/octet-stream',
        "matter": matter or {},
        **metadata,
        "preview_url": f'/api/talkdoc/documents/{doc_id}/file/',
        "created_at": str(doc["created_at"]),
        "updated_at": str(doc["updated_at"]),
    })


@api_view(['GET'])
@supabase_required
def document_file(request, doc_id: str):
    user_id = request.supabase_user.get('user_id')
    try:
        document = _db()['rag_documents'].find_one({"_id": ObjectId(doc_id), "user_id": user_id})
    except Exception:
        document = None

    if not document:
        return JsonResponse({"error": "document not found"}, status=404)

    file_id = document.get('storage', {}).get('file_id')
    if not file_id:
        return JsonResponse({"error": "file unavailable"}, status=404)

    try:
        gridfs_api = GridFS(get_mongo_client()['legaldb'], collection='talkdoc_files')
        file_obj = gridfs_api.get(ObjectId(file_id))
    except Exception:
        return JsonResponse({"error": "file unavailable"}, status=404)

    filename = document.get('name_display') or document.get('name_original') or document.get('name_stored') or 'document'
    content_type = document.get('mimetype') or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response = HttpResponse(file_obj.read(), content_type=content_type)
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@api_view(['DELETE'])
@supabase_required
def delete_document(request, doc_id: str):
    user_id = request.supabase_user.get('user_id')
    db = _db()

    try:
        object_id = ObjectId(doc_id)
    except Exception:
        return JsonResponse({"error": "document not found"}, status=404)

    document = db['rag_documents'].find_one({"_id": object_id, "user_id": user_id})
    if not document:
        return JsonResponse({"error": "document not found"}, status=404)

    file_id = document.get('storage', {}).get('file_id')
    if file_id:
        try:
            gridfs_api = GridFS(get_mongo_client()['legaldb'], collection='talkdoc_files')
            gridfs_api.delete(ObjectId(file_id))
        except Exception:
            logger.warning(f"[TALKDOC][DELETE] Failed to remove GridFS file for doc_id={doc_id}", exc_info=True)

    db['rag_documents'].delete_one({"_id": object_id, "user_id": user_id})

    affected_sessions = list(db['rag_chat_sessions'].find(
        {"user_id": user_id, "deleted": False, "doc_ids": object_id},
        {"_id": 1, "doc_ids": 1},
    ))
    for session in affected_sessions:
        next_doc_ids = [session_doc_id for session_doc_id in session.get('doc_ids', []) if session_doc_id != object_id]
        db['rag_chat_sessions'].update_one(
            {"_id": session['_id']},
            {"$set": {"doc_ids": next_doc_ids, "has_docs": bool(next_doc_ids)}},
        )

    return JsonResponse({"message": "document deleted", "doc_id": doc_id})

@api_view(['GET'])
@supabase_required
def list_docs(request):
    user_id = request.supabase_user.get('user_id')
    q = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)

    filt = {"user_id": user_id}
    filt.update(_build_matter_filter(request))

    col = _db()['rag_documents']
    pipeline = [{"$match": filt}]
    if q:
        pipeline += [{"$match":{"name_original":{"$regex": q, "$options": "i"}}}]
    pipeline += [
        {"$sort": {"created_at": -1}},
        {"$facet": {
            "total": [{"$count":"count"}],
            "items": [{"$skip": (page-1)*page_size}, {"$limit": page_size}]
        }}
    ]
    out = list(col.aggregate(pipeline))[0]
    total = (out["total"][0]["count"] if out["total"] else 0)
    items = [_serialize_doc(x) for x in out["items"]]
    return JsonResponse({"total": total, "items": items})

# ---------- Sessions ----------

@api_view(['POST'])
@supabase_required
def create_session(request):
    """
    body: { doc_ids: [..], matter: {...} }
    """
    user_id = request.supabase_user.get('user_id')
    data = json.loads(request.body or b"{}")
    doc_ids = _normalize_owned_doc_ids(user_id, data.get("doc_ids", []))
    matter = data.get("matter", {})

    # Allow sessions without documents

    title = data.get("title") or _default_session_title(doc_ids, matter)

    session = {
        "user_id": user_id,
        "title": title,
        "doc_ids": doc_ids,
        "has_docs": bool(doc_ids),  # Flag to track if this is a document-based chat
        "matter": matter or {},
        "model": os.getenv("RAG_MODEL", "gpt-4o"),
        "created_at": datetime.utcnow(),
        "last_message_at": datetime.utcnow(),
        "deleted": False
    }
    res = _db()['rag_chat_sessions'].insert_one(session)
    return JsonResponse({
        "session_id": str(res.inserted_id),
        "title": title,
        "doc_ids": [str(doc_id) for doc_id in doc_ids],
        "matter": matter or {},
        "has_docs": bool(doc_ids),
    })

@api_view(['GET'])
@supabase_required
def list_sessions(request):
    user_id = request.supabase_user.get('user_id')
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    q = request.GET.get('q', '').strip()

    filt = {"user_id": user_id, "deleted": False}
    if q:
        filt["title"] = {"$regex": q, "$options": "i"}

    col = _db()['rag_chat_sessions']
    pipeline = [
        {"$match": filt},
        {"$sort": {"last_message_at": -1}},
        {"$facet": {
            "total": [{"$count":"count"}],
            "items": [{"$skip": (page-1)*page_size}, {"$limit": page_size}]
        }}
    ]
    out = list(col.aggregate(pipeline))[0]
    total = (out["total"][0]["count"] if out["total"] else 0)
    items = [_serialize_session(x) for x in out["items"]]
    return JsonResponse({"total": total, "items": items})

@api_view(['GET'])
@supabase_required
def get_messages(request, session_id: str):
    user_id = request.supabase_user.get('user_id')
    session = _db()['rag_chat_sessions'].find_one({"_id": ObjectId(session_id), "user_id": user_id, "deleted": False})
    if not session:
        return JsonResponse({"error": "not found"}, status=404)

    col = _db()['rag_messages']
    msgs = list(col.find({"session_id": ObjectId(session_id)}).sort("created_at", 1))
    out = []
    for m in msgs:
        out.append({
            "id": str(m["_id"]), "role": m["role"], "content": m["content"],
            "created_at": m["created_at"], "citations": m.get("citations", [])
        })
    return JsonResponse({"messages": out})

@api_view(['DELETE'])
@supabase_required
def delete_session(request, session_id: str):
    user_id = request.supabase_user.get('user_id')
    res = _db()['rag_chat_sessions'].update_one({"_id": ObjectId(session_id), "user_id": user_id}, {"$set": {"deleted": True}})
    if res.matched_count:
        return JsonResponse({"message": "deleted"})
    return JsonResponse({"error": "not found"}, status=404)

@api_view(['POST'])
@supabase_required
def modify_session_docs(request, session_id: str):
    user_id = request.supabase_user.get('user_id')
    data = json.loads(request.body or b"{}")
    add = _normalize_owned_doc_ids(user_id, data.get("add", []))
    remove = set(data.get("remove", []))
    sess = _db()['rag_chat_sessions'].find_one({"_id": ObjectId(session_id), "user_id": user_id, "deleted": False})
    if not sess: return JsonResponse({"error": "not found"}, status=404)

    if remove and _db()['rag_messages'].count_documents({"session_id": sess["_id"]}, limit=1) > 0:
        return JsonResponse({"error": "session documents cannot be removed after chat has started"}, status=400)

    doc_ids = [doc_id for doc_id in sess.get("doc_ids", []) if str(doc_id) not in remove]
    for doc_id in add:
        if doc_id not in doc_ids:
            doc_ids.append(doc_id)

    _db()['rag_chat_sessions'].update_one(
        {"_id": sess["_id"]},
        {"$set": {"doc_ids": doc_ids, "has_docs": bool(doc_ids), "last_message_at": sess.get("last_message_at", datetime.utcnow())}},
    )
    return JsonResponse({"message":"updated", "doc_ids": [str(doc_id) for doc_id in doc_ids], "has_docs": bool(doc_ids)})

# ---------- Chat ----------

@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='20/m', block=True)
def send_message(request, session_id: str):
    """
    body: { text: "..." }
    """
    user_id = request.supabase_user.get('user_id')
    data = json.loads(request.body or b"{}")
    text = data.get("text","").strip()
    if not text:
        return JsonResponse({"error":"empty"}, status=400)

    db = _db()
    sess = db['rag_chat_sessions'].find_one({"_id": ObjectId(session_id), "user_id": user_id, "deleted": False})
    if not sess: return JsonResponse({"error":"not found"}, status=404)

    # 1) save user message
    um = {"session_id": sess["_id"], "role": "user", "content": text, "created_at": datetime.utcnow()}
    db['rag_messages'].insert_one(um)

    # 2) retrieve context only for document-based chats
    top_context = ""
    cli_hits = []
    
    if sess.get("has_docs"):  # Only do document search if session has documents
        ensure_index()
        qvec = embed_texts([text])[0]
        cli_hits = knn_search(ensure_index(), qvec, user_id=user_id,
                           doc_ids=[str(d) for d in sess["doc_ids"]], matter=sess.get("matter"), k=24)
        top_context = "\n\n".join([f"[{h['name_stored']} p.{h.get('page') or '?'}]\n{h['text']}" for h in cli_hits[:10]])

    # 3) Select appropriate system prompt based on session type
    if sess.get("has_docs"):
        system = (
            "You are a professional legal research assistant for Mamla.AI. Your role is to help lawyers and their clients understand legal documents.\n\n"
            "IMPORTANT GUIDELINES:\n"
            "1. ONLY answer questions related to the provided legal documents and legal matters\n"
            "2. If asked about non-legal topics, politely decline and redirect to legal questions\n"
            "3. Use clear, professional language suitable for both lawyers and non-lawyers\n"
            "4. Always cite specific documents and page numbers when providing information\n"
            "5. Be thorough but concise - include all important details from the documents\n"
            "6. Structure responses with bullet points and clear headings for readability\n"
            "7. Highlight critical information like dates, parties, obligations, and risks\n"
            "8. If information is missing or unclear, explicitly state what needs clarification\n\n"
            "FORMAT YOUR RESPONSES:\n"
            "- Start with a brief summary\n"
            "- Use bullet points for key details\n"
            "- Always cite sources as (Document Name · Page X)\n"
            "- End with any important warnings or recommendations\n\n"
            "Remember: Focus ONLY on legal matters. Decline politely if asked about unrelated topics."
        )
    else:
        system = (
            "You are a professional legal assistant for Mamla.AI. You provide information about Indian legal procedures, laws, and general legal concepts.\n\n"
            "IMPORTANT GUIDELINES:\n"
            "1. ONLY answer questions about legal matters, procedures, and laws\n"
            "2. If asked about non-legal topics, politely decline: 'I can only assist with legal matters. Please ask a question related to law, legal procedures, or your legal documents.'\n"
            "3. Use clear, professional language that both lawyers and clients can understand\n"
            "4. Always clarify this is GENERAL legal information, NOT specific legal advice\n"
            "5. Recommend consulting a qualified lawyer for case-specific advice\n"
            "6. Focus on Indian legal system and procedures\n"
            "7. Be helpful but always maintain professional boundaries\n\n"
            "FORMAT YOUR RESPONSES:\n"
            "- Use simple, clear language\n"
            "- Include relevant sections of law when applicable\n"
            "- Suggest next steps or actions when appropriate\n"
            "- Always add: 'Note: This is general information. Please consult a lawyer for specific legal advice.'\n\n"
            "Remember: Strictly limit responses to legal topics only."
        )
    
    # Retrieve conversation history from database
    history_msgs = list(db['rag_messages'].find(
        {"session_id": sess["_id"]},
        {"role": 1, "content": 1, "_id": 0}
    ).sort("created_at", 1).limit(20))  # Last 20 messages for context
    
    # Build messages array with system prompt, history, and current question
    messages = [{"role": "system", "content": system}]
    
    # Add conversation history (excluding the message we just saved)
    for msg in history_msgs[:-1]:  # Exclude the last one (current user message we just saved)
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current user message with context (for document-based) or plain (for general chat)
    if sess.get("has_docs"):
        messages.append({"role": "user", "content": f"Context:\n{top_context}\n\nQuestion:\n{text}"})
    else:
        messages.append({"role": "user", "content": text})

    # 4) call LLM via centralized client
    app_scenario = 'talkdoc:rag' if sess.get('has_docs') else 'talkdoc:general'
    answer = chat_complete(messages=messages, app_scenario=app_scenario, temperature=0.2)

    # 5) citations only for document-based chats
    citations = []
    if sess.get("has_docs"):
        citations = [{"doc_id": h["doc_id"], "doc_name": h["name_stored"], "page": h.get("page"), "score": h["score"], "snippet": (h["text"][:320] + "…")} for h in cli_hits[:5]]

    # 6) store assistant message
    am = {"session_id": sess["_id"], "role": "assistant", "content": answer, "citations": citations, "created_at": datetime.utcnow()}
    db['rag_messages'].insert_one(am)
    db['rag_chat_sessions'].update_one({"_id": sess["_id"]}, {"$set": {"last_message_at": datetime.utcnow()}})

    return JsonResponse({"message": answer, "citations": citations})


# ── New REST-compatible views ──────────────────────────────────────────────────

@api_view(['GET'])
@supabase_required
def documents_list(request):
    """GET /api/talkdoc/documents/ — returns {results, count}"""
    user_id = request.supabase_user.get('user_id')
    q = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)

    filt = {"user_id": user_id}
    filt.update(_build_matter_filter(request))
    col = _db()['rag_documents']
    pipeline = [{"$match": filt}]
    if q:
        pipeline += [{"$match": {"$or": [
            {"name_original": {"$regex": q, "$options": "i"}},
            {"name_display": {"$regex": q, "$options": "i"}},
            {"name_stored": {"$regex": q, "$options": "i"}},
        ]}}]
    pipeline += [
        {"$sort": {"created_at": -1}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "items": [{"$skip": (page - 1) * page_size}, {"$limit": page_size}]
        }}
    ]
    out = list(col.aggregate(pipeline))[0]
    total = (out["total"][0]["count"] if out["total"] else 0)
    items = [_serialize_doc(x) for x in out["items"]]
    return JsonResponse({"results": items, "count": total})


@api_view(['GET'])
@supabase_required
def sessions_list_v2(request):
    """GET /api/talkdoc/sessions/ — returns {results, count}"""
    user_id = request.supabase_user.get('user_id')
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    q = request.GET.get('q', '').strip()

    filt = {"user_id": user_id, "deleted": False}
    if q:
        filt["title"] = {"$regex": q, "$options": "i"}

    col = _db()['rag_chat_sessions']
    pipeline = [
        {"$match": filt},
        {"$sort": {"last_message_at": -1}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "items": [{"$skip": (page - 1) * page_size}, {"$limit": page_size}]
        }}
    ]
    out = list(col.aggregate(pipeline))[0]
    total = (out["total"][0]["count"] if out["total"] else 0)
    items = [_serialize_session(x) for x in out["items"]]
    return JsonResponse({"results": items, "count": total})


@api_view(['GET'])
@supabase_required
def session_messages_v2(request):
    """GET /api/talkdoc/session_messages/?session_id=X"""
    session_id = request.GET.get('session_id', '').strip()
    if not session_id:
        return JsonResponse({"error": "session_id required"}, status=400)
    user_id = request.supabase_user.get('user_id')
    session = _db()['rag_chat_sessions'].find_one({"_id": ObjectId(session_id), "user_id": user_id, "deleted": False})
    if not session:
        return JsonResponse({"error": "session not found"}, status=404)

    col = _db()['rag_messages']
    msgs = list(col.find({"session_id": ObjectId(session_id)}).sort("created_at", 1))
    results = [{
        "id": str(m["_id"]), "role": m["role"], "content": m["content"],
        "created_at": str(m.get("created_at", "")), "citations": m.get("citations", [])
    } for m in msgs]
    return JsonResponse({"results": results})


@api_view(['POST'])
@supabase_required
def upload_file(request):
    """POST /api/talkdoc/upload/ — multipart: file + matter(optional JSON string)"""
    user = request.supabase_user
    user_id = user.get('user_id')
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({"error": "file missing"}, status=400)

    matter = {}
    if request.POST.get('matter'):
        try:
            matter = json.loads(request.POST['matter'])
        except Exception:
            pass

    display_name = _timestamped_filename(file.name)
    metadata = _matter_metadata(matter)
    logger.info(f"[TALKDOC][UPLOAD] Upload requested by user={user_id} file={file.name}")
    storage = upload_bytes(user_id, matter, display_name, file.read())
    name_stored = storage["filename"]
    doc = {
        "user_id": user_id,
        "matter": matter or {},
        "name_original": file.name,
        "name_display": display_name,
        "name_stored": name_stored,
        "mimetype": file.content_type,
        "size": file.size,
        "storage": storage,
        "status": "uploaded",
        "ingest_stage": "queued",
        **metadata,
        "pages": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    res = _db()['rag_documents'].insert_one(doc)
    doc_id = str(res.inserted_id)
    ingest_document.delay(doc_id)
    logger.info(f"[TALKDOC][UPLOAD] Queued ingest for doc_id={doc_id}")
    return JsonResponse({
        "doc_id": doc_id,
        "id": doc_id,
        "name": display_name,
        "filename": display_name,
        "original_name": file.name,
        "stored": name_stored,
        "status": "uploaded",
        "ingest_stage": "queued",
        "error": "",
        "mimetype": file.content_type or mimetypes.guess_type(file.name)[0] or 'application/octet-stream',
        "matter": matter or {},
        **metadata,
        "preview_url": f'/api/talkdoc/documents/{doc_id}/file/',
        "created_at": str(doc["created_at"]),
        "updated_at": str(doc["updated_at"]),
    })


@api_view(['POST'])
@supabase_required
def create_session_v2(request):
    """POST /api/talkdoc/create_session/ — {doc_ids, title, matter} → {session_id, id, title}"""
    user_id = request.supabase_user.get('user_id')
    data = json.loads(request.body or b"{}")
    doc_ids = _normalize_owned_doc_ids(user_id, data.get("doc_ids", []))
    matter = data.get("matter", {})
    title = data.get("title") or _default_session_title(doc_ids, matter)

    session = {
        "user_id": user_id,
        "title": title,
        "doc_ids": doc_ids,
        "has_docs": bool(doc_ids),
        "matter": matter or {},
        "model": os.getenv("RAG_MODEL", "gpt-4o"),
        "created_at": datetime.utcnow(),
        "last_message_at": datetime.utcnow(),
        "deleted": False
    }
    res = _db()['rag_chat_sessions'].insert_one(session)
    sid = str(res.inserted_id)
    return JsonResponse({
        "session_id": sid,
        "id": sid,
        "title": title,
        "doc_ids": [str(doc_id) for doc_id in doc_ids],
        "matter": matter or {},
        "has_docs": bool(doc_ids),
    })


@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='20/m', block=True)
def query_v2(request):
    """POST /api/talkdoc/query/ — {session_id, query} → {answer, citations, message}"""
    user_id = request.supabase_user.get('user_id')
    data = json.loads(request.body or b"{}")
    session_id = data.get("session_id", "").strip()
    text = (data.get("query") or data.get("text", "")).strip()
    if not session_id:
        return JsonResponse({"error": "session_id required"}, status=400)
    if not text:
        return JsonResponse({"error": "query is empty"}, status=400)

    db = _db()
    sess = db['rag_chat_sessions'].find_one({"_id": ObjectId(session_id), "user_id": user_id, "deleted": False})
    if not sess:
        return JsonResponse({"error": "session not found"}, status=404)

    session_doc_ids = [str(doc_id) for doc_id in sess.get("doc_ids", [])]

    um = {"session_id": sess["_id"], "role": "user", "content": text, "created_at": datetime.utcnow()}
    db['rag_messages'].insert_one(um)

    top_context = ""
    cli_hits = []
    if session_doc_ids:
        ensure_index()
        qvec = embed_texts([text])[0]
        cli_hits = knn_search(ensure_index(), qvec, user_id=user_id, doc_ids=session_doc_ids, matter=sess.get("matter"), k=24)
        top_context = "\n\n".join([f"[{h['name_stored']} p.{h.get('page') or '?'}]\n{h['text']}" for h in cli_hits[:10]])

    if session_doc_ids:
        system = (
            "You are a professional legal research assistant for Mamla.AI. "
            "Answer ONLY from the provided document context. Cite sources as (Document · Page X). "
            "Stick to legal matters only."
        )
    else:
        system = (
            "You are a professional legal assistant for Mamla.AI specialising in Indian law. "
            "Answer only legal questions. Always add: 'Note: This is general information. Please consult a qualified advocate for specific advice.'"
        )

    history_msgs = list(db['rag_messages'].find(
        {"session_id": sess["_id"]}, {"role": 1, "content": 1, "_id": 0}
    ).sort("created_at", 1).limit(20))

    messages = [{"role": "system", "content": system}]
    for msg in history_msgs[:-1]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    if top_context:
        messages.append({"role": "user", "content": f"Context:\n{top_context}\n\nQuestion:\n{text}"})
    else:
        messages.append({"role": "user", "content": text})

    app_scenario = 'talkdoc:rag' if session_doc_ids else 'talkdoc:general'
    answer = chat_complete(messages=messages, app_scenario=app_scenario, temperature=0.2)

    citations = []
    if cli_hits:
        citations = [{"doc_id": h["doc_id"], "doc_name": h["name_stored"], "page": h.get("page"), "score": h["score"], "snippet": (h["text"][:320] + "…")} for h in cli_hits[:5]]

    am = {"session_id": sess["_id"], "role": "assistant", "content": answer, "citations": citations, "created_at": datetime.utcnow()}
    db['rag_messages'].insert_one(am)
    db['rag_chat_sessions'].update_one({"_id": sess["_id"]}, {"$set": {"last_message_at": datetime.utcnow()}})

    return JsonResponse({"answer": answer, "message": answer, "citations": citations})
