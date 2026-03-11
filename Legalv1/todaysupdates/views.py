import traceback
import json
import datetime
from django.http import JsonResponse
# from django.conf import settings
# from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view
from supabase_required import supabase_required
from todaysupdates.routes.handlesubscriptions import CreateandmanageSubscription
import logging
logger = logging.getLogger('django')


@api_view(["GET"])
@supabase_required
def get_subscriptions(request):
    """
    GET /todaysupdates/get-subscriptions/
    Returns the subscribed courts array for the current user.
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')  # as in your fetch_event example
        obj = CreateandmanageSubscription()
        subscribed_courts = obj.get_user_subscriptions(user_id)
        return JsonResponse({"subscribed_courts": subscribed_courts}, status=200)
    except Exception as e:
        logger.error(traceback.print_exc())
        return JsonResponse({"error": str(e)}, status=500)

@api_view(["GET"])
@supabase_required
def get_paralegal_subscription(request):
    """
    GET /todaysupdates/get-subscriptions/
    Returns the subscribed courts array for the current user.
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')  # as in your fetch_event example
        obj = CreateandmanageSubscription()
        subscribed_courts = obj.get_paralegal_courts(user_id)
        return JsonResponse({"subscribed_courts": subscribed_courts}, status=200)
    except Exception as e:
        logger.error(traceback.print_exc())
        return JsonResponse({"error": str(e)}, status=500)

@api_view(["POST"])
@supabase_required
def subscribe_court(request):
    """
    POST /todaysupdates/subscribe-court/
    Expects JSON: {"court": "<court_string>"}
    Adds the court to the user's subscribed_courts (max 4).
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = json.loads(request.body.decode("utf-8"))
        court = data.get("court")
        if not court:
            return JsonResponse({"error": "court is required"}, status=400)

        obj = CreateandmanageSubscription()
        subscribed_courts = obj.subscribe_court_and_verify_existence_and_cout(user_id, court)
        return JsonResponse({"subscribed_courts": subscribed_courts}, status=200)
    except Exception as e:
        logger.error(traceback.print_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["POST"])
@supabase_required
def unsubscribe_court(request):
    """
    POST /todaysupdates/unsubscribe-court/
    Expects JSON: {"court": "<court_string>"}
    Removes the court from the user's subscribed_courts.
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = json.loads(request.body.decode("utf-8"))
        court = data.get("court")
        if not court:
            return JsonResponse({"error": "court is required"}, status=400)

        obj = CreateandmanageSubscription()
        subscribed_courts = obj.unsubscribe_court_and_verify_existence(user_id, court)
        return JsonResponse({"subscribed_courts": subscribed_courts}, status=200)
    except Exception as e:
        logger.error(traceback.print_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["POST"])
@supabase_required
def fetch_updates(request):
    """
    POST /todaysupdates/fetch-updates/
    Body JSON can include:
      {
        "start_date": "YYYY-MM-DD" (optional),
        "end_date": "YYYY-MM-DD"   (optional),
        "court": "some_court_name" (optional) - if user wants only one court from subscribed
      }

    1) If no start_date/end_date are given, default to today's date range.
    2) If "court" is provided, we only filter for that one court (BUT must be in user's subscribed_courts).
       Otherwise, we match all subscribed courts.
    3) We look into `whatsapp_chat_sessions` for docs having an `updates` array
       containing { "court": ..., "time": ... } in the date range and in subscribed courts.
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        requested_court = data.get("court")

        obj = CreateandmanageSubscription()
        final_updates = obj.fetch_updates_for_subscribed_courts(user_id, start_date_str, end_date_str, requested_court)
        return JsonResponse({"updates": final_updates}, status=200)

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
    

@api_view(["POST"])
@supabase_required
def paralegal_subscribe_court(request):
    """
    POST /myupdates/subscribe-court/
    {
      "court": "...some_court..."
    }
    - For paralegals only
    - Limit: 3
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = json.loads(request.body.decode("utf-8"))
        court = data.get("court")

        obj = CreateandmanageSubscription()
        subscribed_courts = obj.paralegal_update_court_subscription(user_id, court)
        return JsonResponse({"subscribed_courts": subscribed_courts}, status=200)
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
    
@api_view(["POST"])
@supabase_required
def paralegal_unsubscribe_court(request):
    """
    POST /myupdates/subscribe-court/
    {
      "court": "...some_court..."
    }
    - For paralegals only
    - Limit: 3
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = json.loads(request.body.decode("utf-8"))
        court = data.get("court")

        obj = CreateandmanageSubscription()
        subscribed_courts = obj.paralegal_remove_court_subscription(user_id, court)
        return JsonResponse({"subscribed_courts": subscribed_courts}, status=200)
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

    
@api_view(["POST"])
@supabase_required
def fetch_my_updates(request):
    """
    POST /myupdates/fetch-my-updates/
    {
      "start_date": "YYYY-MM-DD" (optional),
      "end_date": "YYYY-MM-DD"   (optional),
      "court": "some_court"      (optional)
    }
    - Return ONLY the updates posted by this paralegal (e.g., phone_number or user_id check)
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        requested_court = data.get("court")

        obj = CreateandmanageSubscription()
        final_updates = obj.fetch_paralegal_court_updates(user_id, start_date_str, end_date_str, requested_court)

        return JsonResponse({"updates": final_updates}, status=200)
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def updates_list(request):
    """
    GET /api/todaysupdates/updates/
    Query params: today(bool), is_critical(bool), start_date, end_date, court, page, page_size
    Returns: {results: [...], count: N, next: bool}
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')

        today_flag = request.GET.get('today', '').lower() in ('1', 'true', 'yes')
        start_date_str = None
        end_date_str = None
        if today_flag:
            today_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            start_date_str = today_str
            end_date_str = today_str
        else:
            start_date_str = request.GET.get('start_date')
            end_date_str = request.GET.get('end_date')

        requested_court = request.GET.get('court')
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)
        is_critical = request.GET.get('is_critical', '').lower() in ('1', 'true', 'yes')

        obj = CreateandmanageSubscription()
        all_updates = obj.fetch_updates_for_subscribed_courts(user_id, start_date_str, end_date_str, requested_court)
        if not isinstance(all_updates, list):
            all_updates = []

        if is_critical:
            all_updates = [u for u in all_updates if u.get('is_critical') or u.get('critical')]

        total = len(all_updates)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = all_updates[start:end]
        has_next = end < total

        return JsonResponse({"results": page_items, "count": total, "next": has_next}, status=200)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"results": [], "count": 0, "next": False, "error": str(e)}, status=500)
