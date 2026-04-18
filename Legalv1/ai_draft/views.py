from django.http import JsonResponse, HttpResponse, FileResponse
from rest_framework.decorators import api_view
import os
import json
import io
import datetime
from ai_draft.routes.creatupdateAIdrafts import CreateupdatefetchAIdrafts
from ai_draft.tasks import generate_draft_async, update_section_with_ai_async
from django_ratelimit.decorators import ratelimit
from django.core.files.base import ContentFile
from supabase_required import supabase_required
from django.core.cache import cache
import traceback
import logging
from core.entitlements import authorize_feature_use, consume_feature_use, get_feature_quota_payload

logger = logging.getLogger('django')


def _quota_error_response(message, quota, status):
    return JsonResponse({'error': message, 'quota': quota}, status=status)


def _authorize_draft_feature(request, feature_code):
    return authorize_feature_use(getattr(request, 'supabase_user', None), feature_code)


def _finalize_draft_quota(request, feature_code, decision):
    return consume_feature_use(getattr(request, 'supabase_user', None), feature_code, decision)


@api_view(['GET'])
@supabase_required
def get_supported_languages(request):
    """
    Returns Indian languages supported by ChatGPT.
    """
    languages = [
        'English',
        'Hindi',
        'Bengali',
        'Telugu',
        'Marathi',
        'Tamil',
        'Urdu',
        'Gujarati',
        'Kannada',
        'Malayalam',
        'Odia',
        'Punjabi',
        'Assamese',
    ]
    return JsonResponse({'languages': languages})

@api_view(['GET'])
@supabase_required
def get_total_drafts(request):
    """
    Get the total number of drafts created by current users.
    """
    supa_user = request.supabase_user
    logger.info(f"get_total_drafts ============= supa_user   ==>.>>>>> {supa_user}")
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    val = obj.get_total_drafts_count()
    return JsonResponse({'total_drafts': val})

@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='5/m', block=True)
def initiate_drafting_session(request):
    """
    Create a draft‑generation session and immediately save a “Untitled <timestamp>”
    entry in saved_drafts.
    """
    data       = json.loads(request.body)
    supa_user  = request.supabase_user
    user_id    = supa_user.get('user_id')
    user_type = supa_user.get('user_type', 'Client')  # Default to 'Client' if not specified
    decision = _authorize_draft_feature(request, 'ai_draft_generation')
    if not decision.get('allowed'):
        return _quota_error_response(decision['message'], decision['quota'], decision.get('status_code', 429))

    # For client users, ensure draft_for is empty or contains only their own user_id
    if user_type == 'Client':
        draft_for = {}
        # Log any attempt to set draft_for for client users (potential security issue)
        if data.get('draft_for'):
            logger.warning(f"Client user {user_id} attempted to set draft_for to {data.get('draft_for')}")
    else:
        # For lawyers/paralegals, use the provided draft_for or empty dict
        draft_for = data.get('draft_for', {})

    obj = CreateupdatefetchAIdrafts(user_id)
    session_id = obj.start_new_session(
        data.get('user_query'),
        draft_for,  # Use the validated draft_for
        data.get('location', {}),
        data.get('language', 'English')
    )

    # fetch the freshly‑generated sections
    draft_sections = obj.retrieve_sections_of_draft(session_id).get('mssg', [])
    draft_name = f"Untitled {datetime.datetime.now().strftime('%Y‑%m‑d %H:%M')}"
    saved_draft = obj.auto_save_initial_draft(session_id, draft_name, draft_sections)
    quota = _finalize_draft_quota(request, 'ai_draft_generation', decision)

    return JsonResponse({
        'session_id': str(session_id),
        'draft_name': draft_name,
        'draft_id'  : saved_draft.get('draft_id'),
        'draft_saved_at': saved_draft.get('saved_at'),
        'last_updated_on': saved_draft.get('last_updated_on'),
        'draft_for' : draft_for,
        'draft_sections': draft_sections,
        'quota': quota,
    })


@api_view(['POST'])
@supabase_required
def set_location(request):
    """
        - update loaction of created session
    """
    data = json.loads(request.body)
    session_id = data.get('session_id')
    state = data.get('state')
    district = data.get('district')
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)

    logger.info(f"[set_location] Received session_id: {session_id}, state: {state}, district: {district}")

    chk = obj.update_location_for_draft_creation(session_id, state, district)

    if chk.get('mssg'):
        return JsonResponse({'message': 'Location set and draft generated'})
    else:
        return JsonResponse({'message': 'invalid'}, status=400)


