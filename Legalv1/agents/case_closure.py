"""
agents/case_closure.py — CaseClosureAgent

Trigger: Lawyer marks a case as Settled, Disposed, or Archived.

Steps:
  1. Accept case_id, resolution_type, resolution_summary
  2. Fetch all: hearing notes, tasks (completed/pending), case notes
  3. Call brain:t3 → generate structured case summary
  4. Update cases.status = Archived; cases.stage = Closed
  5. Cancel all pending tasks (or list them for review)
  6. Create a final case_notes entry (visibility='shared') for the client
  7. Return: full case summary document + next_suggested_action

API: POST /api/agents/case-closure/
"""
import uuid
import json
import logging
from datetime import datetime, timezone

from core.llm_client import chat_complete
from .base_agent import BaseAgent, get_case, safe_json_loads

logger = logging.getLogger('django')

_CLOSURE_SYSTEM = """You are a legal case summary specialist.
Given a case's complete history (hearings, notes, resolution), generate a formal case summary.

Return ONLY a JSON object:
{
  "timeline": [
    {"date": "...", "event": "...", "significance": "..."}
  ],
  "final_outcome": "Clear statement of how the case was resolved",
  "applicable_law_used": ["key statutes / sections"],
  "parties": {"petitioner": "...", "respondent": "..."},
  "key_milestones": ["significant events in order"],
  "client_summary": "Plain-language summary for the client (max 300 chars)"
}
Be factual. Use only the information provided. Return ONLY the JSON object."""

VALID_RESOLUTIONS = {'Settled', 'Disposed', 'Appeal', 'Archived', 'Closed'}


def _now():
    return datetime.now(timezone.utc).isoformat()


class CaseClosureAgent(BaseAgent):
    name = 'CaseClosureAgent'

    def _run(self, inputs: dict, db, supa_user: dict) -> dict:
        lawyer_id = supa_user.get('user_id', '')
        case_id = (inputs.get('case_id') or '').strip()
        resolution_type = (inputs.get('resolution_type') or 'Archived').strip()
        resolution_summary = (inputs.get('resolution_summary') or '').strip()

        if not case_id:
            raise ValueError("'case_id' is required.")
        if not resolution_summary:
            raise ValueError("'resolution_summary' is required.")
        if resolution_type not in VALID_RESOLUTIONS:
            resolution_type = 'Archived'

        case = get_case(db, case_id, lawyer_id)
        now = _now()

        # ── Step 1: Collect case history ──────────────────────────────────
        hearing_notes = list(
            db['hearing_notes'].find(
                {'case_id': case_id},
                {'_id': 0, 'hearing_date': 1, 'purpose': 1, 'outcome': 1, 'type': 1}
            ).sort('hearing_date', 1)
        )
        tasks = list(
            db['case_tasks'].find(
                {'case_id': case_id},
                {'_id': 1, 'title': 1, 'status': 1, 'due_date': 1}
            )
        )
        notes_count = db['case_notes'].count_documents({'case_id': case_id})

        # ── Step 2: LLM case summary ──────────────────────────────────────
        context = (
            f"Case: {case.get('title', '')}\n"
            f"Type: {case.get('case_type', '')}\n"
            f"Brief: {case.get('brief', '')}\n"
            f"Resolution type: {resolution_type}\n"
            f"Resolution summary: {resolution_summary}\n\n"
            f"Hearing history ({len(hearing_notes)} hearings):\n"
            + json.dumps(hearing_notes, ensure_ascii=False)[:2000]
        )

        case_summary = {}
        try:
            llm_resp = chat_complete(
                messages=[
                    {"role": "system", "content": _CLOSURE_SYSTEM},
                    {"role": "user", "content": context},
                ],
                app_scenario="brain:t3",
                temperature=0.2,
                max_tokens=1500,
            )
            case_summary = safe_json_loads(llm_resp)
            if not case_summary:
                case_summary = {'client_summary': resolution_summary}
            logger.info('[AGENT:CaseClosureAgent] summary generated for case=%s', case_id)
        except Exception as exc:
            logger.warning('[AGENT:CaseClosureAgent] LLM summary failed: %s', exc)
            case_summary = {'client_summary': resolution_summary}

        # ── Step 3: Update case status ────────────────────────────────────
        db['cases'].update_one(
            {'_id': case_id},
            {'$set': {
                'status': resolution_type,
                'stage': 'Closed',
                'resolution_summary': resolution_summary,
                'closed_at': now,
                'updated_at': now,
            }}
        )

        # ── Step 4: Cancel all pending tasks ──────────────────────────────
        pending_task_ids = [
            str(t['_id']) for t in tasks
            if t.get('status') in ('Pending', 'InProgress')
        ]
        cancelled_count = 0
        if pending_task_ids:
            result = db['case_tasks'].update_many(
                {'_id': {'$in': pending_task_ids}},
                {'$set': {'status': 'Cancelled', 'updated_at': now}}
            )
            cancelled_count = result.modified_count

        # ── Step 5: Create shared case note for client ────────────────────
        client_summary = case_summary.get('client_summary') or resolution_summary
        shared_note_id = str(uuid.uuid4())
        db['case_notes'].insert_one({
            '_id': shared_note_id,
            'case_id': case_id,
            'author_id': lawyer_id,
            'author_role': 'Lawyer',
            'visibility': 'shared',
            'content': (
                f"**Case Closed — {resolution_type}**\n\n"
                f"{client_summary}\n\n"
                f"*Resolution: {resolution_summary}*"
            ),
            'attachments': [],
            'created_at': now,
            'updated_at': now,
        })

        return {
            'case_id': case_id,
            'resolution_type': resolution_type,
            'case_summary': case_summary,
            'pending_tasks_cancelled': cancelled_count,
            'client_note_id': shared_note_id,
            'stats': {
                'hearings': len(hearing_notes),
                'tasks_total': len(tasks),
                'tasks_cancelled': cancelled_count,
                'notes': notes_count,
            },
            'next_suggested_action': 'send_closure_email',
        }
