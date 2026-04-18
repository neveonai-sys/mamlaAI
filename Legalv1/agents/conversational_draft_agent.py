"""
agents/conversational_draft_agent.py — ConversationalDraftAgent

Guides a lawyer through a conversational intake flow to collect all the
details needed for a high-quality legal draft.  Once ready, triggers the
existing draft-generation pipeline.

MongoDB collection: draft_conversations

Flow (from the view layer):
  1. POST guide/start/      → start()
  2. POST guide/message/    → message()
  3. POST guide/upload_doc/ → handle_doc_upload()
  4. POST guide/generate/   → generate()
"""
import logging
import uuid
from datetime import datetime, timezone

from core.init_clients import get_mongo_client, get_mongo_db
from core.llm_client import chat_complete
from mamla_brain.prompts import DRAFT_INTAKE_SYSTEM
from mamla_brain.retrieval import search_user_docs

from .base_agent import safe_json_loads

logger = logging.getLogger('django')

MAX_TURNS = 10
SOFT_CAP_TURN = 8          # inject "wrap up" instruction at this turn


def _now():
    return datetime.now(timezone.utc).isoformat()


def _get_db():
    mongo = get_mongo_client()
    return get_mongo_db()


# ─── System prompt builder ────────────────────────────────────────────────────

def _build_system_message(case_context=None, doc_context=None, turn_index=0):
    """Build the system message list for the LLM, injecting any pre-loaded context."""
    parts = [DRAFT_INTAKE_SYSTEM]

    if case_context:
        parts.append(
            "\n\n[CASE CONTEXT PRE-LOADED]\n"
            "The following facts are already known from the case file. "
            "Acknowledge them at the start and skip asking about things you already know.\n\n"
            + case_context
        )

    if doc_context:
        parts.append(
            "\n\n[DOCUMENT CONTEXT PRE-LOADED]\n"
            "The following facts were extracted from the user's uploaded documents. "
            "Use them; do not re-ask for information already present here.\n\n"
            + "\n---\n".join(doc_context)
        )

    if turn_index >= SOFT_CAP_TURN:
        parts.append(
            "\n\n[INSTRUCTION — WRAP UP NOW]\n"
            "You are approaching the maximum conversation length. "
            "On your next reply you MUST signal ready=true and provide the full draft_plan JSON, "
            "even if some optional details are still missing."
        )

    return "".join(parts)


# ─── Doc context helper ───────────────────────────────────────────────────────

def _extract_doc_context(user_id, document_ids):
    """Run several seeding queries to pull the most relevant snippets from uploaded docs."""
    if not document_ids:
        return []
    seed_queries = [
        "parties names petitioner respondent plaintiff defendant",
        "dates filing court order relief sought",
        "applicable law act section offence claim",
        "facts background incident dispute",
    ]
    seen = set()
    snippets = []
    for q in seed_queries:
        try:
            hits = search_user_docs(q, user_id, doc_ids=document_ids, k=5)
            for h in hits:
                chunk_id = h.get('source_id', '') + str(h.get('page', ''))
                if chunk_id not in seen:
                    seen.add(chunk_id)
                    snippets.append(h['text'][:500])
        except Exception as exc:
            logger.warning('[ConversationalDraftAgent] doc search failed: %s', exc)
    return snippets[:16]  # cap to avoid token overflow


# ─── Public API ───────────────────────────────────────────────────────────────

