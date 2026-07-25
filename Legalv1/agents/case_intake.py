"""
agents/case_intake.py — CaseIntakeAgent

Trigger: Lawyer finishes client onboarding and creates a new case.

Steps:
  1. Accept case_description, title, court, client_ids, cnr (optional)
  2. If CNR → call ecourt_scrapped to fetch eCourts case data; extract
     case_type, parties, acts, next_hearing_date
  3. Call brain:t1 to classify case_type and suggest stage from description
  4. Create the cases document in MongoDB
  5. Return case record + next_suggested_action

API: POST /api/agents/case-intake/
"""
import uuid
import json
import logging
from datetime import datetime, timezone

from core.llm_client import chat_complete
from .base_agent import BaseAgent, safe_json_loads
from users.routes.encryption import encrypt_field

logger = logging.getLogger('django')

DB_CASES = 'cases'

_CLASSIFY_SYSTEM = """You are a legal case classifier for the Indian legal system.
Given a case description and any context, return ONLY a JSON object with:
{
  "case_type": "Civil | Criminal | Family | Labour | Constitutional | Revenue | Consumer | Other",
  "stage": "Filing | Pleadings | Evidence | Arguments | Judgment",
  "brief": "One-sentence summary of the matter (max 200 chars)",
  "acts_and_sections": ["list of applicable acts/sections if identifiable"]
}
Do not explain. Return only the JSON object."""


def _now():
    return datetime.now(timezone.utc).isoformat()


class CaseIntakeAgent(BaseAgent):
    name = 'CaseIntakeAgent'

    def _run(self, inputs: dict, db, supa_user: dict) -> dict:
        lawyer_id = supa_user.get('user_id', '')
        title = (inputs.get('title') or '').strip()
        if not title:
            raise ValueError("'title' is required.")

        case_description = (inputs.get('case_description') or '').strip()
        cnr = (inputs.get('cnr') or '').strip().upper()
        court = inputs.get('court') or {}

        ecourts_data = {}
        ecourts_enrichment = {}

        # ── Step 1: eCourts enrichment (if CNR provided) ──────────────────
        if cnr:
            try:
                from ecourt_scrapped.services import scraper_client
                result = scraper_client.post("cnr/search", {"cnr_number": cnr}, timeout=20)
                ecourts_data = result if isinstance(result, dict) else {}
                # Extract useful fields from eCourts response
                case_details = ecourts_data.get('case_details') or ecourts_data.get('caseDetails') or {}
                hearing_dates = ecourts_data.get('hearing_history') or ecourts_data.get('hearingHistory') or []
                next_date = ''
                if hearing_dates:
                    # last entry is usually next date
                    last = hearing_dates[-1] if isinstance(hearing_dates, list) else {}
                    next_date = last.get('next_date') or last.get('nextDate') or ''
                ecourts_enrichment = {
                    'case_type_ecourts': case_details.get('case_type') or case_details.get('caseType') or '',
                    'parties': case_details.get('petitioner_respondent') or '',
                    'next_hearing_ecourts': next_date,
                    'acts': case_details.get('acts') or '',
                    'raw_summary': json.dumps(case_details, ensure_ascii=False)[:800],
                }
                logger.info('[AGENT:CaseIntakeAgent] eCourts enrichment OK cnr=%s', cnr)
            except Exception as exc:
                # eCourts lookup failure is non-fatal — continue without it
                logger.warning('[AGENT:CaseIntakeAgent] eCourts lookup failed cnr=%s err=%s', cnr, exc)

        # ── Step 2: LLM classification ────────────────────────────────────
        context_parts = []
        if case_description:
            context_parts.append(f"Description: {case_description}")
        if ecourts_enrichment.get('raw_summary'):
            context_parts.append(f"eCourts data: {ecourts_enrichment['raw_summary']}")
        if ecourts_enrichment.get('parties'):
            context_parts.append(f"Parties: {ecourts_enrichment['parties']}")
        if ecourts_enrichment.get('acts'):
            context_parts.append(f"Acts/Sections: {ecourts_enrichment['acts']}")

        classification = {}
        if context_parts:
            try:
                llm_resp = chat_complete(
                    messages=[
                        {"role": "system", "content": _CLASSIFY_SYSTEM},
                        {"role": "user", "content": "\n".join(context_parts)},
                    ],
                    app_scenario="brain:t1",
                    temperature=0.1,
                    max_tokens=300,
                )
                classification = safe_json_loads(llm_resp)
                logger.info('[AGENT:CaseIntakeAgent] LLM classification: %s', classification)
            except Exception as exc:
                logger.warning('[AGENT:CaseIntakeAgent] LLM classification failed: %s', exc)

        # ── Step 3: Build and insert the case document ────────────────────
        now = _now()
        case_id = str(uuid.uuid4())

        # Merge court details — ecourts data takes lower priority than explicit input
        resolved_court = {}
        if ecourts_data.get('court_details'):
            cd = ecourts_data['court_details']
            resolved_court = {
                'state': cd.get('state', ''),
                'district': cd.get('district', ''),
                'court': cd.get('court_name') or cd.get('court', ''),
            }
        resolved_court.update({k: v for k, v in court.items() if v})

        doc = {
            '_id': case_id,
            'case_ref': (inputs.get('case_ref') or '').strip(),
            'title': title,
            'case_type': (
                inputs.get('case_type')
                or ecourts_enrichment.get('case_type_ecourts')
                or classification.get('case_type')
                or ''
            ),
            'court': resolved_court,
            'cnr': cnr,
            'lawyer_id': lawyer_id,
            'client_ids': inputs.get('client_ids') or [],
            'paralegal_ids': inputs.get('paralegal_ids') or [],
            'status': 'Active',
            'stage': inputs.get('stage') or classification.get('stage') or 'Filing',
            'filing_date': (inputs.get('filing_date') or '').strip(),
            'next_hearing': (
                inputs.get('next_hearing')
                or ecourts_enrichment.get('next_hearing_ecourts')
                or ''
            ),
            'tags': inputs.get('tags') or classification.get('acts_and_sections') or [],
            'brief': (
                inputs.get('brief')
                or classification.get('brief')
                or case_description[:200]
            ),
            'intake_source': 'agent',
            'created_at': now,
            'updated_at': now,
        }

        plaintext_brief = doc['brief']
        doc['brief'] = encrypt_field(plaintext_brief)
        db[DB_CASES].insert_one(doc)
        doc.pop('_id', None)
        doc['id'] = case_id
        doc['brief'] = plaintext_brief

        return {
            'case': doc,
            'enrichment_notes': {
                'ecourts_used': bool(ecourts_enrichment),
                'llm_classified': bool(classification),
            },
            'next_suggested_action': 'upload_documents',
        }