@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='5/m', block=True)
def update_section(request):
    """
        - update section of draft Created
    """
    data = json.loads(request.body)
    session_id = data.get('session_id')
    section_id = data.get('section_id')
    section_name = data.get('section_name')
    content = data.get('content')

    logger.info(f"[update_section] Received update for session_id: {session_id}, section_id: {section_id}")
    logger.info(f"[update_section] New section_name: {section_name}")
    logger.info(f"[update_section] New content: {content}")

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    chk = obj.update_specific_section_of_the_draft(session_id, section_id, section_name, content)
    logger.info(f"[update_section] Section {section_id} updated successfully.")

    if chk.get('mssg'):
        cache.delete(f"draft_sections:{session_id}")
        return JsonResponse({'message': 'Section updated'})
    else:
        return JsonResponse({'error': 'Section not found'}, status=404)


@api_view(['POST'])
@supabase_required
def delete_section(request):
    """
        - delete any section of draft Created
    """
    data = json.loads(request.body)
    session_id = data.get('session_id')
    section_id = data.get('section_id')
    
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    logger.info(f"[delete_section] Received delete request for session_id: {session_id}, section_id: {section_id}")

    chk = obj.delete_specific_section_of_the_draft(session_id, section_id)

    if chk.get('mssg'):
        cache.delete(f"draft_sections:{session_id}")
        return JsonResponse({'message': 'Section deleted'})
    else:
        return JsonResponse({'error': 'Section not found or already deleted'}, status=404)


@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='5/m', block=True)
def suggest_section(request):
    """
        - suggest any update in section of draft to make changes using AI
    """
    data = json.loads(request.body)
    session_id = data.get('session_id')
    section_id = data.get('section_id')
    suggestion = data.get('suggestion')

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    current_count = obj.get_ai_suggested_content_count(session_id)
    per_draft_limit = 7
    overage_decision = None

    if current_count >= per_draft_limit:
        overage_decision = authorize_feature_use(supa_user, 'ai_suggestions')
        if not overage_decision.get('allowed'):
            quota = get_feature_quota_payload(
                supa_user,
                'ai_suggestions',
                allowed=False,
                next_cta=overage_decision['quota'].get('next_cta', ''),
                message_key=overage_decision['quota'].get('message_key', ''),
                included_limit_override=per_draft_limit,
                used_count_override=current_count,
                remaining_override=0,
            )
            return JsonResponse({
                'error': 'AI suggestion limit reached for this draft.',
                'quota': quota,
            }, status=overage_decision.get('status_code', 429))

    chk = obj.update_content_using_AI_with_user_input(session_id, section_id, suggestion)

    if chk.get('mssg'):
        ai_update_count = obj.update_ai_suggested_content_count(session_id)
        wallet_credits_charged = 0
        message_key = ''
        if overage_decision:
            wallet_quota = consume_feature_use(supa_user, 'ai_suggestions', overage_decision)
            wallet_credits_charged = wallet_quota.get('wallet_credits_charged', 0)
            message_key = wallet_quota.get('message_key', '')
        elif ai_update_count >= 5:
            message_key = 'quota_low_remaining'

        quota = get_feature_quota_payload(
            supa_user,
            'ai_suggestions',
            next_cta='continue',
            message_key=message_key,
            wallet_credits_charged=wallet_credits_charged,
            included_limit_override=per_draft_limit,
            used_count_override=ai_update_count,
            remaining_override=max(per_draft_limit - ai_update_count, 0),
        )
        return JsonResponse({
            'updated_content': chk.get('mssg'),
            'ai_update_count': ai_update_count,
            'quota': quota,
        })
    else:
        quota = get_feature_quota_payload(
            supa_user,
            'ai_suggestions',
            next_cta='continue',
            included_limit_override=per_draft_limit,
            used_count_override=current_count,
            remaining_override=max(per_draft_limit - current_count, 0),
        )
        return JsonResponse({'updated_content': '', 'ai_update_count': current_count, 'quota': quota}, status=400)



@api_view(['POST'])
@supabase_required
def add_section(request):
    """
        - add new section to the created draft
    """
    data = json.loads(request.body)
    session_id = data.get('session_id')
    section_name = data.get('section_name')
    content = data.get('content')  # Can be empty or user-provided

    logger.info(f"[add_section] Adding new section to session_id: {session_id}")
    logger.info(f"[add_section] Section name: {section_name}")
    logger.info(f"[add_section] Initial content: {content}")

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    chk = obj.add_new_section_in_existing_draft(session_id, section_name, content)
    if chk.get('mssg'):
        cache.delete(f"draft_sections:{session_id}")
        return JsonResponse({'message': 'Section added', 'section': chk.get('mssg')})
    else:
        return JsonResponse({'error': 'Failed to add section'}, status=500)


