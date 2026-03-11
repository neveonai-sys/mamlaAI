# Create your views here.
# from rest_framework import status
from rest_framework.decorators import api_view
# from rest_framework.response import Response
from django.http import JsonResponse
# import jwt
from django.core.mail import send_mail
import requests
import datetime as dt
import json
import uuid
# from datetime import datetime
# import calendar
import traceback
from .routes.createupdateevents import Eventmanagement
# from celery import chain
# from django.conf import settings
from supabase_required import supabase_required
from django_ratelimit.decorators import ratelimit
from core.email_templates import EmailTemplates, format_datetime_for_email
import logging

logger = logging.getLogger('django')

MEETING_TYPES = {'VideoCall', 'VoiceCall', 'InPerson', 'Other'}
DEFAULT_EVENT_DURATION_MINUTES = 60


def _clean_text(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return bool(value)


def _coerce_list(value):
    if isinstance(value, list):
        return [_clean_text(item) for item in value if _clean_text(item)]
    if isinstance(value, str):
        parts = []
        for chunk in value.replace('\n', ',').split(','):
            cleaned = _clean_text(chunk)
            if cleaned:
                parts.append(cleaned)
        return parts
    return []


def _parse_datetime_value(value, *, all_day=False, default_time='09:00'):
    cleaned = _clean_text(value)
    if not cleaned:
        return None

    try:
        if 'T' in cleaned:
            return dt.datetime.fromisoformat(cleaned)
        if all_day:
            return dt.datetime.combine(dt.date.fromisoformat(cleaned[:10]), dt.time.min)
        return dt.datetime.fromisoformat(f'{cleaned[:10]}T{default_time}')
    except ValueError:
        return None


def _format_dt(value, *, all_day=False):
    if not value:
        return ''
    return value.date().isoformat() if all_day else value.strftime('%Y-%m-%dT%H:%M')


def _build_virtual_link(meeting_type):
    if meeting_type in {'VideoCall', 'VoiceCall'}:
        return f'https://{meeting_type.lower()}-{uuid.uuid4().hex[:8]}-call.com'
    return ''


def _normalize_event_payload(data, *, existing=None):
    source = dict(existing or {})
    source.update(dict(data or {}))
    status_value = _clean_text(source.get('Status')) or _clean_text(source.get('status')) or 'Y'

    meeting_type = (
        _clean_text(source.get('meetingtype'))
        or _clean_text(source.get('meetingType'))
        or _clean_text(source.get('meeting_mode'))
        or 'InPerson'
    )
    if meeting_type not in MEETING_TYPES:
        meeting_type = 'Other'

    all_day = _coerce_bool(source.get('allDay'))
    start_dt = _parse_datetime_value(source.get('start'), all_day=all_day)
    end_dt = _parse_datetime_value(source.get('end'), all_day=all_day)

    if start_dt and not end_dt:
        end_dt = start_dt if all_day else start_dt + dt.timedelta(minutes=DEFAULT_EVENT_DURATION_MINUTES)
    if start_dt and end_dt and end_dt < start_dt:
        end_dt = start_dt if all_day else start_dt + dt.timedelta(minutes=DEFAULT_EVENT_DURATION_MINUTES)

    attendees = _coerce_list(source.get('attendees'))
    lead_counsel = _clean_text(source.get('leadCounsel')) or _clean_text(source.get('assigned_counsel'))
    if not lead_counsel and attendees:
        lead_counsel = attendees[0]

    meeting_link = _clean_text(source.get('meetinglink'))
    if not meeting_link and meeting_type in {'VideoCall', 'VoiceCall'}:
        meeting_link = _build_virtual_link(meeting_type)

    event_type = _clean_text(source.get('event_type')) or _clean_text(source.get('Task_type')) or 'Other'
    task_type = _clean_text(source.get('Task_type')) or _clean_text(source.get('taskType')) or event_type

    normalized = {
        'title': _clean_text(source.get('title')),
        'description': _clean_text(source.get('description')),
        'start': _format_dt(start_dt, all_day=all_day),
        'end': _format_dt(end_dt, all_day=all_day),
        'allDay': all_day,
        'eventType': event_type,
        'event_type': event_type,
        'taskType': task_type,
        'Task_type': task_type,
        'meetingtype': meeting_type,
        'meetingType': meeting_type,
        'meetinglink': meeting_link,
        'caseId': _clean_text(source.get('caseId')),
        'courtName': _clean_text(source.get('courtName')),
        'courtNumber': _clean_text(source.get('courtNumber')),
        'clientName': _clean_text(source.get('clientName')),
        'partyBEmail': _clean_text(source.get('partyBEmail')),
        'judgeName': _clean_text(source.get('judgeName')),
        'sendReminder': _clean_text(source.get('sendReminder')) or _clean_text(source.get('send_remainder')) or 'None',
        'send_remainder': _clean_text(source.get('send_remainder')) or 'None',
        'occurrence': _clean_text(source.get('occurrence')) or 'only once',
        'location': _clean_text(source.get('location')),
        'timezone': _clean_text(source.get('timezone')) or 'Asia/Kolkata',
        'internalNotes': _clean_text(source.get('internalNotes')),
        'leadCounsel': lead_counsel,
        'assigned_counsel': lead_counsel,
        'attendees': attendees,
        'conflict_status': _clean_text(source.get('conflict_status')) or 'clear',
        'resolution_summary': _clean_text(source.get('resolution_summary')),
        'Status': status_value,
        'status': status_value,
        'recurring': _coerce_bool(source.get('recurring')),
    }

    if start_dt:
        normalized['startdate'] = start_dt.date().isoformat()
        normalized['enddate'] = (end_dt or start_dt).date().isoformat()
        if not all_day:
            normalized['starttime'] = start_dt.strftime('%H:%M')
            normalized['endtime'] = (end_dt or start_dt).strftime('%H:%M')

    return normalized


def _persisted_event_id(base_id, event_payload):
    normalized = _normalize_event_payload(event_payload, existing=event_payload)
    start_dt, _ = _event_bounds(normalized)
    if not base_id or not start_dt:
        return base_id
    return f"{base_id}_{start_dt.strftime('%Y%m%d')}"


def _serialize_event(event_id, raw_event):
    serialized = dict(raw_event)
    all_day = _coerce_bool(serialized.get('allDay'))
    if not serialized.get('start') and serialized.get('startdate'):
        serialized['start'] = serialized.get('startdate') if all_day else f"{serialized.get('startdate')}T{serialized.get('starttime') or '09:00'}"
    if not serialized.get('end') and serialized.get('enddate'):
        serialized['end'] = serialized.get('enddate') if all_day else f"{serialized.get('enddate')}T{serialized.get('endtime') or serialized.get('starttime') or '10:00'}"

    normalized = _normalize_event_payload(serialized, existing=serialized)
    serialized.update(normalized)
    serialized['id'] = event_id
    series_keys = raw_event.get('series_key') if isinstance(raw_event.get('series_key'), list) else []
    series_length = len(series_keys) if series_keys else 1
    is_series = series_length > 1
    serialized['recurring'] = bool(raw_event.get('recurring')) or is_series
    serialized['is_series'] = is_series
    serialized['series_length'] = series_length
    serialized['series_scope_options'] = ['only once', 'this and following', 'entire series'] if is_series else ['only once']
    serialized['series_key'] = series_keys
    return serialized


def _event_bounds(event):
    all_day = _coerce_bool(event.get('allDay'))
    start_dt = _parse_datetime_value(event.get('start'), all_day=all_day)
    end_dt = _parse_datetime_value(event.get('end'), all_day=all_day)
    if start_dt and not end_dt:
        end_dt = start_dt + (dt.timedelta(days=1) if all_day else dt.timedelta(minutes=DEFAULT_EVENT_DURATION_MINUTES))
    if start_dt and end_dt and end_dt <= start_dt:
        end_dt = start_dt + (dt.timedelta(days=1) if all_day else dt.timedelta(minutes=DEFAULT_EVENT_DURATION_MINUTES))
    return start_dt, end_dt or start_dt


def _events_overlap(first_event, second_event):
    first_start, first_end = _event_bounds(first_event)
    second_start, second_end = _event_bounds(second_event)
    if not first_start or not first_end or not second_start or not second_end:
        return False, None, None
    overlap_start = max(first_start, second_start)
    overlap_end = min(first_end, second_end)
    if overlap_start >= overlap_end:
        return False, None, None
    return True, overlap_start, overlap_end


def _conflict_reasons(proposed_event, existing_event):
    reasons = ['Time overlap']
    if proposed_event.get('caseId') and proposed_event.get('caseId') == existing_event.get('caseId'):
        reasons.append('Same case reference')
    if proposed_event.get('clientName') and proposed_event.get('clientName') == existing_event.get('clientName'):
        reasons.append('Same client involved')
    if proposed_event.get('leadCounsel') and proposed_event.get('leadCounsel') == existing_event.get('leadCounsel'):
        reasons.append('Lead counsel double-booked')
    if proposed_event.get('location') and proposed_event.get('location') == existing_event.get('location'):
        reasons.append('Same location reserved')
    return reasons


def _suggest_next_slot(proposed_event, existing_events):
    start_dt, end_dt = _event_bounds(proposed_event)
    if not start_dt or not end_dt:
        return None

    duration = max(end_dt - start_dt, dt.timedelta(minutes=DEFAULT_EVENT_DURATION_MINUTES))
    candidate = max(end_dt, start_dt.replace(minute=0, second=0, microsecond=0))
    if candidate.minute:
        candidate = candidate.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)

    for _ in range(48):
        candidate_end = candidate + duration
        probe = {
            'start': _format_dt(candidate, all_day=_coerce_bool(proposed_event.get('allDay'))),
            'end': _format_dt(candidate_end, all_day=_coerce_bool(proposed_event.get('allDay'))),
            'allDay': proposed_event.get('allDay'),
            'caseId': proposed_event.get('caseId'),
            'clientName': proposed_event.get('clientName'),
            'leadCounsel': proposed_event.get('leadCounsel'),
            'location': proposed_event.get('location'),
        }
        blocked = False
        for event in existing_events:
            overlap, _, _ = _events_overlap(probe, event)
            if overlap:
                blocked = True
                break
        if not blocked:
            return {
                'start': probe['start'],
                'end': probe['end'],
                'label': f"{candidate.strftime('%b %d, %I:%M %p')} - {candidate_end.strftime('%I:%M %p')}",
            }
        candidate += dt.timedelta(hours=1)
    return None


