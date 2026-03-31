"""
agents/post_hearing.py — PostHearingAgent

Trigger: Lawyer marks a hearing event complete and records the outcome.

Steps:
  1. Accept case_id, hearing_notes_id, outcome_text, next_date (optional)
  2. Update hearing_notes record with outcome and next_date
  3. Update cases.next_hearing and cases.stage if appropriate
  4. Call brain:t1 to extract: status (adjourned/decided/partial order)
     and implied tasks from outcome_text
  5. Auto-create case_tasks for each implied task (source='agent')
  6. Return updated case summary + task list + next_suggested_action

API: POST /api/agents/post-hearing/
"""
import uuid
import logging
from datetime import datetime, timezone

from core.llm_client import chat_complete
from .base_agent import BaseAgent, get_case, safe_json_loads

logger = logging.getLogger('django')

_OUTCOME_SYSTEM = """You are a legal case assistant.
Given a hearing outcome text recorded by an Indian lawyer, extract:
1. Hearing status: one of "adjourned", "order_passed", "evidence_recorded", "arguments_heard", "disposed", "settled", "other"
2. A list of follow-up tasks implied by the outcome (file a document, pay court fees, serve notice, etc.)

Return ONLY a JSON object:
{
  "status": "adjourned | order_passed | evidence_recorded | arguments_heard | disposed | settled | other",
  "implied_tasks": [
    {"title": "task title", "priority": "High | Medium | Low"}
  ]
}
Be conservative — only extract tasks that are clearly required or mentioned.
Return ONLY the JSON object."""


def _now():
    return datetime.now(timezone.utc).isoformat()


class PostHearingAgent(BaseAgent):
    name = 'PostHearingAgent'

    def _run(self, inputs: dict, db, supa_user: dict) -> dict:
        lawyer_id = supa_user.get('user_id', '')
        case_id = (inputs.get('case_id') or '').strip()
        note_id = (inputs.get('hearing_notes_id') or '').strip()
        outcome_text = (inputs.get('outcome_text') or '').strip()
        next_date = (inputs.get('next_date') or '').strip()

        if not case_id:
            raise ValueError("'case_id' is required.")
        if not note_id:
            raise ValueError("'hearing_notes_id' is required.")
        if not outcome_text:
            raise ValueError("'outcome_text' is required.")

        case = get_case(db, case_id, lawyer_id)

        # ── Verify hearing note belongs to this case ───────────────────────
        note = db['hearing_notes'].find_one({'_id': note_id, 'case_id': case_id})
        if not note:
            raise ValueError(f"Hearing note {note_id} not found for case {case_id}.")

        now = _now()

        # ── Step 1: Update hearing_notes record ───────────────────────────
        note_updates = {
            'outcome': outcome_text,
            'type': 'outcome',  # promote to outcome if it was prep
        }
        if next_date:
            note_updates['next_date'] = next_date
        db['hearing_notes'].update_one(
            {'_id': note_id},
            {'$set': note_updates}
        )

        # ── Step 2: Update case record ────────────────────────────────────
        case_updates = {'updated_at': now}
        if next_date:
            case_updates['next_hearing'] = next_date

        db['cases'].update_one({'_id': case_id}, {'$set': case_updates})

        # ── Step 3: LLM extraction of outcome + tasks ─────────────────────
        extracted = {}
        try:
            llm_resp = chat_complete(
                messages=[
                    {"role": "system", "content": _OUTCOME_SYSTEM},
                    {"role": "user", "content": outcome_text},
                ],
                app_scenario="brain:t1",
                temperature=0.1,
                max_tokens=400,
            )
            extracted = safe_json_loads(llm_resp)
            logger.info('[AGENT:PostHearingAgent] extracted status=%s tasks=%d',
                        extracted.get('status'), len(extracted.get('implied_tasks', [])))
        except Exception as exc:
            logger.warning('[AGENT:PostHearingAgent] LLM extraction failed: %s', exc)

        # ── Step 4: Auto-create case_tasks ────────────────────────────────
        created_tasks = []
        implied_tasks = extracted.get('implied_tasks') or []
        for task_spec in implied_tasks:
            title = (task_spec.get('title') or '').strip()
            if not title:
                continue
            priority = task_spec.get('priority') or 'Medium'
            if priority not in ('High', 'Medium', 'Low'):
                priority = 'Medium'

            task_id = str(uuid.uuid4())
            task_doc = {
                '_id': task_id,
                'case_id': case_id,
                'title': title,
                'description': f"Auto-generated from hearing outcome: {outcome_text[:100]}",
                'due_date': next_date or '',  # suggest next hearing date as soft deadline
                'assigned_to': lawyer_id,
                'created_by': lawyer_id,
                'status': 'Pending',
                'priority': priority,
                'source': 'agent',
                'created_at': now,
            }
            db['case_tasks'].insert_one(task_doc)
            created_tasks.append({'id': task_id, 'title': title, 'priority': priority})

        # Link generated task IDs back to hearing note
        if created_tasks:
            db['hearing_notes'].update_one(
                {'_id': note_id},
                {'$set': {'tasks_generated': [t['id'] for t in created_tasks]}}
            )

        next_action = (
            'schedule_next_hearing' if next_date
            else 'update_case_stage' if extracted.get('status') in ('disposed', 'settled')
            else 'review_tasks'
        )

        return {
            'hearing_status': extracted.get('status', 'other'),
            'tasks_created': created_tasks,
            'next_date': next_date,
            'case_id': case_id,
            'next_suggested_action': next_action,
        }