@api_view(['GET'])
@supabase_required
def download_draft(request):
    """
        -- if user is satisfied with the content they'll download the final draft
    """
    session_id = request.GET.get('session_id')

    logger.info(f"[download_draft] Download request received for session_id: {session_id}")

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    chk = obj.prepare_content_for_download(session_id)

    logger.info(f"[download_draft] Sending draft as downloadable response.")

    if chk.get('mssg'):
        # Return as a downloadable response
        response = HttpResponse(chk.get('mssg').read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = 'attachment; filename=legal_draft.docx'
        return response
    else:
        HttpResponse('No draft available to download.', status=400)


@api_view(['POST'])
@supabase_required
def update_section_order(request):
    """
        -- user may move any section up or down the way they want
    """
    data = json.loads(request.body)
    session_id = data.get('session_id')
    draft_sections = data.get('draft_sections')

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    chk = obj.adjust_section_position_in_draft(session_id,draft_sections)
    if chk.get('mssg'):
        cache.delete(f"draft_sections:{session_id}")
        return JsonResponse({'message': 'Section order updated'})
    else:
        return JsonResponse({'error': 'Failed to add section'}, status=500)

@api_view(['GET'])
@supabase_required
def get_section_history(request):
    """
        -- user can see section history if any changes are made
    """
    session_id = request.GET.get('session_id')
    section_id = request.GET.get('section_id')

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    chk = obj.retrieve_history_of_section_of_draft_if_updated(session_id, section_id)
    if chk.get('mssg') or chk.get('mssg')==[]:
        return JsonResponse({'history': chk.get('mssg')})
    else:
        return JsonResponse({'error': 'Section not found'}, status=404)


@api_view(['GET'])
@supabase_required
def get_draft_sections(request):
    """
    Retrieve whole draft section wise. 
    Returns status if draft is still generating.
    Uses caching for better performance.
    """
    session_id = request.GET.get('session_id')

    logger.info(f"[get_draft_sections] Fetching draft sections for session_id: {session_id}")
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    
    # Try cache first for completed drafts
    cache_key = f"draft_sections:{session_id}"
    cached_sections = cache.get(cache_key)
    
    if cached_sections:
        logger.info(f"[get_draft_sections] Returning cached sections for {session_id}")
        return JsonResponse({
            'draft_sections': cached_sections,
            'ai_suggested_update_count': 0,
            'status': 'completed',
            'cached': True
        })
    
    obj = CreateupdatefetchAIdrafts(user_id)
    chk = obj.retrieve_sections_of_draft(session_id)
    
    if chk.get('mssg'):
        sections = chk.get('mssg')
        # Cache completed drafts
        if sections:
            cache.set(cache_key, sections, timeout=3600)  # 1 hour
            
        return JsonResponse({
            'draft_sections': sections,
            'ai_suggested_update_count': chk.get('ai_suggested_update_count'),
            'status': chk.get('status', 'completed'),
            'cached': False
        })
    else:
        return JsonResponse({'error': 'Invalid session ID', 'status': 'error'}, status=400)


@api_view(['GET'])
@supabase_required
def get_draft_single_section(request):
    """
        -- retrieve specific section from the draft
    """
    session_id = request.GET.get('session_id')
    section_id = request.GET.get('section_id')

    logger.info(f"[get_draft_sections] Fetching draft sections for session_id: {session_id} and section_id: {section_id}")
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    chk=obj.retrieve_single_section_from_session(session_id, section_id)
    
    if chk.get('mssg'):
        return JsonResponse({'draft_sections': chk.get('mssg')})
    else:
        return JsonResponse({'error': 'Invalid session or section ID'}, status=400)
        

@api_view(['POST'])
@supabase_required
def revert_to_original(request):
    """
        -- if user has made mistakes, they can always revert back to the intial produced draft state
    """
    data = json.loads(request.body)
    session_id = data.get('session_id')

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    chk = obj.revert_draft_changes_to_intial_stage(session_id)
    if chk.get('mssg'):
        return JsonResponse({'message': 'Draft reverted to original'})
    else:
        return JsonResponse({'error': 'Original draft not found'}, status=404)
    

@api_view(['POST'])
@supabase_required
def save_draft(request):
    """
    Overwrite or create a saved draft for the session.
    POST:
    {
      "session_id": "...",
      "draft_name": "...",
      "draft_sections": [...],
      "draft_id": "..."   (optional: if provided, overwrite)
    }
    """
    data = json.loads(request.body)
    session_id = data.get('session_id')
    draft_name = data.get('draft_name')
    draft_sections = data.get('draft_sections')
    draft_id = data.get('draft_id')  # optional

    if not session_id or not draft_name or not draft_sections:
        return JsonResponse({'error': 'Missing required parameters.'}, status=400)

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')

    obj = CreateupdatefetchAIdrafts(user_id)

    chk = obj.save_semi_filled_drafts(session_id, draft_name, draft_sections, draft_id)
    if chk.get('mssg'):
        return JsonResponse({
            'message': 'Successfully Saved',
            'draft_id': chk.get('draft_id'),
            'saved_at': chk.get('saved_at'),
            'last_updated_on': chk.get('last_updated_on'),
        })
    else:
        return JsonResponse({'error': 'Failed'}, status=500)



@api_view(['GET'])
@supabase_required
def get_saved_drafts(request):
    """
    Retrieve all saved drafts for a session.
    Query Parameters:
    - session_id: string
    """

    session_id = request.GET.get('session_id')

    if not session_id:
        logger.error("Missing session_id parameter.")
        return JsonResponse({'error': 'Missing session_id parameter.'}, status=400)
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    chk = obj.get_saved_draft_list(session_id)
    if chk.get('mssg'):
        return JsonResponse({'saved_drafts': chk.get('mssg')}, status=200)
    else:
        return JsonResponse({'saved_drafts': []}, status=200)

@api_view(["GET"])
@supabase_required
def get_user_saved_drafts_v2(request):
    """
    Return every saved_draft that belongs to the logged‑in user.
    Each draft_for item is now a list of
        [{ "client_id": "...", "client_name": "..." }, …]
    """
    user_id = request.supabase_user.get("user_id")
    db = CreateupdatefetchAIdrafts(user_id).get_mongo_client_db()
    saved, total = [], 0
    for sess in db.find({"user_id": user_id},
                        {"saved_drafts": 1, "draft_for": 1, "last_updated_on": 1}):
        sess_for = sess.get("draft_for", [])          # ← single source of truth
        for d in sess.get("saved_drafts", []):
            saved.append({
                "draft_id" : d["draft_id"],
                "draft_name" : d["draft_name"],
                "session_id" : str(sess["_id"]),
                "created_on" : d.get("saved_at"),
                "last_updated_on": sess.get("last_updated_on"),
                "draft_for" : sess_for,          # ← always from session
            })
            total += 1

    return JsonResponse({"saved_drafts": saved,
                         "pagination"  : {"total_count": total}}, status=200)

@api_view(['POST'])
@supabase_required
def delete_saved_draft(request):
    """
    Delete a saved draft from the session.
    Expected JSON payload:
    {
        "session_id": "string",
        "draft_id": "string"
    }
    """

    data = json.loads(request.body)
    session_id = data.get('session_id')
    draft_id = data.get('draft_id')

    if not session_id or not draft_id:
        logger.error("Missing required parameters.")
        return JsonResponse({'error': 'Missing required parameters.'}, status=400)
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
        # Validate session_id and draft_id format
    chk = obj.delete_saved_draft(session_id, draft_id)

    if chk.get('mssg'):
        logger.info(f"Draft '{draft_id}' deleted successfully for session_id: {session_id}")
        return JsonResponse({'message': 'Draft deleted successfully.'}, status=200)
    else:
        logger.error(f"Draft '{draft_id}' not found for session_id: {session_id}")
        return JsonResponse({'error': 'Draft not found.'}, status=404)

# @api_view(['GET'])
# @supabase_required
# def get_user_saved_drafts(request):
#     """
#     Retrieve the list of saved drafts for the user.
#     Query Parameters:
#     - user_id: string
#     """
#     supa_user = request.supabase_user
    # user_id = supa_user.get('user_id')

#     if not user_id:
#         logger.error("Missing user_id parameter.")
#         return JsonResponse({'error': 'Missing user_id parameter.'}, status=400)

#     obj = CreateupdatefetchAIdrafts(user_id)
#     chk = obj.get_saved_draft_list()
#     if chk.get('mssg'):
#         return JsonResponse({'saved_drafts': chk.get('mssg')}, status=200)
#     else:
#         logger.error(f"Exception in get_user_saved_drafts: {traceback.format_exc()}")
#         return JsonResponse({'error': 'An error occurred while retrieving saved drafts.'}, status=500)
    

@api_view(['GET'])
@supabase_required
def get_user_saved_drafts(request):
    """
    Retrieve the list of saved drafts for the user with pagination and search.
    Query Parameters:
    - page: integer (default=1)
    - page_size: integer (default=10)
    - search_field: string (e.g., 'draft_name', 'personal', 'caseid', 'clientid', 'caseid_with_clientid', 'created_on', 'last_updated_on')
    - search_query: string
    """
    # Assuming you have a way to get user_id from the request, e.g., via JWT or session
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    # Pagination parameters
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))

    # Search parameters
    search_field = request.GET.get('search_field', None)
    search_query = request.GET.get('search_query', None)

    obj = CreateupdatefetchAIdrafts(user_id)
    logger.info(f"get_user_saved_drafts ============= request   ==>.>>>>> {request}")
    # Build the query filter
    filter_query = {'user_id': user_id}
    if search_field and search_query:
        if search_field == 'draft_name':
            filter_query['saved_drafts.draft_name'] = {'$regex': search_query, '$options': 'i'}
        elif search_field == 'personal':
            if search_query.lower() in ['yes', 'y', 'true', '1']:
                filter_query['draft_for.personal'] = 'Y'
            elif search_query.lower() in ['no', 'n', 'false', '0']:
                filter_query['draft_for.personal'] = 'N'
            else:
                return JsonResponse({'error': 'Invalid search query for personal.'}, status=400)
        elif search_field == 'caseid':
            filter_query['draft_for.caseid'] = {'$in': [search_query]}
        elif search_field == 'clientid':
            filter_query['draft_for.clientid'] = {'$in': [search_query]}
        elif search_field == 'caseid_with_clientid':
            # Assuming search_query is a part of caseid_with_clientid details
            filter_query['draft_for.caseid_with_clientid'] = {'$elemMatch': {'$regex': search_query, '$options': 'i'}}
        elif search_field in ['created_on', 'last_updated_on']:
            try:
                search_date = datetime.datetime.strptime(search_query, '%Y-%m-%d')
                filter_query[search_field] = {'$gte': search_date}
            except ValueError:
                return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
        else:
            return JsonResponse({'error': 'Invalid search_field parameter.'}, status=400)
    logger.info(f"get_user_saved_drafts ===============>.>>>>> {filter_query}")

    chk = obj.get_saved_draft_list(page, page_size, filter_query)

    if not chk.get('err'):
        return JsonResponse(chk, status=200)
    else:
        logger.error(f"Exception in get_user_saved_drafts: {traceback.format_exc()}")
        return JsonResponse({'error': 'An error occurred while retrieving saved drafts.'}, status=500)


