"""
cases app HTTP views.
All views require @supabase_required.
"""
import json
import traceback
import logging

from django.http import JsonResponse
from rest_framework.decorators import api_view
from supabase_required import supabase_required
from core.init_clients import get_mongo_client
from core.response_utils import error_response

from .routes import case_crud, hearing_notes, case_notes, case_tasks

logger = logging.getLogger('django')


def _db():
    return get_mongo_client()['legaldb']


def _body(request) -> dict:
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# CASE CRUD
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def create_case(request):
    try:
        data = case_crud.create_case(_db(), request.supabase_user, _body(request))
        return JsonResponse({'case': data}, status=201)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to create case.', 500)


@api_view(['GET'])
@supabase_required
def list_cases(request):
    try:
        filters = {
            'status': request.GET.get('status', ''),
            'stage': request.GET.get('stage', ''),
            'search': request.GET.get('search', ''),
        }
        data = case_crud.list_cases(_db(), request.supabase_user, filters)
        return JsonResponse({'cases': data})
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to list cases.', 500)


@api_view(['GET'])
@supabase_required
def get_case(request, case_id):
    try:
        data = case_crud.get_case(_db(), request.supabase_user, case_id)
        if data is None:
            return error_response('Case not found.', 404)
        return JsonResponse({'case': data})
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to fetch case.', 500)


@api_view(['PUT', 'PATCH'])
@supabase_required
def update_case(request, case_id):
    try:
        data = case_crud.update_case(_db(), request.supabase_user, case_id, _body(request))
        return JsonResponse({'case': data})
    except (ValueError, LookupError) as e:
        return error_response(str(e), 400)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to update case.', 500)


@api_view(['POST'])
@supabase_required
def close_case(request, case_id):
    try:
        body = _body(request)
        data = case_crud.close_case(
            _db(), request.supabase_user, case_id,
            body.get('resolution_type', ''),
            body.get('summary', ''),
        )
        return JsonResponse({'case': data})
    except (ValueError, LookupError) as e:
        return error_response(str(e), 400)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to close case.', 500)


@api_view(['GET'])
@supabase_required
def get_timeline(request, case_id):
    try:
        data = case_crud.get_timeline(_db(), request.supabase_user, case_id)
        return JsonResponse(data)
    except LookupError as e:
        return error_response(str(e), 404)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to fetch timeline.', 500)


# ─────────────────────────────────────────────────────────────────────────────
# HEARING NOTES
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def create_hearing_note(request, case_id):
    try:
        data = hearing_notes.create_hearing_note(_db(), request.supabase_user, case_id, _body(request))
        return JsonResponse({'hearing_note': data}, status=201)
    except (ValueError, LookupError) as e:
        return error_response(str(e), 400)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to create hearing note.', 500)


@api_view(['GET'])
@supabase_required
def list_hearing_notes(request, case_id):
    try:
        data = hearing_notes.list_hearing_notes(_db(), request.supabase_user, case_id)
        return JsonResponse({'hearing_notes': data})
    except (LookupError, PermissionError) as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to list hearing notes.', 500)


@api_view(['GET'])
@supabase_required
def get_hearing_note(request, case_id, note_id):
    try:
        data = hearing_notes.get_hearing_note(_db(), request.supabase_user, case_id, note_id)
        return JsonResponse({'hearing_note': data})
    except LookupError as e:
        return error_response(str(e), 404)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to fetch hearing note.', 500)


@api_view(['PUT', 'PATCH'])
@supabase_required
def update_hearing_note(request, case_id, note_id):
    try:
        data = hearing_notes.update_hearing_outcome(
            _db(), request.supabase_user, case_id, note_id, _body(request)
        )
        return JsonResponse({'hearing_note': data})
    except LookupError as e:
        return error_response(str(e), 404)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to update hearing note.', 500)


# ─────────────────────────────────────────────────────────────────────────────
# CASE NOTES
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def create_case_note(request, case_id):
    try:
        data = case_notes.create_note(_db(), request.supabase_user, case_id, _body(request))
        return JsonResponse({'note': data}, status=201)
    except ValueError as e:
        return error_response(str(e), 400)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to create note.', 500)


@api_view(['GET'])
@supabase_required
def list_case_notes(request, case_id):
    try:
        data = case_notes.list_notes(_db(), request.supabase_user, case_id)
        return JsonResponse({'notes': data})
    except (LookupError, PermissionError) as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to list notes.', 500)


@api_view(['PUT', 'PATCH'])
@supabase_required
def update_case_note(request, case_id, note_id):
    try:
        data = case_notes.update_note(_db(), request.supabase_user, case_id, note_id, _body(request))
        return JsonResponse({'note': data})
    except (ValueError, LookupError) as e:
        return error_response(str(e), 400)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to update note.', 500)


@api_view(['DELETE'])
@supabase_required
def delete_case_note(request, case_id, note_id):
    try:
        case_notes.delete_note(_db(), request.supabase_user, case_id, note_id)
        return JsonResponse({'deleted': True})
    except LookupError as e:
        return error_response(str(e), 404)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to delete note.', 500)


# ─────────────────────────────────────────────────────────────────────────────
# CASE TASKS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def create_case_task(request, case_id):
    try:
        data = case_tasks.create_task(_db(), request.supabase_user, case_id, _body(request))
        return JsonResponse({'task': data}, status=201)
    except (ValueError, LookupError) as e:
        return error_response(str(e), 400)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to create task.', 500)


@api_view(['GET'])
@supabase_required
def list_case_tasks(request, case_id):
    try:
        filters = {
            'status': request.GET.get('status', ''),
            'assigned_to': request.GET.get('assigned_to', ''),
        }
        data = case_tasks.list_tasks(_db(), request.supabase_user, case_id, filters)
        return JsonResponse({'tasks': data})
    except (LookupError, PermissionError) as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to list tasks.', 500)


@api_view(['PUT', 'PATCH'])
@supabase_required
def update_case_task(request, case_id, task_id):
    try:
        data = case_tasks.update_task(_db(), request.supabase_user, case_id, task_id, _body(request))
        return JsonResponse({'task': data})
    except (ValueError, LookupError) as e:
        return error_response(str(e), 400)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to update task.', 500)


@api_view(['DELETE'])
@supabase_required
def delete_case_task(request, case_id, task_id):
    try:
        case_tasks.delete_task(_db(), request.supabase_user, case_id, task_id)
        return JsonResponse({'deleted': True})
    except LookupError as e:
        return error_response(str(e), 404)
    except PermissionError as e:
        return error_response(str(e), 403)
    except Exception:
        logger.error(traceback.format_exc())
        return error_response('Failed to delete task.', 500)