def start(user_id: str, case_id: str = None, document_ids: list = None) -> dict:
    """
    Create a new draft conversation.
    Returns {ok, conv_id, message}.
    """
    db = _get_db()
    doc_context = []
    case_context_str = None

    # ── Pre-load case context ────────────────────────────────────────────────
    if case_id:
        try:
            from .draft_context import DraftContextAgent
            result = DraftContextAgent().run(
                {'case_id': case_id, 'draft_type': 'petition'},
                db,
                {'user_id': user_id},
            )
            if result.get('ok'):
                dc = result['draft_context']
                facts = dc.get('key_facts') or []
                case_context_str = (
                    f"Case title: {dc.get('draft_for', {}).get('case_title', '')}\n"
                    f"Case type: {dc.get('case_type', '')}\n"
                    f"Location: {dc.get('location', {})}\n"
                    f"Summary: {dc.get('context_summary', '')}\n"
                    f"Suggested sections: {dc.get('suggested_sections', [])}\n"
                    f"Key facts: {facts}"
                )
        except Exception as exc:
            logger.warning('[ConversationalDraftAgent] case context failed: %s', exc)

    # ── Pre-load document context ────────────────────────────────────────────
    if document_ids:
        doc_context = _extract_doc_context(user_id, document_ids)

    # ── Build opening system + first AI turn ─────────────────────────────────
    system_content = _build_system_message(case_context=case_context_str, doc_context=doc_context)
    seed_messages = [{"role": "system", "content": system_content}]

    if case_context_str:
        seed_messages.append({
            "role": "user",
            "content": "I want to draft a legal document based on the case context you have."
        })
    elif doc_context:
        seed_messages.append({
            "role": "user",
            "content": "I want to draft a legal document based on the document I uploaded."
        })
    else:
        seed_messages.append({
            "role": "user",
            "content": "I need to draft a legal document."
        })

    try:
        ai_reply = chat_complete(seed_messages, app_scenario='brain:t2', temperature=0.2, max_tokens=1024)
    except Exception as exc:
        logger.error('[ConversationalDraftAgent] LLM call failed in start(): %s', exc)
        return {"ok": False, "error": "Could not start the guided drafting session. Please try again."}

    # ── Persist conversation ─────────────────────────────────────────────────
    conv_id = str(uuid.uuid4())
    now = _now()
    messages_log = [
        {"role": "system", "content": system_content, "ts": now},
        {"role": "user", "content": seed_messages[-1]["content"], "ts": now},
        {"role": "assistant", "content": ai_reply, "ts": now},
    ]
    db['draft_conversations'].insert_one({
        "conv_id": conv_id,
        "user_id": user_id,
        "state": "gathering",
        "messages": messages_log,
        "doc_context": doc_context,
        "case_context": case_context_str,   # persisted so it can be re-injected on every turn
        "draft_plan": None,
        "case_id": case_id,
        "turn_count": 1,
        "created_at": now,
        "updated_at": now,
    })

    return {"ok": True, "conv_id": conv_id, "message": ai_reply}


def message(conv_id: str, user_id: str, user_text: str) -> dict:
    """
    Append a user turn, call the LLM, check for ready signal.
    Returns {ok, reply, ready, draft_plan}.
    """
    if not user_text or not user_text.strip():
        return {"ok": False, "error": "Message cannot be empty."}

    db = _get_db()
    conv = db['draft_conversations'].find_one({"conv_id": conv_id, "user_id": user_id})
    if not conv:
        return {"ok": False, "error": "Conversation not found."}
    if conv.get("state") == "generating":
        return {"ok": False, "error": "Draft generation is already in progress."}

    turn_count = conv.get("turn_count", 0)
    if turn_count >= MAX_TURNS:
        return {"ok": False, "error": "Maximum conversation length reached. Please generate your draft now."}

    # ── Build message list for LLM ───────────────────────────────────────────
    # Rebuild system prompt with current turn index (may inject wrap-up instruction)
    # Re-inject case_context so the LLM never loses it between turns
    system_content = _build_system_message(
        case_context=conv.get("case_context"),
        doc_context=conv.get("doc_context") or [],
        turn_index=turn_count,
    )
    llm_messages = [{"role": "system", "content": system_content}]

    # Include conversation history (skip original system message stored in DB)
    for m in conv.get("messages", []):
        if m["role"] != "system":
            llm_messages.append({"role": m["role"], "content": m["content"]})

    llm_messages.append({"role": "user", "content": user_text})

    try:
        ai_reply = chat_complete(llm_messages, app_scenario='brain:t2', temperature=0.2, max_tokens=1024)
    except Exception as exc:
        logger.error('[ConversationalDraftAgent] LLM call failed in message(): %s', exc)
        return {"ok": False, "error": "AI is temporarily unavailable. Please try again."}

    # ── Check for readiness signal ───────────────────────────────────────────
    parsed = safe_json_loads(ai_reply)
    ready = bool(parsed.get("ready"))
    draft_plan = parsed.get("draft_plan") if ready else None

    # ── Persist ─────────────────────────────────────────────────────────────
    now = _now()
    new_messages = [
        {"role": "user", "content": user_text, "ts": now},
        {"role": "assistant", "content": ai_reply, "ts": now},
    ]
    update_fields = {
        "updated_at": now,
        "turn_count": turn_count + 1,
    }
    if ready:
        update_fields["state"] = "ready"
        update_fields["draft_plan"] = draft_plan

    db['draft_conversations'].update_one(
        {"conv_id": conv_id},
        {
            "$push": {"messages": {"$each": new_messages}},
            "$set": update_fields,
        },
    )

    return {"ok": True, "reply": ai_reply, "ready": ready, "draft_plan": draft_plan}