@api_view(['GET'])
@supabase_required
def load_saved_draft(request):
    """
    Load a saved draft based on draft_id and session_id.
    Query Parameters:
    - session_id: string
    - draft_id: string
    """
    session_id = request.GET.get('session_id')
    draft_id = request.GET.get('draft_id')

    if not session_id or not draft_id:
        logger.error("Missing session_id or draft_id parameter.")
        return JsonResponse({'error': 'Missing session_id or draft_id parameter.'}, status=400)

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    # Validate session_id and draft_id format
    chk = obj.load_saved_draft_details(session_id, draft_id)
    if chk.get('draft_sections'):
        return JsonResponse({'draft_sections': chk.get('draft_sections')}, status=200)
    else:
        logger.error(f"Exception in get_user_saved_drafts: {traceback.format_exc()}")
        return JsonResponse(chk, status=500)


@api_view(['POST'])
@supabase_required
def upload_template(request):
    """
    Upload and process a template file OR use an existing template from Mongo.
    
    POST Parameters:
      - draft_type (string) [required for both flows]
      - file (file) [required IF user is uploading a local file]
      - existing_filename (string) [required IF user is using an existing server template]
    """
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    decision = _authorize_draft_feature(request, 'ai_draft_generation')
    if not decision.get('allowed'):
        return _quota_error_response(decision['message'], decision['quota'], decision.get('status_code', 429))
    
    # Always require draft_type
    draft_type = request.POST.get('draft_type', '').strip()
    if not user_id or not draft_type:
        logger.error("Missing user_id or draft_type in request.")
        return JsonResponse({'error': 'Missing required parameters (user_id or draft_type).'}, status=400)

    # Optional param for existing template scenario
    existing_filename = request.POST.get('existing_template_name', '').strip()
    
    # File if user is uploading
    file = request.FILES.get('file', None)

    # If neither a file nor an existing_filename was provided, bail
    if not existing_filename and not file:
        logger.error("Must provide either 'file' or 'existing_filename'.")
        return JsonResponse({'error': 'Missing required parameters (file or existing_filename).'}, status=400)

    # If 'draft_for' was appended, parse it
    draft_for_str = request.POST.get('draft_for', '')
    try:
        draft_for = json.loads(draft_for_str) if draft_for_str else {}
    except Exception as e:
        logger.error(f"Failed to parse draft_for: {e}")
        draft_for = {}

    obj = CreateupdatefetchAIdrafts(user_id)

    try:
        if existing_filename:
            # ========== Flow A: "Use existing template" from Mongo ==========

            # Fetch the template text from your 'draft_content_data' collection
            file_text = obj.fetch_existing_template_text(existing_filename, draft_type)
            if not file_text:
                logger.error(f"No content found for existing template: {existing_filename}, draft_type: {draft_type}")
                return JsonResponse({'error': 'Existing template not found or has no content.'}, status=400)
            
            # Generate draft sections from the text
            draft_sections = obj.generate_draft_sections_from_template(file_text, draft_type)

        else:
            # ========== Flow B: "Upload local file" ==========

            file_name = file.name.lower()
            file_stream = io.BytesIO(file.read())
            # Extract text from the file
            file_text = obj.extract_text_from_file(file_stream, file_name)
            # Generate draft sections
            draft_sections = obj.generate_draft_sections_from_template(file_text, draft_type)

        # In either case, save the draft using your existing logic
        chk = obj.save_draft_from_template(draft_type, draft_sections, draft_for)

        if chk.get("mssg"):
            quota = _finalize_draft_quota(request, 'ai_draft_generation', decision)
            return JsonResponse({
                'message': 'Template uploaded/processed successfully.',
                'session_id': chk["mssg"],
                'quota': quota,
            }, status=200)
        else:
            logger.error(f"Exception in upload_template: {traceback.format_exc()}")
            return JsonResponse(
                {'error': 'An error occurred while uploading/processing the template.'}, 
                status=500
            )

    except Exception as e:
        logger.error(f"Error in upload_template: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@supabase_required
def create_drfatsession_by_casedocument(request):
    """
    Upload a case document, process it, and generate a draft.
    POST Parameters:
    - user_id: string
    - file: file
    """

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    decision = _authorize_draft_feature(request, 'ai_draft_generation')
    if not decision.get('allowed'):
        return _quota_error_response(decision['message'], decision['quota'], decision.get('status_code', 429))
    file = request.FILES.get('file')
    draft_for = json.loads(request.POST.get('draft_for'))
    language  = request.POST.get('language','English')

    logger.info(f"create_drfatsession_by_casedocument ---->>>>> {draft_for} ====== {type(draft_for)}")

    if not user_id or not file:
        logger.error("Missing required parameters.")
        return JsonResponse({'error': 'Missing required parameters.'}, status=400)

    obj = CreateupdatefetchAIdrafts(user_id)

    # Save the uploaded file
    # file_path = default_storage.save(f'case_documents/{file.name}', ContentFile(file.read()))
    # absolute_file_path = os.path.join(MEDIA_ROOT, file_path)

    # Extract text from the file
    # file_text = obj.extract_text_from_file(absolute_file_path)

    # Read the uploaded file into a BytesIO object
    file_stream = io.BytesIO(file.read())
    file_name = file.name.lower()
    # Extract text from the file
    file_text = obj.extract_text_from_file(file_stream, file_name)

    # Use GPT to process the text and generate draft sections
    draft_sections = obj.generate_draft_sections_with_gpt(file_text, language)

    chk = obj.insert_draft_session_for_casedocument(draft_sections, draft_for, language)
    if chk.get("mssg"):
        quota = _finalize_draft_quota(request, 'ai_draft_generation', decision)
        return JsonResponse({'message': 'Case document processed successfully.', 'session_id': chk.get("mssg"), 'quota': quota}, status=200)
    else:
        logger.error(f"Exception in file_lawsuit: {traceback.format_exc()}")
        return JsonResponse({'error': 'An error occurred while processing the case document.'}, status=500)


@api_view(['GET'])
@supabase_required
def send_default_template_for_create_draft(request):
    # Path to the template file
    template_path = '../Creat_Draft_Petition.docx'
    logger.info(template_path)
    if not os.path.exists(template_path):
        return JsonResponse({"error": "Template not found."}, status=404)
    
    # Serve the file using FileResponse
    response = FileResponse(open(template_path, 'rb'), as_attachment=True, filename='legal_draft_template.docx')
    return response


@api_view(['GET'])
@supabase_required
def get_draft_for_draftsession_id(request):
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({'error': 'session_id parameter is required.'}, status=400)

    obj = CreateupdatefetchAIdrafts(user_id)
    chk = obj.fetch_draft_for(session_id)
    if 'draft_for' in chk:
        return JsonResponse(chk, status=200)
    else:
        return JsonResponse(chk, status=500)


# ─── New REST-compatible views added for mamlaAI frontend ────────────────────

@api_view(['GET'])
@supabase_required
def list_drafts(request):
    """GET aidrafts/list/ — paginated list of saved drafts with 'results' key."""
    user_id = request.supabase_user.get("user_id")
    page_size = int(request.GET.get('page_size', 20))
    page = int(request.GET.get('page', 1))
    q = request.GET.get('q', '').strip().lower()
    case_id = request.GET.get('case_id', '').strip()

    db = CreateupdatefetchAIdrafts(user_id).get_mongo_client_db()
    base_query = {"user_id": user_id}
    if case_id:
        base_query["draft_for.caseid"] = case_id
    saved = []
    for sess in db.find(base_query,
                        {"saved_drafts": 1, "draft_for": 1, "last_updated_on": 1, "status": 1}):
        sess_for = sess.get("draft_for", {})
        for d in sess.get("saved_drafts", []):
            name = d.get("draft_name", "")
            if q and q not in name.lower():
                continue
            saved.append({
                "id": d["draft_id"],
                "draft_id": d["draft_id"],
                "title": name,
                "draft_name": name,
                "session_id": str(sess["_id"]),
                "created_at": d.get("saved_at"),
                "status": sess.get("status", "draft"),
                "draft_for": sess_for,
            })
    saved.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    total = len(saved)
    start = (page - 1) * page_size
    results = saved[start:start + page_size]
    return JsonResponse({
        "results": results,
        "count": total,
        "next": f"?page={page + 1}" if start + page_size < total else None,
    }, status=200)


@api_view(['POST'])
@supabase_required
def section_edit(request):
    """POST aidrafts/section_edit/ — edit a section by index."""
    data = json.loads(request.body)
    session_id = data.get('session_id')
    section_index = data.get('section_index', 0)
    new_content = data.get('new_content', '')

    user_id = request.supabase_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    sections = obj.retrieve_sections_of_draft(session_id).get('mssg', [])
    if not sections or section_index >= len(sections):
        return JsonResponse({'error': 'Section not found'}, status=404)
    sec = sections[section_index]
    chk = obj.update_specific_section_of_the_draft(
        session_id, sec.get('section_id'), sec.get('section_title'), new_content
    )
    if chk.get('mssg'):
        return JsonResponse({'message': 'Section updated'})
    return JsonResponse({'error': 'Failed to update section'}, status=500)


@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='10/m', block=True)
def refine_section(request):
    """POST aidrafts/refine_section/ — AI refinement of section by index."""
    data = json.loads(request.body)
    session_id = data.get('session_id')
    section_index = data.get('section_index', 0)
    instruction = data.get('instruction', '')

    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    sections = obj.retrieve_sections_of_draft(session_id).get('mssg', [])
    if not sections or section_index >= len(sections):
        return JsonResponse({'error': 'Section not found'}, status=404)
    sec = sections[section_index]
    section_id = sec.get('section_id')

    current_count = obj.get_ai_suggested_content_count(session_id)
    per_draft_limit = 7
    overage_decision = None
    if current_count >= per_draft_limit:
        overage_decision = authorize_feature_use(supa_user, 'ai_suggestions')
        if not overage_decision.get('allowed'):
            quota = get_feature_quota_payload(
                supa_user,
                'ai_suggestions',
                allowed=False,
                next_cta=overage_decision['quota'].get('next_cta', ''),
                message_key=overage_decision['quota'].get('message_key', ''),
                included_limit_override=per_draft_limit,
                used_count_override=current_count,
                remaining_override=0,
            )
            return JsonResponse({
                'error': 'AI suggestion limit reached for this draft.',
                'quota': quota,
            }, status=overage_decision.get('status_code', 429))

    chk = obj.update_content_using_AI_with_user_input(session_id, section_id, instruction)
    refined = chk.get('mssg', '')
    ai_update_count = obj.update_ai_suggested_content_count(session_id)
    wallet_credits_charged = 0
    message_key = ''
    if overage_decision:
        wallet_quota = consume_feature_use(supa_user, 'ai_suggestions', overage_decision)
        wallet_credits_charged = wallet_quota.get('wallet_credits_charged', 0)
        message_key = wallet_quota.get('message_key', '')
    elif ai_update_count >= 5:
        message_key = 'quota_low_remaining'

    quota = get_feature_quota_payload(
        supa_user,
        'ai_suggestions',
        next_cta='continue',
        message_key=message_key,
        wallet_credits_charged=wallet_credits_charged,
        included_limit_override=per_draft_limit,
        used_count_override=ai_update_count,
        remaining_override=max(per_draft_limit - ai_update_count, 0),
    )
    return JsonResponse({'refined_content': refined, 'content': refined, 'ai_update_count': ai_update_count, 'quota': quota})