def _available_assignees(proposed_event, conflicts):
    attendees = _coerce_list(proposed_event.get('attendees'))
    if not attendees:
        return []
    blocked = {conflict.get('leadCounsel') for conflict in conflicts if conflict.get('leadCounsel')}
    return [attendee for attendee in attendees if attendee not in blocked]


def _build_conflict_report(proposed_event, existing_events, exclude_event_id=None):
    conflicts = []
    comparable_events = []
    for event in existing_events:
        if exclude_event_id and event.get('id') == exclude_event_id:
            continue
        comparable_events.append(event)
        overlap, overlap_start, overlap_end = _events_overlap(proposed_event, event)
        if not overlap:
            continue
        conflict = dict(event)
        conflict['reasons'] = _conflict_reasons(proposed_event, event)
        conflict['overlap_start'] = _format_dt(overlap_start, all_day=False)
        conflict['overlap_end'] = _format_dt(overlap_end, all_day=False)
        conflict['overlap_minutes'] = int((overlap_end - overlap_start).total_seconds() // 60)
        conflicts.append(conflict)

    next_slot = _suggest_next_slot(proposed_event, comparable_events)
    return {
        'has_conflicts': bool(conflicts),
        'conflicts': conflicts,
        'recommendations': {
            'next_available_slot': next_slot,
            'alternative_assignees': _available_assignees(proposed_event, conflicts),
            'override_allowed': False,
        },
    }


def _load_events_for_user(user_id, start_date=None, end_date=None):
    manager = Eventmanagement(user_id)
    raw = manager.get_all_events_for_user(start_date, end_date)
    meetings_dict = raw.get('meetings', {}) if isinstance(raw, dict) else {}
    return [_serialize_event(event_id, meeting) for event_id, meeting in meetings_dict.items()]


def _update_event_record(user_id, event_id, payload):
    manager = Eventmanagement(user_id)
    collection = manager.get_mongo_client_db()
    document = collection.find_one(
        {'user_id': user_id, f'meetings.{event_id}': {'$exists': True}},
        {f'meetings.{event_id}': 1, '_id': 0},
    )
    if not document:
        return None

    existing_event = document.get('meetings', {}).get(event_id, {})
    normalized = _normalize_event_payload(payload, existing=existing_event)
    normalized['meeting_last_updated_on'] = dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M')

    set_dict = {'last_updated_on': dt.datetime.utcnow()}
    for key, value in normalized.items():
        set_dict[f'meetings.{event_id}.{key}'] = value

    collection.update_one({'user_id': user_id}, {'$set': set_dict})
    updated_event = dict(existing_event)
    updated_event.update(normalized)
    return _serialize_event(event_id, updated_event)


def _load_single_event_for_user(user_id, event_id):
    manager = Eventmanagement(user_id)
    collection = manager.get_mongo_client_db()
    document = collection.find_one(
        {'user_id': user_id, f'meetings.{event_id}': {'$exists': True}},
        {f'meetings.{event_id}': 1, '_id': 0},
    )
    if not document:
        return None
    return document.get('meetings', {}).get(event_id)


def _derive_updated_fields(existing_event, proposed_event):
    updated_fields = []
    existing_start, existing_end = _event_bounds(existing_event)
    proposed_start, proposed_end = _event_bounds(proposed_event)

    field_pairs = [
        ('title', 'title'),
        ('description', 'description'),
        ('allDay', 'allDay'),
        ('event_type', 'eventType'),
        ('meetingtype', 'meetingType'),
        ('caseId', 'caseId'),
        ('clientName', 'clientName'),
        ('location', 'location'),
        ('partyBEmail', 'partyBEmail'),
        ('leadCounsel', 'leadCounsel'),
        ('send_remainder', 'sendReminder'),
        ('internalNotes', 'internalNotes'),
        ('timezone', 'timezone'),
        ('courtName', 'courtName'),
        ('courtNumber', 'courtNumber'),
        ('judgeName', 'judgeName'),
        ('recurring', 'recurring'),
    ]

    for existing_key, output_key in field_pairs:
        if existing_event.get(existing_key) != proposed_event.get(existing_key):
            updated_fields.append(output_key)

    if _coerce_list(existing_event.get('attendees')) != _coerce_list(proposed_event.get('attendees')):
        updated_fields.append('attendeesText')

    if existing_start and proposed_start:
        if existing_start.date() != proposed_start.date():
            updated_fields.append('startDate')
        if existing_start.strftime('%H:%M') != proposed_start.strftime('%H:%M') and not _coerce_bool(proposed_event.get('allDay')):
            updated_fields.append('startTime')

    if existing_end and proposed_end:
        if existing_end.date() != proposed_end.date():
            updated_fields.append('endDate')
        if existing_end.strftime('%H:%M') != proposed_end.strftime('%H:%M') and not _coerce_bool(proposed_event.get('allDay')):
            updated_fields.append('endTime')

    deduped = []
    for item in updated_fields:
        if item not in deduped:
            deduped.append(item)
    return deduped

@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='5/m', block=True)  # Limit to 5 requests per minute per user
def create_event(request):
    """
   {"title":"newwww","start":"2024-09-17T22:01","end":"2024-09-24T00:03","partyBEmail":" ajmrlegaly@gmail.com","meetinglink":"VideoCall","caseId":"121313","Status":"Y","Task_type":"Client Meeting","send_remainder":"Email","email_id":"mems650@gmail.com"}
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = request.data
        logger.info(data)
        email_id = supa_user.get('email')
        fname = supa_user.get('fname')
        lname = supa_user.get('lname')
        data['fname'] = fname
        data['lname'] = lname
        data['email_id'] = email_id

        start_datetime = data.get('start', '')
        end_datetime = data.get('end', '')

        party_b_email = data.get('partyBEmail', '')

        obj = Eventmanagement(user_id)
        create_status = obj.create_new_event(data)

        ##TODO: move sending mail to another file...
        if create_status.get('mssg'):
            logger.info(f" ======= create_status ==== {create_status} ")
            # Format dates for professional display
            formatted_start = format_datetime_for_email(start_datetime)
            formatted_end = format_datetime_for_email(end_datetime)
            obj.notify_event_created(
                email_id,
                fname,
                lname,
                data.get('title', ''),
                formatted_start,
                formatted_end,
                party_b_email,
                create_status.get('meet_link'),
            )
        else:
            raise Exception
        return JsonResponse({"message": "Event created successfully"}, status=201)
    except Exception as err:
        logger.error(f"errrooorr at create event --------> {traceback.format_exc()}")
        return JsonResponse({'status': 'fail', 'message': str(err)}, status=500)

@api_view(['GET'])
@supabase_required
def fetch_event(request):
    try:
        # email_id = request.GET.get('email_id')
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        startdate = request.GET.get('start_date')
        enddate = request.GET.get('end_date')
        obj = Eventmanagement(user_id)

        '''
        # Get the current date to determine the current month and year
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        # Define the start and end dates for the current month
        start_date = f"{current_year}-{current_month:02d}-01"
        # To get the last day of the current month, you can use the calendar module
        
        last_day = calendar.monthrange(current_year, current_month)[1]
        end_date = f"{current_year}-{current_month:02d}-{last_day:02d}"

        start_dt = datetime.strptime(startdate, "%Y-%m-%d")
        end_dt = datetime.strptime(enddate, "%Y-%m-%d")
        '''

        meeting_list = obj.get_all_events_for_user(startdate, enddate)
        return JsonResponse({"events": meeting_list}, status=201)
    except Exception as err:
        logger.error(f"errrooorr at fetch_event event --------> {traceback.format_exc()}")
        return JsonResponse({"events": []}, status=500)


@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='5/m', block=True)
def update_event(request):
    try:
        logger.info(f"""update_event ---> {request.data} """)
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = request.data
        email_id = supa_user.get('email')
        fname = supa_user.get('fname')
        lname = supa_user.get('lname')
        data['fname'] = fname
        data['lname'] = lname
        data['email_id'] = email_id
        # email_id = data.get('email_id')
        obj = Eventmanagement(user_id)
        chk = obj.update_event_for_user(data)
        if chk:
            return JsonResponse({"mssg": "Successfully Updated"}, status=201)
        else:
            return JsonResponse({"mssg": "Meeting Not Found"}, status=401)
    except Exception as err:
        logger.error(f"errrooorr at update_event event --------> {traceback.format_exc()}")
        return JsonResponse({"mssg": f"""Failed to udpate, {err}"""}, status=500)  


@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='5/m', block=True)
def delete_event(request):
    try:
        logger.info(f"""delete_event ---> {request.data} """)
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = request.data.get('data')
        email_id = supa_user.get('email')
        fname = supa_user.get('fname')
        lname = supa_user.get('lname')
        data['fname'] = fname
        data['lname'] = lname
        data['email_id'] = email_id
        obj = Eventmanagement(user_id)
        chk = obj.delete_event_for_user(data)
        if chk:
            return JsonResponse({"mssg": "Successfully deleted"}, status=201)
        else:
            return JsonResponse({"mssg": "Meeting Not Found"}, status=401)
    except Exception as err:
        logger.error(f"errrooorr at delete_event event --------> {traceback.format_exc()}")
        return JsonResponse({"mssg": f"""Failed to delete, {err}"""}, status=500)   

def send_event_reminder(event):
    message = f"""Reminder for event: {event.title} at {event.start_date.strftime('%Y-%m-%d')} from {event.start_time} to {event.end_time}"""

    # Send Email Reminder
    if event.send_reminder in ['Email', 'Both'] and event.party_b_email:
        send_mail(
            'Event Reminder',
            message,
            'from@example.com',  # Replace with your actual email settings
            [event.party_b_email],
            fail_silently=False,
        )

    # Send WhatsApp Reminder using a service like Twilio
    if event.send_reminder in ['WhatsApp', 'Both']:
        send_whatsapp_message(event.phone_number, message)

def send_whatsapp_message(phone_number, message):
    # Example using Twilio API (ensure you replace with actual implementation)
    account_sid = 'your_account_sid'
    auth_token = 'your_auth_token'
    from_whatsapp_number = 'whatsapp:+14155238886'  # Your Twilio number
    to_whatsapp_number = f'whatsapp:+{phone_number}'
    
    requests.post(
        f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json',
        data={
            'From': from_whatsapp_number,
            'To': to_whatsapp_number,
            'Body': message,
        },
        auth=(account_sid, auth_token)
    )


# ── REST-compatible event views ────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@supabase_required
def events_rest(request):
    """
    GET  /api/calendar/events/          → {results: [...], count: N}
    POST /api/calendar/events/          → create event, returns event dict
    """
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')

    if request.method == 'GET':
        try:
            upcoming = request.GET.get('upcoming')
            search = _clean_text(request.GET.get('search'))
            page_size = int(request.GET.get('page_size', 100))
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')

            events = _load_events_for_user(user_id, start_date, end_date)

            # Sort by start ascending
            events.sort(key=lambda e: str(e.get('start', '') or ''))

            if upcoming:
                now_str = dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M')
                events = [e for e in events if str(e.get('start', '')) >= now_str]

            if search:
                needle = search.lower()
                events = [
                    event for event in events
                    if needle in ' '.join([
                        _clean_text(event.get('title')),
                        _clean_text(event.get('caseId')),
                        _clean_text(event.get('clientName')),
                        _clean_text(event.get('courtName')),
                        _clean_text(event.get('description')),
                    ]).lower()
                ]

            events = events[:page_size]
            return JsonResponse({"results": events, "count": len(events)})
        except Exception:
            logger.error(f"events_rest GET error\n{traceback.format_exc()}")
            return JsonResponse({"results": [], "count": 0})

    # POST — create
    try:
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        email_id = supa_user.get('email', '')
        fname = supa_user.get('fname', '')
        lname = supa_user.get('lname', '')
        data['email_id'] = data.get('email_id') or email_id
        data['fname'] = fname
        data['lname'] = lname

        # Map frontend camelCase / renamed fields to legacy expected fields
        if 'taskType' in data and 'Task_type' not in data:
            data['Task_type'] = data.pop('taskType')
        if 'meetingType' in data and 'meetingtype' not in data:
            data['meetingtype'] = data.pop('meetingType')
        if 'allDay' in data:
            data['allDay'] = bool(data['allDay'])
        if not data.get('meetinglink') and data.get('meetingtype') in {'VideoCall', 'VoiceCall'}:
            data['meetinglink'] = _build_virtual_link(data.get('meetingtype'))

        if not data.get('id'):
            data['id'] = str(uuid.uuid4())[:8]

        normalized_payload = _normalize_event_payload(data, existing=data)
        data['Status'] = normalized_payload.get('Status', 'Y')
        data['status'] = normalized_payload.get('status', data['Status'])

        requested_event_id = data['id']

        obj = Eventmanagement(user_id)
        result = obj.create_new_event(data)
        if result.get('mssg'):
            persisted_event_id = _persisted_event_id(requested_event_id, data)
            persisted_event = _load_single_event_for_user(user_id, persisted_event_id)
            if not persisted_event:
                logger.error(f"events_rest POST persistence mismatch for user {user_id} event {persisted_event_id}")
                return JsonResponse({"error": "Event was not saved to the calendar store"}, status=500)
            obj.notify_event_created(
                email_id,
                fname,
                lname,
                data.get('title', ''),
                data.get('start', ''),
                data.get('end', ''),
                data.get('partyBEmail', ''),
                result.get('meet_link') or persisted_event.get('meetinglink', '') or data.get('meetinglink', ''),
            )
            response_event = _serialize_event(persisted_event_id, persisted_event)
            return JsonResponse({"message": "Created", "meet_link": result.get("meet_link"), "event": response_event}, status=201)
        return JsonResponse({"error": "Failed to create event"}, status=500)
    except Exception:
        logger.error(f"events_rest POST error\n{traceback.format_exc()}")
        return JsonResponse({"error": "Server error"}, status=500)


@api_view(['PUT', 'DELETE'])
@supabase_required
def event_detail_rest(request, event_id):
    """
    PUT    /api/calendar/events/<event_id>/   → update event
    DELETE /api/calendar/events/<event_id>/  → delete event
    """
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    email_id = supa_user.get('email', '')
    fname = supa_user.get('fname', '')
    lname = supa_user.get('lname', '')

    if request.method == 'PUT':
        try:
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            if 'meetingType' in data and 'meetingtype' not in data:
                data['meetingtype'] = data.get('meetingType')
            if 'taskType' in data and 'Task_type' not in data:
                data['Task_type'] = data.get('taskType')
            data['email_id'] = data.get('email_id') or email_id
            data['fname'] = fname
            data['lname'] = lname

            existing_event = _load_single_event_for_user(user_id, event_id)
            if not existing_event:
                return JsonResponse({"error": "Event not found"}, status=404)

            merged_event = dict(existing_event)
            merged_event.update(data)
            normalized_existing = _normalize_event_payload(existing_event, existing=existing_event)
            normalized_merged = _normalize_event_payload(merged_event, existing=existing_event)

            updated_fields = data.get('updatedFields') or _derive_updated_fields(normalized_existing, normalized_merged)
            if not updated_fields:
                return JsonResponse({"message": "Updated", "event": _serialize_event(event_id, existing_event)})

            manager = Eventmanagement(user_id)
            service_payload = dict(merged_event)
            service_payload['id'] = event_id
            service_payload['updatedFields'] = updated_fields
            service_payload['recurring'] = _coerce_bool(service_payload.get('recurring'))
            service_payload['occurrence'] = _clean_text(service_payload.get('occurrence')) or existing_event.get('occurrence') or 'only once'
            service_payload['partyBEmail'] = service_payload.get('partyBEmail') or existing_event.get('partyBEmail', '')
            updated = manager.update_event_for_user(service_payload)
            if not updated:
                return JsonResponse({"error": "Unable to update event"}, status=500)

            refreshed_event = _load_single_event_for_user(user_id, event_id)
            if refreshed_event:
                return JsonResponse({"message": "Updated", "event": _serialize_event(event_id, refreshed_event)})
            return JsonResponse({"message": "Updated", "event": {"id": event_id}})
        except Exception:
            logger.error(f"event_detail_rest PUT error\n{traceback.format_exc()}")
            return JsonResponse({"error": "Server error"}, status=500)

    # DELETE
    try:
        existing_event = _load_single_event_for_user(user_id, event_id)
        if not existing_event:
            return JsonResponse({"error": "Event not found"}, status=404)
        request_data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data = {
            'id': event_id,
            'email_id': email_id,
            'fname': fname,
            'lname': lname,
            'title': request_data.get('title') or existing_event.get('title', ''),
            'partyBEmail': request_data.get('partyBEmail') or existing_event.get('partyBEmail', ''),
            'occurrence': request_data.get('occurrence') or existing_event.get('occurrence') or 'only once',
            'recurring': _coerce_bool(request_data.get('recurring')) if 'recurring' in request_data else _coerce_bool(existing_event.get('recurring')),
        }
        obj = Eventmanagement(user_id)
        chk = obj.delete_event_for_user(data)
        if chk:
            return JsonResponse({"message": "Deleted"})
        return JsonResponse({"error": "Event not found"}, status=404)
    except Exception:
        logger.error(f"event_detail_rest DELETE error\n{traceback.format_exc()}")
        return JsonResponse({"error": "Server error"}, status=500)


@api_view(['POST'])
@supabase_required
def conflict_check_rest(request):
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        event_id = _clean_text(data.get('id')) or None
        proposed_event = _normalize_event_payload(data)

        start_dt, end_dt = _event_bounds(proposed_event)
        start_date = (start_dt.date() - dt.timedelta(days=1)).isoformat() if start_dt else None
        end_date = (end_dt.date() + dt.timedelta(days=1)).isoformat() if end_dt else None
        existing_events = _load_events_for_user(user_id, start_date, end_date)
        report = _build_conflict_report(proposed_event, existing_events, exclude_event_id=event_id)
        return JsonResponse({
            'event': proposed_event,
            **report,
        })
    except Exception:
        logger.error(f"conflict_check_rest error\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Unable to check conflicts right now.'}, status=500)


@api_view(['POST'])
@supabase_required
def conflict_resolution_rest(request):
    try:
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        strategy = _clean_text(data.get('strategy')) or 'reschedule'
        event_payload = data.get('event') if isinstance(data.get('event'), dict) else data
        proposed_event = _normalize_event_payload(event_payload)

        report = data.get('report') if isinstance(data.get('report'), dict) else None
        if not report:
            supa_user = request.supabase_user
            user_id = supa_user.get('user_id')
            start_dt, end_dt = _event_bounds(proposed_event)
            start_date = (start_dt.date() - dt.timedelta(days=1)).isoformat() if start_dt else None
            end_date = (end_dt.date() + dt.timedelta(days=1)).isoformat() if end_dt else None
            report = _build_conflict_report(proposed_event, _load_events_for_user(user_id, start_date, end_date), exclude_event_id=_clean_text(proposed_event.get('id')) or None)

        summary_lines = []
        if strategy == 'reschedule':
            slot = data.get('slot') if isinstance(data.get('slot'), dict) else report.get('recommendations', {}).get('next_available_slot')
            if not slot:
                return JsonResponse({'error': 'No alternate slot available.'}, status=400)
            proposed_event['start'] = slot.get('start', proposed_event.get('start'))
            proposed_event['end'] = slot.get('end', proposed_event.get('end'))
            proposed_event['conflict_status'] = 'resolved'
            summary_lines.append(f"Event rescheduled to {slot.get('label', slot.get('start', 'the next available slot'))}.")
        elif strategy == 'reassign':
            assignee = _clean_text(data.get('assignee'))
            if not assignee:
                alternatives = report.get('recommendations', {}).get('alternative_assignees') or []
                assignee = alternatives[0] if alternatives else ''
            if not assignee:
                return JsonResponse({'error': 'No alternate assignee available.'}, status=400)
            proposed_event['leadCounsel'] = assignee
            proposed_event['assigned_counsel'] = assignee
            proposed_event['conflict_status'] = 'resolved'
            summary_lines.append(f"Lead counsel reassigned to {assignee}.")
        elif strategy == 'override':
            proposed_event['conflict_status'] = 'override_requested'
            summary_lines.append('Override requested for manual approval.')
        else:
            return JsonResponse({'error': 'Unsupported resolution strategy.'}, status=400)

        proposed_event['resolution_summary'] = ' '.join(summary_lines)
        return JsonResponse({
            'message': 'Resolution prepared',
            'event': proposed_event,
            'summary': summary_lines,
            'status': proposed_event.get('conflict_status'),
        })
    except Exception:
        logger.error(f"conflict_resolution_rest error\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Unable to prepare the conflict resolution.'}, status=500)
