"""
agents/hearing_prep.py — HearingPrepAgent

Trigger: Lawyer opens a hearing event in the calendar or manually invokes from case page.

Steps:
  1. Accept case_id, hearing_date, purpose, document_ids (optional)
  2. Pull eCourts history via CNR if linked to case
  3. Pull last 3 hearing_notes outcomes for the case
  4. Run TalkDoc KNN on case documents for purpose-relevant chunks (top-8)
  5. Call brain:t3 with assembled context → structured hearing brief
  6. Store result in hearing_notes as type='prep'
  7. Return structured brief + note_id + next_suggested_action

API: POST /api/agents/hearing-prep/
"""
import uuid
import json
import logging
from datetime import datetime, timezone

from core.llm_client import chat_complete
from .base_agent import BaseAgent, get_case, safe_json_loads

logger = logging.getLogger('django')

_BRIEF_SYSTEM = """You are the Mamla Case Companion, an expert assistant for Indian lawyers.

Given the case context, eCourts history, past hearing outcomes, and relevant document excerpts,
generate a comprehensive hearing preparation brief.

Return ONLY a JSON object with exactly these keys:
{
  "applicable_law": ["list of relevant acts/sections with brief description"],
  "arguments_for": ["key arguments the lawyer should raise"],
  "watch_points": ["anticipated counter-arguments or risks to watch for"],
  "suggested_questions": ["questions to ask opposing counsel, witness, or court"],
  "checklist": ["documents to bring, procedural steps, things to confirm"],
  "summary": "2-3 sentence hearing strategy summary"
}

Be specific and grounded in the provided context. Do not invent case-specific facts.
Return ONLY the JSON object — no preamble, no explanation."""


def _now():
    return datetime.now(timezone.utc).isoformat()


class HearingPrepAgent(BaseAgent):
    name = 'HearingPrepAgent'

    def _run(self, inputs: dict, db, supa_user: dict) -> dict:
        lawyer_id = supa_user.get('user_id', '')
        case_id = (inputs.get('case_id') or '').strip()
        hearing_date = (inputs.get('hearing_date') or '').strip()
        purpose = (inputs.get('purpose') or 'general hearing preparation').strip()
        document_ids = inputs.get('document_ids') or []

        if not case_id:
            raise ValueError("'case_id' is required.")
        if not hearing_date:
            raise ValueError("'hearing_date' is required.")

        case = get_case(db, case_id, lawyer_id)
        context_parts = []

        # ── Step 1: Case context ──────────────────────────────────────────
        context_parts.append(
            f"Case: {case.get('title', '')}\n"
            f"Type: {case.get('case_type', '')}\n"
            f"Stage: {case.get('stage', '')}\n"
            f"Court: {json.dumps(case.get('court', {}))}\n"
            f"Brief: {case.get('brief', '')}\n"
            f"Hearing Purpose: {purpose}"
        )

        # ── Step 2: eCourts history (if CNR linked) ───────────────────────
        cnr = (case.get('cnr') or '').strip()
        if cnr:
            try:
                from ecourt_scrapped.services import scraper_client
                result = scraper_client.post("cnr/search", {"cnr_number": cnr}, timeout=20)
                if isinstance(result, dict):
                    history = result.get('hearing_history') or result.get('hearingHistory') or []
                    if history:
                        recent = history[-5:] if len(history) > 5 else history
                        context_parts.append(
                            "eCourts Hearing History (last 5):\n" +
                            json.dumps(recent, ensure_ascii=False)[:800]
                        )
                    orders = result.get('orders') or result.get('case_orders') or []
                    if orders:
                        context_parts.append(
                            "Recent Orders:\n" +
                            json.dumps(orders[-3:], ensure_ascii=False)[:600]
                        )
            except Exception as exc:
                logger.warning('[AGENT:HearingPrepAgent] eCourts lookup failed cnr=%s: %s', cnr, exc)

        # ── Step 3: Past hearing outcomes ─────────────────────────────────
        past_outcomes = list(
            db['hearing_notes'].find(
                {'case_id': case_id, 'type': 'outcome'},
                {'_id': 0, 'hearing_date': 1, 'outcome': 1, 'purpose': 1}
            ).sort('hearing_date', -1).limit(3)
        )
        if past_outcomes:
            context_parts.append(
                "Past Hearing Outcomes:\n" +
                "\n".join(
                    f"[{o.get('hearing_date','')}] {o.get('purpose','')}: {o.get('outcome','')}"
                    for o in past_outcomes
                )
            )

        # ── Step 4: Document KNN search ───────────────────────────────────
        if document_ids:
            try:
                from talkdoc.tasks import embed_texts
                from talkdoc.search import os_client, knn_search

                cli = os_client()
                [query_vec] = embed_texts([f"{purpose} {case.get('case_type','')}"])
                hits = knn_search(cli, query_vec, lawyer_id, doc_ids=document_ids, k=8)
                if hits:
                    context_parts.append(
                        "Relevant Document Excerpts:\n" +
                        "\n---\n".join(h['text'] for h in hits[:8])[:3000]
                    )
            except Exception as exc:
                logger.warning('[AGENT:HearingPrepAgent] document search failed: %s', exc)

        # ── Step 5: LLM call → structured brief ───────────────────────────
        full_context = "\n\n===\n\n".join(context_parts)

        ai_brief = {}
        try:
            llm_resp = chat_complete(
                messages=[
                    {"role": "system", "content": _BRIEF_SYSTEM},
                    {"role": "user", "content": full_context},
                ],
                app_scenario="brain:t3",
                temperature=0.2,
                max_tokens=2000,
            )
            ai_brief = safe_json_loads(llm_resp)
            if not ai_brief:
                # Store raw text as summary if JSON parse failed
                ai_brief = {"summary": llm_resp[:500]}
            logger.info('[AGENT:HearingPrepAgent] brief generated for case=%s', case_id)
        except Exception as exc:
            logger.error('[AGENT:HearingPrepAgent] LLM brief generation failed: %s', exc)
            ai_brief = {"error": str(exc)}

        # ── Step 6: Store as hearing_notes (type=prep) ────────────────────
        note_id = str(uuid.uuid4())
        note_doc = {
            '_id': note_id,
            'case_id': case_id,
            'lawyer_id': lawyer_id,
            'hearing_date': hearing_date,
            'calendar_event_id': (inputs.get('calendar_event_id') or '').strip(),
            'type': 'prep',
            'content': f"AI-generated hearing brief for: {purpose}",
            'ai_brief': ai_brief,
            'purpose': purpose,
            'outcome': '',
            'next_date': '',
            'tasks_generated': [],
            'created_at': _now(),
        }
        db['hearing_notes'].insert_one(note_doc)

        return {
            'note_id': note_id,
            'ai_brief': ai_brief,
            'case_id': case_id,
            'hearing_date': hearing_date,
            'context_used': {
                'ecourts': bool(cnr),
                'past_outcomes': len(past_outcomes),
                'document_chunks': len(document_ids),
            },
            'next_suggested_action': 'record_outcome',
        }