def handle_doc_upload(conv_id: str, user_id: str, document_ids: list) -> dict:
    """
    Process newly uploaded documents mid-conversation.
    Injects extracted facts into the conversation and gets AI to react.
    Returns {ok, reply}.
    """
    if not document_ids:
        return {"ok": False, "error": "No document IDs provided."}

    db = _get_db()
    conv = db['draft_conversations'].find_one({"conv_id": conv_id, "user_id": user_id})
    if not conv:
        return {"ok": False, "error": "Conversation not found."}

    # ── Extract facts from new docs ──────────────────────────────────────────
    new_snippets = _extract_doc_context(user_id, document_ids)

    existing_doc_context = conv.get("doc_context") or []

    if not new_snippets:
        # Document was uploaded but Celery indexing hasn't completed yet.
        # Proceed gracefully — tell the AI the doc is coming, don't error out.
        injected_content = (
            "[NEW DOCUMENT UPLOADED]\n"
            "The user just uploaded a new document. It is still being processed and indexed. "
            "Acknowledge this, let the user know the document will be reflected shortly, "
            "and continue by asking the next clarifying question."
        )
        merged_doc_context = existing_doc_context
    else:
        injected_content = (
            "[NEW DOCUMENTS UPLOADED]\n"
            "The user just uploaded new documents. The following facts were extracted:\n\n"
            + "\n---\n".join(new_snippets)
            + "\n\nAcknowledge the key facts you found and ask the next clarifying question."
        )
        merged_doc_context = existing_doc_context + new_snippets

    system_content = _build_system_message(
        case_context=conv.get("case_context"),
        doc_context=merged_doc_context,
    )
    llm_messages = [{"role": "system", "content": system_content}]
    for m in conv.get("messages", []):
        if m["role"] != "system":
            llm_messages.append({"role": m["role"], "content": m["content"]})
    llm_messages.append({"role": "user", "content": injected_content})

    try:
        ai_reply = chat_complete(llm_messages, app_scenario='brain:t2', temperature=0.2, max_tokens=1024)
    except Exception as exc:
        logger.error('[ConversationalDraftAgent] LLM call in handle_doc_upload() failed: %s', exc)
        return {"ok": False, "error": "AI is temporarily unavailable. Please try again."}

    # ── Persist ─────────────────────────────────────────────────────────────
    now = _now()
    new_messages = [
        {"role": "user", "content": injected_content, "ts": now},
        {"role": "assistant", "content": ai_reply, "ts": now},
    ]
    db['draft_conversations'].update_one(
        {"conv_id": conv_id},
        {
            "$set": {"doc_context": merged_doc_context, "updated_at": now},
            "$push": {"messages": {"$each": new_messages}},
            "$inc": {"turn_count": 1},
        },
    )

    return {"ok": True, "reply": ai_reply}


