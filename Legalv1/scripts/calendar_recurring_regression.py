import os
import sys
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Legalv1.settings')

import django

django.setup()

from calendar_management.routes.createupdateevents import Eventmanagement
from calendar_management.views import _serialize_event
from core.init_clients import get_mongo_client


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    mongo = get_mongo_client()
    collection = mongo['legaldb']['user_details']
    user_id = f'regression-calendar-{uuid.uuid4().hex[:10]}'
    email = f'{user_id}@example.com'

    collection.insert_one({
        'user_id': user_id,
        'email': email,
        'meetings': {},
    })

    manager = Eventmanagement(user_id)
    manager._send_email = lambda *args, **kwargs: True

    try:
        create_payload = {
            'id': 'regressionchain',
            'title': 'Regression Chain',
            'description': 'Validate linked daily events',
            'start': '2026-03-01T09:00',
            'end': '2026-03-04T10:00',
            'allDay': False,
            'eventType': 'Client Consultation',
            'event_type': 'Client Consultation',
            'Task_type': 'Client Consultation',
            'taskType': 'Client Consultation',
            'meetingtype': 'InPerson',
            'meetingType': 'InPerson',
            'caseId': 'REG-101',
            'clientName': 'Regression Client',
            'location': 'Conference Room',
            'partyBEmail': '',
            'leadCounsel': 'Test Counsel',
            'assigned_counsel': 'Test Counsel',
            'attendees': [],
            'sendReminder': 'Email',
            'send_remainder': 'Email',
            'recurring': True,
            'occurrence': 'only once',
            'internalNotes': '',
            'timezone': 'Asia/Kolkata',
            'conflict_status': 'clear',
            'resolution_summary': '',
            'courtName': '',
            'courtNumber': '',
            'judgeName': '',
            'email_id': email,
            'fname': 'Regression',
            'lname': 'Tester',
            'Status': 'Y',
        }

        create_result = manager.create_new_event(dict(create_payload))
        assert_true(create_result.get('mssg') is True, 'Create event failed')

        meetings = manager.get_all_events_for_user('2026-03-01', '2026-03-05').get('meetings', {})
        assert_true(len(meetings) == 4, f'Expected 4 linked events, found {len(meetings)}')

        serialized = _serialize_event('regressionchain_20260301', meetings['regressionchain_20260301'])
        assert_true(serialized.get('is_series') is True, 'Serialized event should expose is_series=true')
        assert_true(serialized.get('series_length') == 4, f"Expected series_length=4, got {serialized.get('series_length')}")
        assert_true(serialized.get('series_scope_options') == ['only once', 'this and following', 'entire series'], 'Serialized scope options mismatch')

        update_result = manager.update_event_for_user({
            'id': 'regressionchain_20260303',
            'title': 'Regression Chain',
            'start': '2026-03-03T11:00',
            'end': '2026-03-03T12:00',
            'updatedFields': ['startTime', 'endTime'],
            'recurring': True,
            'occurrence': 'this and following',
            'partyBEmail': '',
            'email_id': email,
            'fname': 'Regression',
            'lname': 'Tester',
        })
        assert_true(update_result is True, 'this and following update failed')

        post_update = collection.find_one({'user_id': user_id}, {'meetings': 1, '_id': 0}).get('meetings', {})
        first_half = post_update['regressionchain_20260301']
        second_day = post_update['regressionchain_20260302']
        third_day = post_update['regressionchain_20260303']
        fourth_day = post_update['regressionchain_20260304']

        assert_true(first_half.get('series_key') == ['regressionchain_20260301', 'regressionchain_20260302'], 'Earlier series segment should keep first two keys only')
        assert_true(second_day.get('series_key') == ['regressionchain_20260301', 'regressionchain_20260302'], 'Second event should remain in first segment')
        assert_true(third_day.get('series_key') == ['regressionchain_20260303', 'regressionchain_20260304'], 'Updated segment should start at selected key')
        assert_true(fourth_day.get('series_key') == ['regressionchain_20260303', 'regressionchain_20260304'], 'Following event should remain in updated segment')
        assert_true(third_day.get('starttime') == '11:00' and fourth_day.get('starttime') == '11:00', 'Updated segment should receive the new time')
        assert_true(first_half.get('starttime') == '09:00' and second_day.get('starttime') == '09:00', 'Earlier segment should keep original time')

        delete_result = manager.delete_event_for_user({
            'id': 'regressionchain_20260302',
            'title': 'Regression Chain',
            'recurring': True,
            'occurrence': 'only once',
            'partyBEmail': '',
            'email_id': email,
            'fname': 'Regression',
            'lname': 'Tester',
        })
        assert_true(delete_result is True, 'Single occurrence delete failed')

        post_delete = collection.find_one({'user_id': user_id}, {'meetings': 1, '_id': 0}).get('meetings', {})
        assert_true(post_delete['regressionchain_20260302'].get('Status') == 'D', 'Deleted occurrence should be marked D')
        assert_true(post_delete['regressionchain_20260301'].get('series_key') == ['regressionchain_20260301'], 'Remaining earlier event should drop deleted key from series')
        assert_true(post_delete['regressionchain_20260303'].get('Status') == 'Y', 'Future segment should remain active after single delete')

        print('calendar recurring regression: PASS')
    finally:
        collection.delete_one({'user_id': user_id})


if __name__ == '__main__':
    main()