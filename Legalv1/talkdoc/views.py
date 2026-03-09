import io, json, os
from datetime import datetime
from bson import ObjectId
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django_ratelimit.decorators import ratelimit
from supabase_required import supabase_required  # your decorator
from core.init_clients import get_mongo_client
from core.llm_client import chat_complete
from .storage import upload_bytes
from .tasks import ingest_document, embed_texts
from .search import ensure_index, knn_search

def _db():
    return get_mongo_client()['legaldb']


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

    storage = upload_bytes(user_id, matter, file.name, file.read())
    name_stored = storage["filename"]
    doc = {
        "user_id": user_id,
        "matter": matter or {},
        "name_original": file.name,
        "name_stored": name_stored,
        "mimetype": file.content_type,
        "size": file.size,
        "storage": storage,
        "status": "uploaded",
        "pages": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    res = _db()['rag_documents'].insert_one(doc)
    doc_id = str(res.inserted_id)

    # async ingest
    ingest_document.delay(doc_id)

    return JsonResponse({"doc_id": doc_id, "name": name_stored})

@api_view(['GET'])
@supabase_required
def list_docs(request):
    user_id = request.supabase_user.get('user_id')
    q = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)

    filt = {"user_id": user_id}
    for k in ('personal',):
        if request.GET.get(k):
            filt[f"matter.{k}"] = request.GET.get(k)
    for k in ('caseid', 'clientid'):
        vals = request.GET.getlist(k)
        if vals:
            filt[f"matter.{k}"] = {"$in": vals}

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
    items = [{
        "id": str(x["_id"]), "name": x["name_original"], "stored": x["name_stored"],
        "status": x["status"], "size": x.get("size", 0), "created_at": x["created_at"]
    } for x in out["items"]]
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
    doc_ids = data.get("doc_ids", [])
    matter = data.get("matter", {})

    # Allow sessions without documents

    session = {
        "user_id": user_id,
        "title": data.get("title") or ("Chat Session" if doc_ids else "General Chat"),
        "doc_ids": [ObjectId(d) for d in doc_ids],
        "has_docs": bool(doc_ids),  # Flag to track if this is a document-based chat
        "matter": matter or {},
        "model": os.getenv("RAG_MODEL", "gpt-4o"),
        "created_at": datetime.utcnow(),
        "last_message_at": datetime.utcnow(),
        "deleted": False
    }
    res = _db()['rag_chat_sessions'].insert_one(session)
    return JsonResponse({"session_id": str(res.inserted_id)})

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
    items = [{"id": str(x["_id"]), "title": x["title"], "created_at": x["created_at"], "last_message_at": x["last_message_at"]} for x in out["items"]]
    return JsonResponse({"total": total, "items": items})

@api_view(['GET'])
@supabase_required
def get_messages(request, session_id: str):
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
    _db()['rag_chat_sessions'].update_one({"_id": ObjectId(session_id)}, {"$set": {"deleted": True}})
    return JsonResponse({"message": "deleted"})

@api_view(['POST'])
@supabase_required
def modify_session_docs(request, session_id: str):
    data = json.loads(request.body or b"{}")
    add = [ObjectId(x) for x in data.get("add", [])]
    remove = set(data.get("remove", []))
    sess = _db()['rag_chat_sessions'].find_one({"_id": ObjectId(session_id)})
    if not sess: return JsonResponse({"error": "not found"}, status=404)
    doc_ids = [d for d in sess["doc_ids"] if str(d) not in remove] + add
    _db()['rag_chat_sessions'].update_one({"_id": sess["_id"]}, {"$set": {"doc_ids": doc_ids}})
    return JsonResponse({"message":"updated"})

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