def generate(conv_id: str, user_id: str) -> dict:
    """
    Trigger draft generation using the collected draft_plan.
    Returns {ok, session_id}.
    """
    db = _get_db()
    conv = db['draft_conversations'].find_one({"conv_id": conv_id, "user_id": user_id})
    if not conv:
        return {"ok": False, "error": "Conversation not found."}
    if conv.get("state") not in ("ready", "gathering"):
        return {"ok": False, "error": "Conversation is not ready for generation."}

    draft_plan = conv.get("draft_plan") or {}
    key_facts = draft_plan.get("key_facts") or {}
    sections_plan = draft_plan.get("sections_plan") or []

    # ── Build enriched query from draft_plan + full conversation ─────────────
    draft_type = draft_plan.get("draft_type") or "legal document"
    facts_text = "\n".join(f"- {k}: {v}" for k, v in key_facts.items() if v)
    sections_text = ", ".join(sections_plan) if sections_plan else ""

    # Include the full intake conversation so the drafting pipeline has rich context
    conv_lines = []
    for m in conv.get("messages", []):
        if m["role"] in ("user", "assistant"):
            content = (m.get("content") or "").strip()
            # Skip injected system-style markers — they are noise for the drafter
            if content and not content.startswith("[NEW DOCUMENT"):
                role_label = "Lawyer" if m["role"] == "user" else "AI"
                conv_lines.append(f"{role_label}: {content[:400]}")
    # Keep last 20 turns to avoid token overflow
    conv_summary = "\n".join(conv_lines[-20:]) if conv_lines else ""

    user_query = (
        f"Draft type: {draft_type}\n"
        + (f"Key facts:\n{facts_text}\n" if facts_text else "")
        + (f"Required sections: {sections_text}\n" if sections_text else "")
        + (f"\nIntake conversation (use this for full context):\n{conv_summary}\n" if conv_summary else "")
        + "\nPlease generate a complete, professionally drafted Indian legal document."
    )

    # ── Determine draft_for from case_id if available ─────────────────────────
    draft_for = {}
    case_id = conv.get("case_id")
    if case_id:
        case_doc = db['cases'].find_one({"_id": case_id})
        if case_doc:
            draft_for = {
                "case_id": case_id,
                "case_title": case_doc.get("title", ""),
                "client_ids": case_doc.get("client_ids") or [],
            }

    # ── Set state to generating ───────────────────────────────────────────────
    db['draft_conversations'].update_one(
        {"conv_id": conv_id},
        {"$set": {"state": "generating", "updated_at": _now()}},
    )

    # ── Delegate to existing draft generation pipeline ────────────────────────
    try:
        from ai_draft.routes.creatupdateAIdrafts import CreateupdatefetchAIdrafts
        import datetime

        obj = CreateupdatefetchAIdrafts(user_id)
        session_id = obj.start_new_session(user_query, draft_for)

        # Auto-save
        draft_sections = obj.retrieve_sections_of_draft(session_id).get('mssg', [])
        draft_name = f"Guided Draft — {draft_type.title()} {datetime.datetime.now().strftime('%d %b %Y')}"
        obj.auto_save_initial_draft(session_id, draft_name, draft_sections)

        # Link session_id back to conversation for traceability
        db['draft_conversations'].update_one(
            {"conv_id": conv_id},
            {"$set": {"session_id": str(session_id), "updated_at": _now()}},
        )

        return {"ok": True, "session_id": str(session_id)}
    except Exception as exc:
        logger.error('[ConversationalDraftAgent] draft generation failed: %s', exc)
        db['draft_conversations'].update_one(
            {"conv_id": conv_id},
            {"$set": {"state": "ready", "updated_at": _now()}},
        )
        return {"ok": False, "error": "Draft generation failed. Please try again."}
