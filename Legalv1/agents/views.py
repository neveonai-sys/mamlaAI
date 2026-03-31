"""
agents/views.py — HTTP entry points for all Mamla agents.

All views:
  - @api_view(['POST'])
  - @supabase_required
  - Thin wrapper: parse body → call agent.run() → return JsonResponse

No business logic lives here.
"""
import json
import logging

from django.http import JsonResponse
from rest_framework.decorators import api_view
from supabase_required import supabase_required
from core.init_clients import get_mongo_client

from .case_intake import CaseIntakeAgent
from .document_intel import DocumentIntelligenceAgent
from .hearing_prep import HearingPrepAgent
from .post_hearing import PostHearingAgent
from .draft_context import DraftContextAgent
from .case_closure import CaseClosureAgent

logger = logging.getLogger('django')

# Singleton agent instances (stateless Python classes — safe to share)
_case_intake = CaseIntakeAgent()
_doc_intel = DocumentIntelligenceAgent()
_hearing_prep = HearingPrepAgent()
_post_hearing = PostHearingAgent()
_draft_context = DraftContextAgent()
_case_closure = CaseClosureAgent()


def _db():
    return get_mongo_client()['legaldb']


def _body(request) -> dict:
    try:
        return json.loads(request.body) if request.body else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def _agent_response(result: dict) -> JsonResponse:
    """Convert agent result to JsonResponse. Use 400 status on validation errors."""
    if not result.get('ok'):
        return JsonResponse(result, status=400)
    return JsonResponse(result, status=200)


# ─────────────────────────────────────────────────────────────────────────────
# CaseIntakeAgent
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def case_intake(request):
    """
    POST /api/agents/case-intake/
    Creates a new case with eCourts enrichment + LLM classification.

    Body:
      title (required), case_description, cnr, court {state, district, court},
      case_type, client_ids, paralegal_ids, filing_date, next_hearing, tags, brief
    """
    result = _case_intake.run(_body(request), _db(), request.supabase_user)
    return _agent_response(result)


# ─────────────────────────────────────────────────────────────────────────────
# DocumentIntelligenceAgent
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def document_intel(request):
    """
    POST /api/agents/document-intel/
    Extracts structured facts from documents already uploaded to TalkDoc.

    Body:
      case_id (required), document_ids (required, list of rag_document IDs)
    """
    result = _doc_intel.run(_body(request), _db(), request.supabase_user)
    return _agent_response(result)


# ─────────────────────────────────────────────────────────────────────────────
# HearingPrepAgent
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def hearing_prep(request):
    """
    POST /api/agents/hearing-prep/
    Generates an AI hearing brief and stores it as a hearing_notes record.

    Body:
      case_id (required), hearing_date (required), purpose,
      document_ids (optional), calendar_event_id (optional)
    """
    result = _hearing_prep.run(_body(request), _db(), request.supabase_user)
    return _agent_response(result)


# ─────────────────────────────────────────────────────────────────────────────
# PostHearingAgent
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def post_hearing(request):
    """
    POST /api/agents/post-hearing/
    Records hearing outcome, updates case, auto-creates follow-up tasks.

    Body:
      case_id (required), hearing_notes_id (required), outcome_text (required),
      next_date (optional, ISO date)
    """
    result = _post_hearing.run(_body(request), _db(), request.supabase_user)
    return _agent_response(result)


# ─────────────────────────────────────────────────────────────────────────────
# DraftContextAgent
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def draft_context(request):
    """
    POST /api/agents/draft-context/
    Builds enriched context for DraftingWorkspace pre-fill.

    Body:
      case_id (required), draft_type (petition|written_statement|application|reply|affidavit|notice),
      document_ids (optional)
    """
    result = _draft_context.run(_body(request), _db(), request.supabase_user)
    return _agent_response(result)


# ─────────────────────────────────────────────────────────────────────────────
# CaseClosureAgent
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def case_closure(request):
    """
    POST /api/agents/case-closure/
    Archives the case, generates a summary, cancels pending tasks,
    creates a shared client-visible closure note.

    Body:
      case_id (required), resolution_type (Settled|Disposed|Appeal|Archived|Closed),
      resolution_summary (required)
    """
    result = _case_closure.run(_body(request), _db(), request.supabase_user)
    return _agent_response(result)