@api_view(['POST'])
@supabase_required
def export_draft(request):
    """POST aidrafts/export/ — download draft as docx/pdf."""
    data = json.loads(request.body)
    session_id = data.get('session_id')
    fmt = data.get('format', 'docx')

    user_id = request.supabase_user.get('user_id')
    obj = CreateupdatefetchAIdrafts(user_id)
    chk = obj.prepare_content_for_download(session_id)
    if chk.get('mssg'):
        response = HttpResponse(
            chk.get('mssg').read(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename=legal_draft.{fmt}'
        return response
    return JsonResponse({'error': 'No draft available'}, status=400)


# ─── Guided Drafting endpoints ────────────────────────────────────────────────

@api_view(['POST'])
@supabase_required
def guide_start(request):
    """POST aidrafts/guide/start/ — Start a new guided drafting conversation."""
    import agents.conversational_draft_agent as cda
    data = json.loads(request.body)
    user_id = request.supabase_user.get('user_id')
    result = cda.start(
        user_id=user_id,
        case_id=data.get('case_id') or None,
        document_ids=data.get('document_ids') or None,
    )
    if not result.get('ok'):
        return JsonResponse({'error': result.get('error', 'Failed to start session.')}, status=400)
    return JsonResponse({'conv_id': result['conv_id'], 'message': result['message']})


@api_view(['POST'])
@supabase_required
def guide_message(request):
    """POST aidrafts/guide/message/ — Send a user message in the guided conversation."""
    import agents.conversational_draft_agent as cda
    data = json.loads(request.body)
    user_id = request.supabase_user.get('user_id')
    conv_id = (data.get('conv_id') or '').strip()
    user_text = (data.get('message') or '').strip()
    if not conv_id or not user_text:
        return JsonResponse({'error': 'conv_id and message are required.'}, status=400)
    result = cda.message(conv_id=conv_id, user_id=user_id, user_text=user_text)
    if not result.get('ok'):
        return JsonResponse({'error': result.get('error', 'Failed to process message.')}, status=400)
    return JsonResponse({
        'reply': result['reply'],
        'ready': result['ready'],
        'draft_plan': result.get('draft_plan'),
    })


@api_view(['POST'])
@supabase_required
def guide_upload_doc(request):
    """POST aidrafts/guide/upload_doc/ — Process newly uploaded docs mid-conversation."""
    import agents.conversational_draft_agent as cda
    data = json.loads(request.body)
    user_id = request.supabase_user.get('user_id')
    conv_id = (data.get('conv_id') or '').strip()
    document_ids = data.get('document_ids') or []
    if not conv_id or not document_ids:
        return JsonResponse({'error': 'conv_id and document_ids are required.'}, status=400)
    result = cda.handle_doc_upload(conv_id=conv_id, user_id=user_id, document_ids=document_ids)
    if not result.get('ok'):
        return JsonResponse({'error': result.get('error', 'Document processing failed.')}, status=400)
    return JsonResponse({'reply': result['reply']})


@api_view(['POST'])
@supabase_required
def guide_generate(request):
    """POST aidrafts/guide/generate/ — Generate the draft from the gathered context."""
    import agents.conversational_draft_agent as cda
    data = json.loads(request.body)
    user_id = request.supabase_user.get('user_id')
    conv_id = (data.get('conv_id') or '').strip()
    if not conv_id:
        return JsonResponse({'error': 'conv_id is required.'}, status=400)
    # quota gate — reuse same feature code as regular draft generation
    decision = _authorize_draft_feature(request, 'ai_draft_generation')
    if not decision.get('allowed'):
        return _quota_error_response(decision['message'], decision['quota'], decision.get('status_code', 429))
    result = cda.generate(conv_id=conv_id, user_id=user_id)
    if not result.get('ok'):
        return JsonResponse({'error': result.get('error', 'Draft generation failed.')}, status=400)
    _finalize_draft_quota(request, 'ai_draft_generation', decision)
    return JsonResponse({'session_id': result['session_id']})
