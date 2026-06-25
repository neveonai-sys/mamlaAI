from celery import shared_task
import requests
import traceback
from io import BytesIO
import base64
import datetime
from .routes.session_manager import SessionManager
import os
from django.conf import settings
from core.init_clients import get_mongo_client, get_mongo_db, get_supabase_client
# from whatsapp_module.routes.handlewhatsappmessage import Whatsappmessageformulation
import logging
logger = logging.getLogger(__name__)


def get_mongo_client_db():
    mongo = get_mongo_client()
    if not mongo:
        return ''
    db = get_mongo_db()
    return db

@shared_task
def insert_new_user_details(user_data):
    try:
        user_collection = get_mongo_client_db()['user_details']
        user_collection.insert_one(user_data)
    except Exception as e:
        logger.error(f"Error inserting new user details: {str(e)}")

@shared_task
def create_userdetails_in_supabase_public_table(user_details_for_metadata):
    supabase = get_supabase_client()
    response = (
        supabase.table("user_metadata")
        .insert({"user_id": user_details_for_metadata.get('user_id'), "first_name": user_details_for_metadata.get('fname'), "last_name": user_details_for_metadata.get('lname'), "phone": user_details_for_metadata.get('phone'), "email": user_details_for_metadata.get('email'), "user_type": user_details_for_metadata.get('user_type')})
        .execute()
    )

    logger.info(f"create_userdetails_in_supabase_public_table ---> response: {response}")

@shared_task
def insert_new_user_details(user_details):
        try:           
            data = {
                    "supabase_id": user_details.get('supabase_userid'),
                    "user_type": user_details.get('user_type'),
                    "whatsappOptIn": user_details.get('whatsappOptIn'),
                    "agreedTnC": user_details.get('agreedTnC'),
                    "onboarding_time": user_details.get('supabase_created_at'),
                    "last_updated_on":user_details.get('supabase_created_at'),
                    "user_status": user_details.get('user_status'),
                    "meetings":{},
                    }
            
            if user_details.get('user_type')=='Lawyer':
                data["barcode_id"] = user_details.get('barcode_id')
                data["case_ids"] = user_details.get('case_ids')
                data["ai_draft_count"] = 0
                data["template_draft_count"] = 0
            elif user_details.get('user_type')=='Client':
                data["case_ids"] = user_details.get('case_ids')
            elif user_details.get('user_type')=='Paralegal':
                data["state"] = user_details.get('state')
                data["district"] = user_details.get('district')
                data["courts"] = user_details.get('courts')
                data["template_draft_count"] = 0
            elif user_details.get('user_type')=='Law Student':
                data["college_name"] = user_details.get('college_name', '')
                data["ai_draft_count"] = 0
                data["template_draft_count"] = 0
            
            # Upsert in local DB
            get_mongo_client_db()['user_details'].update_one(
                {"user_id": user_details.get('user_id')},
                {
                    "$setOnInsert": {"user_id": user_details.get('user_id')},
                    "$set": data,
                },
                upsert=True
            )
            try:
                send_whatsapp_message(user_details.get('phone_number'))
            except:
                logger.error("unable to send whatsapp message")

        except Exception as err:
            logger.error(traceback.format_exc())

@shared_task
def update_onboarded_user_details(user_details):
    try:
        data = {
                "supabase_id": user_details.get('supabase_userid'),
                "whatsappOptIn": user_details.get('whatsappOptIn'),
                "agreedTnC": user_details.get('agreedTnC'),
                "last_updated_on":user_details.get('supabase_created_at'),
                "user_status": user_details.get('user_status'),
                }
            
        get_mongo_client_db()['user_details'].update_one(
                {"user_id": user_details.get('user_id')},
                {
                    "$set": data,
                }
            )
        try:
            send_whatsapp_message(user_details.get('phone_number'))
        except:
            logger.error("unable to send whatsapp message")
    except Exception as err:
        logger.error(traceback.format_exc())


