# reminders/tasks.py

from celery import shared_task
from datetime import datetime, timedelta
import pytz
import os
from utilities.routes.utils import Handutilities  # Replace with your notification function
from opensearchpy import OpenSearch, helpers
from core.init_clients import get_mongo_client, get_mongo_db
import requests
import traceback
import logging
logger = logging.getLogger('django')

def get_mongo_client_db(required_collection):
    mongo = get_mongo_client()
    if not mongo:
        return ''
    db = get_mongo_db()

    if required_collection == "user_details":    
        return db['user_details']
    
    elif required_collection == "state_district_court_data":
        state_district_court_collection = db["state_district_court_data"]
        existing_indexes = state_district_court_collection.index_information()
        if "state_name" not in existing_indexes:
            state_district_court_collection.create_index([("state_name", 1)])
        if "district_name" not in existing_indexes:
            state_district_court_collection.create_index([("district_name", 1)])
        if "court_name" not in existing_indexes:
            state_district_court_collection.create_index([("court_name", 1)])

        return state_district_court_collection

@shared_task
def update_state_district_court_data():
    try:
        get_mongo_client_db(required_collection="state_district_court_data").delete_many({})

        # 1. GET ALL STATES
        states_url = "https://phoenix.akshit.me/district-court/states"
        states_response = requests.post(states_url)
        if states_response.status_code != 200:
            logger.error("Unable to fetch states.")
            return
        
        # The JSON response has a top-level "states" key
        response_json = states_response.json()
        states_data = response_json.get("states", [])  # list of dict
    
        logger.info(f"IN UTILITIESS state_district_courtlist -----------> {states_data}")
        # 2. PARALLEL FETCH DISTRICTS FOR EACH STATE
        districts_url = "https://phoenix.akshit.me/district-court/districts"
    
        courts_url = "https://phoenix.akshit.me/district-court/courts"

        state_platform_assigned_id_value = 0
        for state_obj in states_data:
            # Get districts serially
            state_platform_assigned_id_value+=1
            state_platform_assigned_id = f"S{state_platform_assigned_id_value}"

            payload = {"stateId": state_obj["id"]}
            dist_resp = requests.post(districts_url, json=payload)
            if dist_resp.status_code == 200:
                dist_data = dist_resp.json().get("districts", [])

                district_platform_assigned_id_value = 0
                for district_obj in dist_data:
                    # Get courts serially
                    district_platform_assigned_id_value+=1
                    district_platform_assigned_id = f"D{district_platform_assigned_id_value}"

                    payload = {"districtId": district_obj["id"]}
                    court_resp = requests.post(courts_url, json=payload)
                    if court_resp.status_code == 200:
                        courts_data = court_resp.json().get("courts", [])
                        # Insert into DB

                        court_platform_assigned_id_value = 0
                        for court_obj in courts_data:
                            logger.info(f"IN UTILITIESS state_obj, districts_data, courts_data -----------> {state_obj}, {district_obj}, {court_obj}")

                            court_platform_assigned_id_value+=1
                            court_platform_assigned_id = f"C{court_platform_assigned_id_value}"
                            doc = {
                                "state_id": state_obj["id"],
                                "state_name": state_obj["name"],
                                "state_platform_assigned_id": state_platform_assigned_id,
                                "district_id": district_obj["id"],
                                "district_name": district_obj["name"],
                                "district_platform_assigned_id": district_platform_assigned_id,
                                "court_id": court_obj["id"],
                                "court_name": court_obj["name"],
                                "court_platform_assigned_id": court_platform_assigned_id
                            }
                            get_mongo_client_db(required_collection="state_district_court_data").insert_one(doc)
    except Exception as err:
        logger.error(f"error at update stateditrictcourt ---> {err}")


# @shared_task
# def send_whatsapp_message_celery(payload):
#     request_to_whatsapp_url(payload)

# def request_to_whatsapp_url(payload):
#     ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
#     PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
#     WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
#     try:
#         headers = {
#             "Authorization": f"Bearer {ACCESS_TOKEN}",
#             "Content-Type": "application/json"
#         }
#         # logging.info(f"send_whatsapp_message -------->>>> {headers} == payload == {payload}")
#         response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
#         logging.info(f"WhatsApp API response in UTILS: {response.status_code}, {response.text}")
#         return response
#     except Exception as err:
#         logger.error(traceback.format_exc())
#         logger.error(f"EERROR SHAREDD TASKKKK AT request_whatsapp_url in UTILS USEEERRSSSS ---->  {err}")


