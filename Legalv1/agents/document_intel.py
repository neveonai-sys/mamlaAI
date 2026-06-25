"""
agents/document_intel.py — DocumentIntelligenceAgent

Trigger: Documents uploaded to a case (or existing TalkDoc session linked to a case).

Steps:
  1. Accept case_id, document_ids (rag_documents IDs already uploaded)
  2. For each summary query (parties, key dates, applicable law, relief sought),
     embed query + run knn_search on the provided doc_ids
  3. Call brain:t2 with assembled snippets → extract structured facts
  4. Update cases.brief if empty
  5. Return extracted facts + next_suggested_action

API: POST /api/agents/document-intel/
"""
import json
import logging
from datetime import datetime, timezone

from core.llm_client import chat_complete
from .base_agent import BaseAgent, get_case, safe_json_loads

logger = logging.getLogger('django')

_EXTRACT_SYSTEM = """You are a legal document analyst.
Given retrieved snippets from case documents, extract the following facts.
Return ONLY a JSON object with these keys (use empty string or list if not found):
{
  "parties": {
    "petitioner": "...",
    "respondent": "...",
    "others": []
  },
  "key_dates": [{"date": "...", "event": "..."}],
  "applicable_law": ["act/section combinations"],
  "relief_sought": "what the petitioner is asking for",
  "brief": "One paragraph case summary (max 300 chars)",
  "gaps": ["missing documents or information that seem needed"]
}
Do not invent facts. If a field cannot be determined, leave it empty."""

_SUMMARY_QUERIES = [
    "Who are the parties in this case? petitioner respondent names",
    "Key dates: filing date, agreements, incidents, important events",
    "Applicable law: acts sections statutes IPC CPC relevant provisions",
    "Relief sought: what is being prayed for demanded or requested",
]


def _now():
    return datetime.now(timezone.utc).isoformat()


class DocumentIntelligenceAgent(BaseAgent):
    name = 'DocumentIntelligenceAgent'

    def _run(self, inputs: dict, db, supa_user: dict) -> dict:
        lawyer_id = supa_user.get('user_id', '')
        case_id = (inputs.get('case_id') or '').strip()
        document_ids = inputs.get('document_ids') or []

        if not case_id:
            raise ValueError("'case_id' is required.")
        if not document_ids:
            raise ValueError("'document_ids' must be a non-empty list.")

        case = get_case(db, case_id, lawyer_id)

        # ── Step 1: Embed queries + KNN search ────────────────────────────
        from talkdoc.tasks import embed_texts
        from talkdoc.search import os_client, knn_search

        cli = os_client()
        raw_chunks = []

        query_vecs = embed_texts(_SUMMARY_QUERIES)
        for idx, (query, vec) in enumerate(zip(_SUMMARY_QUERIES, query_vecs)):
            try:
                hits = knn_search(cli, vec, lawyer_id, doc_ids=document_ids, k=6)
                for h in hits:
                    raw_chunks.append(h['text'])
            except Exception as exc:
                logger.warning('[AGENT:DocumentIntelligenceAgent] knn search [%d] failed: %s', idx, exc)

        if not raw_chunks:
            return {
                'facts': {},
                'brief_updated': False,
                'note': 'No document content retrieved — check document_ids and OpenSearch connectivity.',
                'next_suggested_action': 'upload_documents',
            }

        # Deduplicate and cap context size
        seen = set()
        unique_chunks = []
        for c in raw_chunks:
            key = c[:100]
            if key not in seen:
                seen.add(key)
                unique_chunks.append(c)
        context_text = "\n\n---\n\n".join(unique_chunks[:20])
        # Truncate to ~4000 chars so we stay within token budget
        context_text = context_text[:4000]

        # ── Step 2: LLM extraction ────────────────────────────────────────
        facts = {}
        try:
            llm_resp = chat_complete(
                messages=[
                    {"role": "system", "content": _EXTRACT_SYSTEM},
                    {"role": "user", "content": (
                        f"Case title: {case.get('title', '')}\n\n"
                        f"Document excerpts:\n{context_text}"
                    )},
                ],
                app_scenario="brain:t2",
                temperature=0.1,
                max_tokens=800,
            )
            facts = safe_json_loads(llm_resp)
            logger.info('[AGENT:DocumentIntelligenceAgent] extracted facts keys=%s', list(facts.keys()))
        except Exception as exc:
            logger.error('[AGENT:DocumentIntelligenceAgent] LLM extraction failed: %s', exc)

        # ── Step 3: Update cases.brief if empty ───────────────────────────
        brief_updated = False
        if facts.get('brief') and not case.get('brief'):
            db['cases'].update_one(
                {'_id': case_id},
                {'$set': {'brief': facts['brief'], 'updated_at': _now()}}
            )
            brief_updated = True
            logger.info('[AGENT:DocumentIntelligenceAgent] updated cases.brief for case_id=%s', case_id)

        # Determine next action based on case stage
        next_action = 'create_hearing_prep' if case.get('next_hearing') else 'start_draft'

        return {
            'facts': facts,
            'documents_processed': len(document_ids),
            'chunks_retrieved': len(unique_chunks),
            'brief_updated': brief_updated,
            'next_suggested_action': next_action,
        }
