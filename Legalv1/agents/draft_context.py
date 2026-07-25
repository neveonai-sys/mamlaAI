"""
agents/draft_context.py — DraftContextAgent

Trigger: Lawyer initiates a draft from within a case (rather than standalone drafting).

Steps:
  1. Accept case_id, draft_type
  2. Pull cases record → extract court, parties, case_type, stage
  3. Pull last hearing_notes outcome (if any)
  4. Run TalkDoc KNN search on case documents for key facts (if document_ids provided)
  5. Build enriched draft_context JSON:
     - draft_for: case + client IDs
     - location: court details
     - context_summary: auto-generated paragraph
     - suggested_sections: appropriate for draft_type + case_type
  6. Return context → frontend passes this into DraftingWorkspace pre-fill

API: POST /api/agents/draft-context/
"""
import logging
from datetime import datetime, timezone

from core.llm_client import chat_complete
from .base_agent import BaseAgent, get_case, safe_json_loads
from users.routes.encryption import decrypt_field

logger = logging.getLogger('django')

_CONTEXT_SYSTEM = """You are a legal drafting assistant for Indian lawyers.
Given the case details, hearing history, and document excerpts, produce a structured
context pack to pre-fill a legal draft.

Return ONLY a JSON object:
{
  "context_summary": "One paragraph summarising the case facts and current stage for the drafter",
  "suggested_sections": ["section names appropriate for this draft_type and case_type"],
  "key_facts": ["bullet-point list of most important facts to include in the draft"]
}
Keep context_summary under 400 chars. Return ONLY the JSON."""

# Sensible default sections by draft type
_DEFAULT_SECTIONS: dict = {
    'petition': ['Cause Title', 'Facts of the Case', 'Grounds', 'Prayer', 'Verification'],
    'written_statement': ['Cause Title', 'Preliminary Objections', 'Reply on Merits', 'Counter-claim (if any)', 'Prayer'],
    'application': ['Cause Title', 'Application', 'Grounds', 'Prayer', 'Verification'],
    'reply': ['Cause Title', 'Reply to Grounds', 'Additional Grounds', 'Prayer'],
    'affidavit': ['Title', 'Deponent Details', 'Sworn Statement', 'Verification'],
    'notice': ['Addressee', 'Subject', 'Facts', 'Legal Demand', 'Consequences of Non-Compliance'],
}


def _now():
    return datetime.now(timezone.utc).isoformat()


class DraftContextAgent(BaseAgent):
    name = 'DraftContextAgent'

    def _run(self, inputs: dict, db, supa_user: dict) -> dict:
        lawyer_id = supa_user.get('user_id', '')
        case_id = (inputs.get('case_id') or '').strip()
        draft_type = (inputs.get('draft_type') or 'petition').strip().lower()
        document_ids = inputs.get('document_ids') or []

        if not case_id:
            raise ValueError("'case_id' is required.")

        case = get_case(db, case_id, lawyer_id)
        # case['brief'] is ciphertext (raw Mongo read via base_agent.get_case,
        # not case_crud._serialize) — decrypt once up front, everything below
        # (LLM context + the returned draft_context) uses this variable.
        case_brief = decrypt_field(case.get('brief', ''))
        context_parts = []

        # ── Step 1: Case context ──────────────────────────────────────────
        import json
        context_parts.append(
            f"Case title: {case.get('title', '')}\n"
            f"Case type: {case.get('case_type', '')}\n"
            f"Stage: {case.get('stage', '')}\n"
            f"Court: {json.dumps(case.get('court', {}))}\n"
            f"Brief: {case_brief}\n"
            f"Draft type requested: {draft_type}"
        )

        # ── Step 2: Last hearing outcome ──────────────────────────────────
        last_outcome = db['hearing_notes'].find_one(
            {'case_id': case_id, 'type': 'outcome'},
            {'_id': 0, 'hearing_date': 1, 'outcome': 1, 'next_date': 1}
        )
        if last_outcome:
            context_parts.append(
                f"Last Hearing [{last_outcome.get('hearing_date','')}]: "
                f"{decrypt_field(last_outcome.get('outcome',''))}"
            )

        # ── Step 3: Document search (if doc IDs provided) ─────────────────
        if document_ids:
            try:
                from talkdoc.tasks import embed_texts
                from talkdoc.search import os_client, knn_search

                cli = os_client()
                query = f"{draft_type} {case.get('case_type','')} facts parties relief"
                [vec] = embed_texts([query])
                hits = knn_search(cli, vec, lawyer_id, doc_ids=document_ids, k=8)
                if hits:
                    context_parts.append(
                        "Relevant document snippets:\n" +
                        "\n---\n".join(h['text'] for h in hits[:8])[:2500]
                    )
            except Exception as exc:
                logger.warning('[AGENT:DraftContextAgent] document search failed: %s', exc)

        # ── Step 4: LLM enriched context ──────────────────────────────────
        enriched = {}
        try:
            llm_resp = chat_complete(
                messages=[
                    {"role": "system", "content": _CONTEXT_SYSTEM},
                    {"role": "user", "content": "\n\n===\n\n".join(context_parts)},
                ],
                app_scenario="brain:t2",
                temperature=0.2,
                max_tokens=600,
            )
            enriched = safe_json_loads(llm_resp)
        except Exception as exc:
            logger.warning('[AGENT:DraftContextAgent] LLM context generation failed: %s', exc)

        # ── Step 5: Build draft_context return payload ────────────────────
        court = case.get('court') or {}
        suggested_sections = (
            enriched.get('suggested_sections')
            or _DEFAULT_SECTIONS.get(draft_type)
            or _DEFAULT_SECTIONS['petition']
        )

        draft_context = {
            'draft_for': {
                'case_id': case_id,
                'client_ids': case.get('client_ids') or [],
                'case_title': case.get('title', ''),
            },
            'location': {
                'state': court.get('state', ''),
                'district': court.get('district', ''),
                'court': court.get('court', ''),
            },
            'draft_type': draft_type,
            'case_type': case.get('case_type', ''),
            'context_summary': (
                enriched.get('context_summary')
                or case_brief
            ),
            'key_facts': enriched.get('key_facts') or [],
            'suggested_sections': suggested_sections,
            'cnr': case.get('cnr', ''),
        }

        return {
            'draft_context': draft_context,
            'case_id': case_id,
            'next_suggested_action': 'start_draft',
        }