@shared_task
def fetch_todays_meetings():
    try:
        # Get today's date
        tz = pytz.timezone('UTC')  # Change to your timezone
        today = datetime.now(tz).date()
        
        # Define start and end of day
        start_of_day = datetime.combine(today, datetime.min.time()).replace(tzinfo=tz)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Fetch meetings for today
        pipeline = [
            {
                "$project": {
                    "user_id": 1,
                    "fname": 1,
                    "lname": 1,
                    "email": 1,
                    "phone_number": 1,
                    "user_type": 1,
                    "case_ids": 1,
                    "meetings": {
                        "$objectToArray": "$meetings"
                    }
                }
            },
            {
                "$unwind": "$meetings"
            },
            {
                "$replaceRoot": {
                    "newRoot": {
                        "$mergeObjects": ["$$ROOT", "$meetings.v"]
                    }
                }
            },
            {
                "$addFields": {
                    "meeting_start_date": {
                        "$cond": {
                            "if": { "$ifNull": ["$startdate", False] },
                            "then": {
                                "$toDate": {
                                    "$concat": [
                                        "$startdate",
                                        "T",
                                        { "$ifNull": ["$starttime", "00:00"] }
                                    ]
                                }
                            },
                            "else": { "$toDate": "$start" }
                        }
                    },
                    "meeting_end_date": {
                        "$cond": {
                            "if": { "$ifNull": ["$enddate", False] },
                            "then": {
                                "$toDate": {
                                    "$concat": [
                                        "$enddate",
                                        "T",
                                        { "$ifNull": ["$endtime", "23:59"] }
                                    ]
                                }
                            },
                            "else": { "$toDate": "$end" }
                        }
                    }
                }
            },
            {
                "$match": {
                    "meeting_start_date": {
                        "$gte": start_of_day,
                        "$lt": end_of_day
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "user_id": 1,
                    "fname": 1,
                    "lname": 1,
                    "email": 1,
                    "phone_number": 1,
                    "user_type": 1,
                    "case_ids": 1,
                    "meeting_id": "$meetings.k",
                    "title": 1,
                    "eventType": 1,
                    "partyBEmail": 1,
                    "meetingtype": 1,
                    "caseId": 1,
                    "Status": 1,
                    "courtName": 1,
                    "courtNumber": 1,
                    "clientName": 1,
                    "judgeName": 1,
                    "taskType": 1,
                    "sendReminder": 1,
                    "email_id": 1,
                    "allDay": 1,
                    "occurrence": 1,
                    "recurring": 1,
                    "startdate": 1,
                    "starttime": 1,
                    "enddate": 1,
                    "endtime": 1,
                    "start": 1,
                    "end": 1
                }
            }
        ]
        logger.warning(f"pipeline ------ fetch_todays_meetings ======> {pipeline}")
        meetings_today = list(get_mongo_client_db(required_collection="user_details").aggregate(pipeline))
        
        # Connect to OpenSearch
        opensearch = OpenSearch(
            hosts=[{'host': 'localhost', 'port': 9200}],
            http_auth=('admin', 'admin'),  # Update with your credentials
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )
        
        # Index name for today
        index_name = os.getenv("OPENSEARCH_INDEX_PREFIX", "") + f"meetings_{today.strftime('%Y%m%d')}"
        
        # Delete index if exists
        if opensearch.indices.exists(index=index_name):
            opensearch.indices.delete(index=index_name)
        
        # Create index
        opensearch.indices.create(index=index_name, ignore=400)
        
        # Bulk index meetings
        # from elasticsearch.helpers import bulk
        
        actions = [
            {
                "_index": index_name,
                "_source": meeting
            }
            for meeting in meetings_today
        ]
        
        helpers.bulk(opensearch, actions)
        
        # Send notifications
        for meeting in meetings_today:
            user_details = {
                "user_id": meeting.get("user_id"),
                "fname": meeting.get("fname"),
                "lname": meeting.get("lname"),
                "email": meeting.get("email"),
                "phone_number": meeting.get("phone_number"),
                "partyBemail":meeting.get("partyBEmail"),
                # Add other necessary fields
            }
            meeting_details = meeting  # All meeting details
            
            obj = Handutilities()
            logging.info(f" ----- fetch_todays_meetings --- meeting_details ---> {meeting_details}")
            obj.send_notification(user_details, meeting_details, reminder_type="hourly")

        return f"Indexed {len(meetings_today)} meetings to {index_name}"
    except Exception as err:
        logging.error(f" ----- fetch_todays_meetings --- error ---> {err}")
        logger.info(traceback.format_exc())

@shared_task
def send_hourly_reminders():
    try:
        # Connect to OpenSearch
        opensearch = OpenSearch(
            hosts=[{'host': 'localhost', 'port': 9200}],
            http_compress=True,  # enables gzip compression for request bodies
            use_ssl=False,
            verify_certs=False,
        )
        
        # Get today's date
        tz = pytz.timezone('UTC')  # Change to your timezone
        today = datetime.now(tz).date()
        index_name = os.getenv("OPENSEARCH_INDEX_PREFIX", "") + f"meetings_{today.strftime('%Y%m%d')}"
        
        # Define time window: next hour
        now = datetime.now(tz)
        one_hour_later = now + timedelta(hours=1)
        
        # Query for meetings starting within the next hour
        query = {
            "bool": {
                "must": [
                    {
                        "range": {
                            "meeting_start_date": {
                                "gte": now.isoformat(),
                                "lt": one_hour_later.isoformat()
                            }
                        }
                    }
                ]
            }
        }
        
        try:
            response = opensearch.search(
                index=index_name,
                body={
                    "query": query
                },
                size=10000  # Adjust based on expected volume
            )
        except Exception as err:
            return f"No HOURLY Remainder. Probably no meetings found. Error  ---> {err}"
        
        meetings = [hit['_source'] for hit in response['hits']['hits']]
        
        # Send notifications
        for meeting in meetings:
            user_details = {
                "user_id": meeting.get("user_id"),
                "fname": meeting.get("fname"),
                "lname": meeting.get("lname"),
                "email": meeting.get("email"),
                "phone_number": meeting.get("phone_number"),
                "partyBemail":meeting.get("partyBEmail"),
                # Add other necessary fields
            }
            meeting_details = meeting  # All meeting details
            
            obj = Handutilities()
            obj.send_notification(user_details, meeting_details, reminder_type="hourly")
        
        return f"Sent {len(meetings)} hourly reminders"

    except Exception as err:
        logging.error(f" ----- send_hourly_reminders --- error ---> {err}")
        logger.info(traceback.format_exc())

@shared_task
def send_quarterly_reminders():
    try:
        # Connect to OpenSearch
        opensearch = OpenSearch(
            hosts=[{'host': 'localhost', 'port': 9200}],
            http_compress=True,  # enables gzip compression for request bodies
            use_ssl=False,
            verify_certs=False,
        )
        
        # Get today's date
        tz = pytz.timezone('UTC')  # Change to your timezone
        today = datetime.now(tz).date()
        index_name = os.getenv("OPENSEARCH_INDEX_PREFIX", "") + f"meetings_{today.strftime('%Y%m%d')}"
        
        # Define time window: next 15 minutes
        now = datetime.now(tz)
        fifteen_mins_later = now + timedelta(minutes=15)
        
        # Query for meetings starting within the next 15 minutes
        query = {
            "bool": {
                "must": [
                    {
                        "range": {
                            "meeting_start_date": {
                                "gte": now.isoformat(),
                                "lt": fifteen_mins_later.isoformat()
                            }
                        }
                    }
                ]
            }
        }
        
        try:
            response = opensearch.search(
                index=index_name,
                body={
                    "query": query
                },
                size=10000  # Adjust based on expected volume
            )
        except Exception as err:
            return f"No Quaterly Remainder. Probably no meetings found. Error  ---> {err}"
        
        meetings = [hit['_source'] for hit in response['hits']['hits']]
        
        # Send notifications
        for meeting in meetings:
            user_details = {
                "user_id": meeting.get("user_id"),
                "fname": meeting.get("fname"),
                "lname": meeting.get("lname"),
                "email": meeting.get("email"),
                "phone_number": meeting.get("phone_number"),
                "partyBemail":meeting.get("partyBEmail"),
                # Add other necessary fields
            }
            meeting_details = meeting  # All meeting details
            
            obj = Handutilities()
            obj.send_notification(user_details, meeting_details, reminder_type="quarterly")
        
        return f"Sent {len(meetings)} 15-minute reminders"
    except Exception as err:
        logging.error(f" ----- send_quarterly_reminders --- error ---> {err}")
        logger.info(traceback.format_exc())


@shared_task
def cleanup_previous_day_index():
    try:
        tz = pytz.timezone('UTC')  # Change to your timezone
        yesterday = datetime.now(tz).date() - timedelta(days=1)
        index_name = os.getenv("OPENSEARCH_INDEX_PREFIX", "") + f"meetings_{yesterday.strftime('%Y%m%d')}"
        
        opensearch = OpenSearch(
            hosts=[{'host': 'localhost', 'port': 9200}],
            http_compress=True,  # enables gzip compression for request bodies
            use_ssl=False,
            verify_certs=False,
        )
        
        if opensearch.indices.exists(index=index_name):
            opensearch.indices.delete(index=index_name)
        
        return f"Deleted index {index_name}"
    except Exception as err:
        logging.error(f" ----- cleanup_previous_day_index --- error ---> {err}")
        logger.info(traceback.format_exc())


@shared_task
def send_daily_consolidated_reminders():
    try:
        # Get today's date
        tz = pytz.timezone('UTC')  # Change to your timezone
        today = datetime.now(tz).date()
        
        # Define start and end of day
        start_of_day = datetime.combine(today, datetime.min.time()).replace(tzinfo=tz)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Fetch meetings updated today
        pipeline = [
            {
                "$project": {
                    "user_id": 1,
                    "fname": 1,
                    "lname": 1,
                    "email": 1,
                    "phone_number": 1,
                    "user_type": 1,
                    "case_ids": 1,
                    "meetings": {
                        "$objectToArray": "$meetings"
                    }
                }
            },
            {
                "$unwind": "$meetings"
            },
            {
                "$replaceRoot": {
                    "newRoot": {
                        "$mergeObjects": ["$$ROOT", "$meetings.v"]
                    }
                }
            },
            {
                "$addFields": {
                    "meeting_start_date": {
                        "$cond": {
                            "if": { "$ifNull": ["$startdate", False] },
                            "then": {
                                "$toDate": {
                                    "$concat": [
                                        "$startdate",
                                        "T",
                                        { "$ifNull": ["$starttime", "00:00"] }
                                    ]
                                }
                            },
                            "else": { "$toDate": "$start" }
                        }
                    },
                    "meeting_end_date": {
                        "$cond": {
                            "if": { "$ifNull": ["$enddate", False] },
                            "then": {
                                "$toDate": {
                                    "$concat": [
                                        "$enddate",
                                        "T",
                                        { "$ifNull": ["$endtime", "23:59"] }
                                    ]
                                }
                            },
                            "else": { "$toDate": "$end" }
                        }
                    }
                }
            },
            {
                "$match": {
                    "meeting_last_updated_on": {
                        "$gte": start_of_day.strftime('%Y-%m-%dT%H:%M'),
                        "$lt": end_of_day.strftime('%Y-%m-%dT%H:%M')
                    }
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "fname": { "$first": "$fname" },
                    "lname": { "$first": "$lname" },
                    "email": { "$first": "$email" },
                    "phone_number": { "$first": "$phone_number" },
                    "meetings": {
                        "$push": {
                            "meeting_id": "$meeting_id",
                            "title": "$title",
                            "eventType": "$eventType",
                            "meeting_start_date": "$meeting_start_date",
                            "meeting_end_date": "$meeting_end_date",
                            "partyBemail":"$partyBEmail",
                            # Add other fields as needed
                        }
                    }
                }
            }
        ]
        logger.warning(f"pipeline ------ send_daily_consolidated_reminders ======> {pipeline}")
        try:
            updated_meetings = list(get_mongo_client_db(required_collection="user_details").aggregate(pipeline))
        except Exception as e:
            return {"error": str(e)}
        
        # Send consolidated notifications
        for user in updated_meetings:
            user_details = {
                "user_id": user.get("user_id"),
                "fname": user.get("fname"),
                "lname": user.get("lname"),
                "email": user.get("email"),
                "phone_number": user.get("phone_number"),
                "partyBEmail": user.get("partyBEmail"),
                # Add other necessary fields
            }
            meetings_consolidated = user.get("meetings", [])
            
            # Prepare a consolidated message
            consolidated_details = "\n".join([
                f"Title: {meeting['title']}, Type: {meeting['eventType']}, Start: {meeting['meeting_start_date'].strftime('%Y-%m-%d %H:%M')}, End: {meeting['meeting_end_date'].strftime('%Y-%m-%d %H:%M')}"
                for meeting in meetings_consolidated
            ])
            
            # Send notification
            obj = Handutilities()
            obj.send_notification(
                user_details,
                {
                    "consolidated_meetings": consolidated_details
                },
                reminder_type="daily_consolidated"
            )
        
        return f"Sent consolidated reminders to {len(updated_meetings)} users"
    except Exception as err:
        logging.error(f" ----- send_daily_consolidated_reminders --- error ---> {err}")
        logger.info(traceback.format_exc())