def send_whatsapp_message(phone_number):
    """
    Send a WhatsApp message. Return True if delivered, False if not.
    For demonstration, assume it's always successful.
    """
    try:
        payload = {
                "messaging_product": "whatsapp",
                "to": f'91{phone_number}',
                "type": "template",
                "template": {
                    "name": "onboard_user_template",
                    "language": {
                        "code": "en"
                    }
                }
            }

        logger.info(f"[DEBUG] Sending WhatsApp message PAYLOAD --> {payload}'")
        chk = request_to_whatsapp_url(payload)
        logger.info(f"[DEBUG] Sending WhatsApp message chk --> {chk}'")
    except Exception as err:
        logger.error(traceback.format_exc())

@shared_task
def send_email_celery( to_email, subj, body, file_name=None, attach_files=None):
    try:
        payload = {
        "to_emails": to_email,
        "subject": subj,
        "body": body
        }
        
        logger.info(" in shared taskkkssss USERSSS---")
        url = f"{settings.FRONTEND_URL}/api/utils/send-email/"
        files={}
        # headers = {}
        if attach_files:
            file_data = base64.b64decode(attach_files)
            file_buffer = BytesIO(file_data)
            files={
                    ('attachments',(file_name.split('.')[0]+'.pdf',file_buffer,'application/pdf'))
                    }
            # headers = {}
        response = requests.request("POST", url, data=payload, files=files)
        # file_buffer.close()
        logger.info(response.text)
    #     return True
    except Exception as err:
        logger.error(traceback.format_exc())
        logger.error(f"EERROR SHAREDD TASKKKK AT send_email USEEERRSSSS ---->  {err}")
    #     return False

##TODO: to implement sms functionality
@shared_task
def send_sms_celery(phonenumber, sms_body):
    try:
        pass
    except Exception as err:
        logger.error(traceback.format_exc())
        logger.error(f"EERROR SHAREDD TASKKKK AT send_sms_celery USEEERRSSSS ---->  {err}")

@shared_task
def send_whatsapp_message_celery(payload):
    request_to_whatsapp_url(payload)

def request_to_whatsapp_url(payload):
    ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
    PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
    WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    try:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        # logging.info(f"send_whatsapp_message -------->>>> {headers} == payload == {payload}")
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
        logging.info(f"WhatsApp API response: {response.status_code}, {response.text}")
        return response
    except Exception as err:
        logger.error(traceback.format_exc())
        logger.error(f"EERROR SHAREDD TASKKKK AT request_whatsapp_url USEEERRSSSS ---->  {err}")

@shared_task
def cleanup_inactive_sessions():
    session_manager = SessionManager()
    inactivity_threshold = 15  # minutes
    try:
        session_manager.remove_inactive_sessions(inactivity_threshold)
    except Exception as e:
        logger.error(f"Error during cleanup of inactive sessions: {str(e)}")

@shared_task
def invalidate_inactive_sessions():
    try:
        # session_manager = SessionManager()
        threshold_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        result = get_mongo_client_db()['sessions'].delete_many({'last_activity': {'$lt': threshold_time}})
        logger.info(f"Invalidated {result.deleted_count} inactive sessions.")
    except Exception as e:
        logger.error(f"Error invalidating inactive sessions: {traceback.format_exc()}")

@shared_task
def invalidate_all_sessions_weekly():
    try:
        # session_manager = SessionManager()
        result = get_mongo_client_db()['sessions'].delete_many({})
        logger.info(f"Weekly invalidation: {result.deleted_count} sessions invalidated.")
    except Exception as e:
        logger.error(f"Error invalidating all sessions weekly: {traceback.format_exc()}")

@shared_task
def invalidate_sessions_weekly_for_specific_users(user_ids):
    """ not using just plcaeholder if we want to invalidate specific users"""
    try:
        # session_manager = SessionManager()
        result = get_mongo_client_db()['sessions'].delete_many({'user_id': {'$in': user_ids}})
        logger.info(f"Weekly invalidation: {result.deleted_count} sessions invalidated for specified users.")
    except Exception as e:
        logger.error(f"Error invalidating sessions weekly for specific users: {traceback.format_exc()}")
