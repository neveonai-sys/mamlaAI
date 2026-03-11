from django.shortcuts import render
from django.http import JsonResponse, HttpResponseNotFound
from rest_framework.decorators import api_view
from supabase_required import supabase_required
from core.init_clients import get_mongo_client
import logging
import datetime
import traceback

logger = logging.getLogger('django')


@api_view(['GET'])
@supabase_required
def dashboard_home(request):
    """
    GET /api/dashboard/home/
    Aggregates key metrics for the dashboard home screen:
    - pending_drafts: AI drafts without an exported/completed status
    - upcoming_events: count of events in the next 30 days
    - recent_updates: last 5 court updates from subscribed courts
    - recent_drafts: last 5 AI draft names + status + created_at
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'User ID not found in token'}, status=401)

        db = get_mongo_client()['legaldb']
        now = datetime.datetime.utcnow()
        in_30_days = now + datetime.timedelta(days=30)

        # ── 1. Pending drafts count ──────────────────────────────────────────
        pending_drafts = db['aidrafts_complete_data'].count_documents({
            'user_id': user_id,
            'status': {'$nin': ['exported', 'completed', 'deleted']},
        })

        # ── 2. Recent drafts (last 5) ────────────────────────────────────────
        recent_cursor = db['aidrafts_complete_data'].find(
            {'user_id': user_id},
            {'session_id': 1, 'draft_name': 1, 'status': 1, 'created_at': 1, '_id': 0},
        ).sort('created_at', -1).limit(5)
        recent_drafts = list(recent_cursor)
        for d in recent_drafts:
            if isinstance(d.get('created_at'), datetime.datetime):
                d['created_at'] = d['created_at'].isoformat()

        # ── 3. Upcoming events (next 30 days stored in user_details.meetings) ─
        upcoming_events = 0
        upcoming_events_list = []
        try:
            user_doc = db['user_details'].find_one(
                {'user_id': user_id},
                {'meetings': 1, '_id': 0},
            )
            if user_doc and user_doc.get('meetings'):
                for key, meeting in user_doc['meetings'].items():
                    start_str = meeting.get('start', '') or ''
                    if start_str:
                        try:
                            # Accept "YYYY-MM-DDTHH:MM" or full ISO
                            start_dt = datetime.datetime.fromisoformat(start_str[:16])
                            if now <= start_dt <= in_30_days:
                                upcoming_events += 1
                                upcoming_events_list.append({
                                    'id': key,
                                    'title': meeting.get('title', ''),
                                    'start': start_str,
                                    'event_type': meeting.get('Task_type', 'Other'),
                                    'location': meeting.get('courtName', '') or meeting.get('location', ''),
                                    'description': meeting.get('description', ''),
                                })
                        except (ValueError, TypeError):
                            pass
            # Sort by start ascending
            upcoming_events_list.sort(key=lambda x: x['start'])
            upcoming_events_list = upcoming_events_list[:10]
        except Exception:
            logger.warning('dashboard_home: failed to count events\n' + traceback.format_exc())

        # ── 4. Recent court updates (last 5) ─────────────────────────────────
        recent_updates = []
        try:
            pipeline = [
                {'$match': {'user_id': user_id}},
                {'$project': {'updates': {'$objectToArray': {'$ifNull': ['$updates', {}]}}}},
                {'$unwind': '$updates'},
                {'$replaceRoot': {'newRoot': '$updates.v'}},
                {'$sort': {'time': -1}},
                {'$limit': 5},
                {'$project': {'court': 1, 'update': 1, 'time': 1, '_id': 0}},
            ]
            cursor = db['whatsapp_chat_sessions'].aggregate(pipeline)
            for item in cursor:
                if isinstance(item.get('time'), datetime.datetime):
                    item['time'] = item['time'].isoformat()
                recent_updates.append(item)
        except Exception:
            logger.warning('dashboard_home: failed to fetch updates\n' + traceback.format_exc())

        return JsonResponse({
            'pending_drafts': pending_drafts,
            'upcoming_events': upcoming_events,
            'upcoming_events_list': upcoming_events_list,
            'recent_drafts': recent_drafts,
            'recent_updates': recent_updates,
        }, status=200)

    except Exception:
        logger.error('dashboard_home error\n' + traceback.format_exc())
        return JsonResponse({'error': 'Failed to load dashboard data'}, status=500)


def health(request):
    """Health check endpoint for load balancers and monitoring."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return JsonResponse({'status': 'ok', 'service': 'legalv1'}, status=200)


def schema_view(request):
    """OpenAPI schema. Only served when DEBUG=True to avoid exposing API structure in production."""
    from django.conf import settings
    if not settings.DEBUG:
        return HttpResponseNotFound()
    from drf_spectacular.views import SpectacularAPIView
    return SpectacularAPIView.as_view()(request)


def swagger_ui_view(request):
    """Swagger UI. Only served when DEBUG=True."""
    from django.conf import settings
    if not settings.DEBUG:
        return HttpResponseNotFound()
    from drf_spectacular.views import SpectacularSwaggerView
    return SpectacularSwaggerView.as_view(url_name='schema')(request)
