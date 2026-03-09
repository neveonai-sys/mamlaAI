from celery import shared_task
import requests
import traceback
from io import BytesIO
import base64
import logging
import datetime
from django.conf import settings
from core.init_clients import get_mongo_client
import pymongo

logger = logging.getLogger('django')

def get_mongo_client_db():
    mongo = get_mongo_client()
    if not mongo:
        return ''
    db = mongo['legaldb']
    return db

@shared_task
def send_email_celery( to_email, subj, body, cc_emails=None, file_name=None, attach_files=None):
    try:
        if cc_emails:
            payload = {
            "to_emails": to_email,
            "subject": subj,
            "body": body,
            "cc_emails": cc_emails
            }
        else:
            payload = {
            "to_emails": to_email,
            "subject": subj,
            "body": body
            }
            
        logger.info(f" in shared taskkkssss --- {payload}")
        url = f"{settings.FRONTEND_URL}/api/utils/send-email/"
        files = {}
        if attach_files:
            file_data = base64.b64decode(attach_files)
            file_buffer = BytesIO(file_data)
            files={
                    ('attachments',(file_name.split('.')[0]+'.pdf',file_buffer,'application/pdf'))
                    }
        response = requests.request("POST", url, data=payload, files=files)
        logger.info(response.text)
    except Exception as err:
        logger.error(traceback.format_exc())
        logger.error(f"EERROR SHAREDD TASKKKK AT send_email calender_management ---->  {err}")

@shared_task
def execute_query(data_dict, qry_type):
    try:
        logger.info(f"execute_query calender_management {qry_type} --> data_dict = {data_dict} ")
        if qry_type == 'delete':
            partyBEmail = data_dict.get('partyBEmail')
            unset_dict = data_dict.get('unset_dict')
            
            if data_dict.get('once_flag'):
                
                bulk_operations = []
                for skey in data_dict.get('series_keys'):
                    if skey != data_dict.get('key'):
                        bulk_operations.append(pymongo.UpdateOne(
                            {"user_id": partyBEmail, f"meetings.{skey}.series_key": data_dict.get('key')},
                            {"$pull": {f"meetings.{skey}.series_key": data_dict.get('key')}}
                        ))

                if bulk_operations:
                    logger.info(f"Preparing to remove '{data_dict.get('key')}' from series_key arrays of other meetings.")
                
                    # Execute bulk write
                    result = get_mongo_client_db()['user_details'].bulk_write(bulk_operations)
                    logger.info(f"Modified count: {result.modified_count}")
                    
            get_mongo_client_db()['user_details'].update_one(
                    {"email": partyBEmail},
                    {"$set": unset_dict}
                )
        elif qry_type == 'update':
            partyBEmail = data_dict.get('partyBEmail')
            set_dict = data_dict.get('set_dict')
            # input_data = data_dict.get('input_data')
            
            get_mongo_client_db()['user_details'].update_one(
                {
                    "email": partyBEmail,
                },
                {
                    "$set":set_dict
                },
                upsert=False
            )
        elif qry_type == 'create':
            partyBEmail = data_dict.get('partyBEmail')
            recur = data_dict.get('recur')
            if recur:
                new_meeting = data_dict.get('new_meeting')
                get_mongo_client_db()['user_details'].update_one(
                            {"email": partyBEmail},  # Select the user by email
                            {"$set": new_meeting}  # Use meeting_id as the custom key
                        )
            else:
                key = data_dict.get('key')
                data = data_dict.get('data')
                get_mongo_client_db()['user_details'].update_one(
                        {"email": partyBEmail},  # Select the user by email
                        {"$set": {f"meetings.{key}": data}}  # Use meeting_id as the custom key
                    )
    except Exception as err:
        logger.error(traceback.format_exc())
        logger.error(f"EERROR SHAREDD TASKKKK AT execute_query calender_management ---->  {err}")
    
