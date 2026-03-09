from calendar_management.tasks import send_email_celery, execute_query
from celery import group, chord
import json
import os
import re
import traceback
import datetime
import random
import requests
import logging
import pymongo
from core.init_clients import get_mongo_client
from core.email_templates import EmailTemplates

logger = logging.getLogger('django')

class Eventmanagement:
    def __init__(self, user_id) :
        # self.user_email_id = email_id
        self.user_id = user_id
    
    def get_mongo_client_db(self):
        mongo = get_mongo_client()
        if not mongo:
            return ''
        db = mongo['legaldb']

        user_collection = db['user_details']

        existing_indexes = user_collection.index_information()
        if "user_id" not in existing_indexes:
            user_collection.create_index([("user_id", 1)])

        return user_collection

    def create_new_event(self, data):
    #title, start_datetime, end_datetime, task_type, status, party_b_email=None, meetingtype=None, case_id=None, send_reminder=None):
        try:
            """
                result = users_collection.update_one(
                {"_id": "USER1"},  # Filter by the user ID (or any other criteria)
                {"$set": {"address": "123 Main St, City, Country"}}  # Add the new field
                )
                "last_updated_on": ISODate("2024-10-29T15:30:00Z")
            """
            party_b_email = data.get('partyBEmail', '')
            meetingtype = data.get('meetingtype', '')
            # start_datetime = data.get('start')
            key = data.get('id')
            del data['id']
            meet_link = self.generata_meeting_link(meetingtype) if meetingtype in ["VideoCall","VoiceCall"] else None
            # new_meeting = {
            #     key: data
            # }
            new_meeting = self.get_recured_data_dict(data,key,data.get('allDay'))

            self.get_mongo_client_db().update_one(
                        {"user_id": self.user_id},  # Select the user by user_id
                        {
                            "$set": new_meeting
                        }
                    )
            if data.get("partyBEmail"):
                partyBEmail_list = data.get("partyBEmail").split(',')
                if len(partyBEmail_list)>1:
                    email_data=[]
                    task_group = group(execute_query.s({'partyBEmail':partyBEmail, 'new_meeting':new_meeting, 'recur':True}, 'create') for partyBEmail in partyBEmail_list)
                    # Trigger the tasks
                    result = task_group.apply_async()
                else:
                    self.get_mongo_client_db().update_one(
                    {"email": party_b_email},  # Select the user by email
                    {"$set": new_meeting}  # Use meeting_id as the custom key
                )

            return {"mssg":True, "meet_link":meet_link}
        except:
            logger.error(f"Errorrr attt create_new_event -->\n{traceback.format_exc()}")
            return {"mssg":False}

    def get_recured_data_dict(self,data,key=None,all_day=False):
        """
            creating event seperateky for each day of a series, creating meeting commmon meeting key with each date appended at the end of the series. 
        """
        meeting_last_updated_on = datetime.datetime.now()
        if all_day:
            new_meeting = {}
            key_list = []
            start_date = data.get('start')
            end_date = data.get('end')
            start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            # end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            # while start_date_obj <= end_date_obj:

            updated_key = key+'_'+start_date_obj.strftime('%Y%m%d')
            # key_list.append(updated_key[:])
            data['startdate'] = start_date
            data['enddate'] = end_date
            data['meeting_last_updated_on'] = meeting_last_updated_on

            new_meeting[f"meetings.{updated_key}"] = data.copy()

            del data['start']
            del data['end']

        else:
            new_meeting = {}
            key_list = []
            start_date = data.get('start').split('T')[0]
            end_date = data.get('end').split('T')[0]
            start_time = data.get('start').split('T')[1]
            end_time = data.get('end').split('T')[1]
            start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')

            while start_date_obj <= end_date_obj:

                updated_key = key+'_'+start_date_obj.strftime('%Y%m%d')
                key_list.append(updated_key[:])
                data['startdate'] = start_date_obj.strftime('%Y-%m-%d')
                data['enddate'] = start_date_obj.strftime('%Y-%m-%d')
                data['starttime'] = start_time
                data['endtime'] = end_time
                data['meeting_last_updated_on'] = meeting_last_updated_on
                new_meeting[f"meetings.{updated_key}"] = data.copy()

                start_date_obj += datetime.timedelta(days=1)
            for meeting in new_meeting.values():
                meeting['series_key'] = key_list
                meeting['series_start_date'] = start_date
                meeting['series_end_date'] = end_date
                meeting['series_start_time'] = start_time
                meeting['series_end_time'] = end_time
                del meeting['start']
                del meeting['end']
        return new_meeting

    def generata_meeting_link(self,meetingtype):
        return f"""https://{meetingtype}-{random.randint(100000,999999)}-call.com"""

    def update_start_end_datetime_for_fetch_events(self,meetings):
        """
            storing date and time as seperate field for easy update during recurring events. but UI need single field so combining them after fetching
        """
        try:
            # logger.info(f"update_start_end_datetime_for_fetch_events --> meeting = {meetings} ")
            for key, meeting in meetings.items():
                # logger.info(f"update_start_end_datetime_for_fetch_events --> meeting = {meeting} ")
                if not meeting.get('allDay') :
                    start_datetime = f"{meeting['startdate']}T{meeting['starttime']}"
                    end_datetime = f"{meeting['enddate']}T{meeting['endtime']}"
                    
                    meeting['start'] = start_datetime
                    meeting['end'] = end_datetime
                    
                    del meeting['startdate']
                    del meeting['enddate']
                    del meeting['starttime']
                    del meeting['endtime']
                
                else:                    
                    meeting['start'] = meeting['startdate']
                    meeting['end'] = meeting['enddate']
                    
                    del meeting['startdate']
                    del meeting['enddate']
        
            return meetings
        except Exception as err:
            logger.error(traceback.format_exc())
            logger.error(f"EERROR update_start_end_datetime_for_fetch_events  ---->  {err}")

    def get_all_events_for_user(self, startdate=None, enddate=None, both_active_inactive=None):
        try:
            if startdate and enddate:
                ## all active meetings between daterange
                pipeline = [
                                {
                                    '$match': {
                                        'user_id': self.user_id
                                    }
                                },
                                {
                                    '$project': {
                                        'meetingsArray': {
                                            '$objectToArray': '$meetings'
                                        }
                                    }
                                },
                                {
                                    '$project': {
                                        'meetingsArray': {
                                            '$filter': {
                                                'input': '$meetingsArray',
                                                'as': 'meeting',
                                                'cond': {
                                                    '$and': [
                                                        { '$eq': ['$$meeting.v.Status', 'Y'] },
                                                        { '$gte': ['$$meeting.v.startdate', startdate] },
                                                        { '$lte': ['$$meeting.v.startdate', enddate] }
                                                    ]
                                                }
                                            }
                                        }
                                    }
                                },
                                {
                                    '$project': {
                                        'meetings': {
                                            '$arrayToObject': '$meetingsArray'
                                        }
                                    }
                                },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'meetings': 1
                                    }
                                }
                            ]
                meetings =  next(self.get_mongo_client_db().aggregate(pipeline), {"meetings": {}})
            elif both_active_inactive:
                ## all active and inactive meetings
                meetings =  self.get_mongo_client_db().find_one({"user_id": self.user_id}, {"meetings": 1, "_id": 0})
            else:
                ## all active meetings
                pipeline = [
                                {
                                    '$match': {
                                        'user_id': self.user_id
                                    }
                                },
                                {
                                    '$project': {
                                        'meetingsArray': {
                                            '$objectToArray': '$meetings'
                                        }
                                    }
                                },
                                {
                                    '$project': {
                                        'meetingsArray': {
                                            '$filter': {
                                                'input': '$meetingsArray',
                                                'as': 'meeting',
                                                'cond': {
                                                    '$and': [
                                                        { '$eq': ['$$meeting.v.Status', 'Y'] }
                                                    ]
                                                }
                                            }
                                        }
                                    }
                                },
                                {
                                    '$project': {
                                        'meetings': {
                                            '$arrayToObject': '$meetingsArray'
                                        }
                                    }
                                },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'meetings': 1
                                    }
                                }
                            ]
                meetings =  next(self.get_mongo_client_db().aggregate(pipeline), {"meetings": {}})
            updated_meetings = self.update_start_end_datetime_for_fetch_events(meetings.get('meetings'))
            # logger.info(f"=====================  {updated_meetings}  =================================")
            return {"meetings":updated_meetings}

        except:
            logger.error(f"Errorrr attt get_all_events_for_user -->\n{traceback.format_exc()}")
            return {}


    def delete_event_for_user(self, input_data):
        try:
            # Find the user and delete the specific meeting
            logger.info(f"delete_event_for_user ----------------> {input_data}")
            key = input_data["id"]
            title = input_data.get("title")
            recurring = input_data.get("recurring")
            occurrence = input_data.get("occurrence")
            once_flag = False ## for deleteing series_key element from the list if single occuracne is deleted out of series
            now_time = datetime.datetime.now()
            if recurring and occurrence == "entire series":
                # meeting_last_updated_on = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')
                projection_series = {
                f"meetings.{key}.series_key": 1
                }

                user_document = self.get_mongo_client_db().find_one({"user_id": self.user_id}, projection_series)

                if not user_document:
                    logger.error(f"User document with user_id '{self.user_id}' not found.")
                    return

                series_keys = user_document.get("meetings", {}).get(key, {}).get("series_key", [])

                if not series_keys:
                    logger.error(f"No series_keys found for meeting '{key}'.")
                    return

                logger.info(f"Series Keys: {series_keys}")

                # Step 2: Fetch the Status of each meeting in series_keys
                # Construct projection to include only the Status of each series_key
                projection_status = {f"meetings.{skey}.Status": 1 for skey in series_keys}

                user_document_status = self.get_mongo_client_db().find_one({"user_id": self.user_id}, projection_status)

                if not user_document_status:
                    logger.error(f"User document with user_id '{self.user_id}' not found in status projection.")
                    return

                # Step 3: Filter series_keys where Status == 'Y'
                active_series_keys = []
                for skey in series_keys:
                    meeting = user_document_status.get("meetings", {}).get(skey, {})
                    status = meeting.get("Status")
                    if status == "Y":
                        active_series_keys.append(skey)
                        logger.debug(f"Meeting '{skey}' is active and will be updated.")
                    else:
                        logger.debug(f"Skipping meeting '{skey}' with Status '{status}'.")

                if not active_series_keys:
                    logger.info("No active meetings with Status 'Y' found in the series.")
                    return

                logger.info(f"Active Series Keys to Update: {active_series_keys}")

                # Step 4: Construct the $set dictionary for updates
                current_time = now_time.strftime('%Y-%m-%dT%H:%M')  # Current UTC time in desired format

                set_dict = {
                    "last_updated_on": now_time  # Update the last updated timestamp for the entire document
                }

                for skey in active_series_keys:
                    set_dict[f"meetings.{skey}.Status"] = "D"
                    set_dict[f"meetings.{skey}.meeting_last_updated_on"] = current_time

                logger.info(f"Set Dictionary: {set_dict}")

                # Step 5: Perform the update operation
                update_result = self.get_mongo_client_db().update_one(
                    {"user_id": self.user_id},
                    {"$set": set_dict}
                )

                # Send professional deletion email for entire series
                fname = input_data.get('fname', 'User')
                lname = input_data.get('lname', '')
                email_subject, email_body = EmailTemplates.event_deleted_series(fname, lname, title)
                self.send_email_by_celery([[input_data.get('email_id'), email_subject, email_body]], input_data.get("partyBEmail"))

                if input_data.get("partyBEmail"):
                    partyBEmail_list = input_data.get("partyBEmail").split(',')
                    if len(partyBEmail_list)>1:
                        email_data=[]
                        task_group = group(execute_query.s({'partyBEmail':partyBEmail, 'unset_dict':set_dict}, 'delete') for partyBEmail in partyBEmail_list)
                        # Trigger the tasks
                        result = task_group.apply_async()
                    else:
                        self.get_mongo_client_db().update_one(
                        {"email": partyBEmail_list[0]},
                        {"$set": set_dict}
                    )

            else:
                if recurring and occurrence == "only once":
                    projection_series = {
                        f"meetings.{key}.series_key": 1  # Fetch only the series_key for the specified meeting
                    }

                    try:
                        user_document = self.get_mongo_client_db().find_one({"user_id": self.user_id}, projection_series)
                    except Exception as e:
                        logger.error(f"Error fetching user document: {e}")
                        return

                    if not user_document:
                        logger.error(f"User document with user_id '{self.user_id}' not found.")
                        return

                    series_keys = user_document.get("meetings", {}).get(key, {}).get("series_key", [])

                    if not series_keys:
                        logger.error(f"No series_keys found for meeting '{key}'.")
                        return

                    logger.info(f"Series Keys: {series_keys}")


                    # Step 3: Prepare bulk operations to remove the meeting_key from other meetings' series_key arrays
                    bulk_operations = []
                    for skey in series_keys:
                        if skey != key:
                            bulk_operations.append(pymongo.UpdateOne(
                                {"user_id": self.user_id, f"meetings.{skey}.series_key": key},
                                {"$pull": {f"meetings.{skey}.series_key": key}}
                            ))

                    if bulk_operations:
                        logger.info(f"Preparing to remove '{key}' from series_key arrays of other meetings.")
        
                        
                        # Execute bulk write
                        if bulk_operations:
                            result = self.get_mongo_client_db().bulk_write(bulk_operations)
                            logger.info(f"Modified count: {result.modified_count}")

                    once_flag = True
                
                # Step 2: Construct the $set dictionary to update Status and meeting_last_updated_on for the specific meeting
                current_time = now_time.strftime('%Y-%m-%dT%H:%M')  # Current UTC time in desired format

                set_dict = {
                    "last_updated_on": now_time  # Update the last_updated_on timestamp for the entire document
                }

                set_dict[f"meetings.{key}.Status"] = "D"
                set_dict[f"meetings.{key}.meeting_last_updated_on"] = current_time

                logger.info(f"Set Dictionary for Single Occurrence Update: {set_dict}")

                update_result_set = self.get_mongo_client_db().update_one(
                {"user_id": self.user_id},
                {"$set": set_dict}
                )

                logger.info(f"Set Operation: Modified count: {update_result_set.modified_count}")
                
                # Send professional deletion email for single event
                fname = input_data.get('fname', 'User')
                lname = input_data.get('lname', '')
                email_subject, email_body = EmailTemplates.event_deleted_single(fname, lname, title)
                self.send_email_by_celery([[input_data.get('email_id'), email_subject, email_body]], input_data.get("partyBEmail"))
                if input_data.get("partyBEmail"):
                    partyBEmail_list = input_data.get("partyBEmail").split(',')
                    # unset_dict = {f"meetings.{key}": "D"}
                    if len(partyBEmail_list)>1:
                        # email_data=[]
                        if once_flag:
                            task_group = group(execute_query.s({'partyBEmail':partyBEmail, 'unset_dict':set_dict, 'once_flag':True, 'series_keys':series_keys, 'key':key}, 'delete') for partyBEmail in partyBEmail_list)
                        else:
                            task_group = group(execute_query.s({'partyBEmail':partyBEmail, 'unset_dict':set_dict}, 'delete') for partyBEmail in partyBEmail_list)
                        # Trigger the tasks
                        result = task_group.apply_async()
                    else:
                        self.get_mongo_client_db().update_one(
                            {"email": partyBEmail_list[0]},
                            {"$set": set_dict}
                        )
                        # self.send_email_by_celery([[partyBEmail_list[0],'Event Deleted',f"""Hi Sir/Mam,\nYour event {title} is deleted.\nRegards,\nLegalAI Team"""]])
            return True 
        except Exception as err:
            logger.error(f"errrooorr at delete_event_for_user event --------> {traceback.format_exc()}")
            return False

    def update_event_for_user(self, input_data):
        try:
            logger.info(f"update_event_for_user ============= input_DATATTAT ---> {input_data}")
            key = input_data.get('id')
            del input_data['id']
            title = input_data.get("title")
            ## is introduced , to keep a note of when meeting updadted, will help in sending remainders
            now_time = datetime.datetime.now()
            input_data['meeting_last_updated_on'] = now_time.strftime('%Y-%m-%dT%H:%M')

            update_key_list = input_data.get('updatedFields')
            update_key_list.append('meeting_last_updated_on')
            updated_values = {}
            pretty_updated = {}

            """
                doing below part so that, start and end date do not get update for the whole series only the time should be updated.
                creating new dict with updated fields as we don't want to update complete series with all data.
            """
            for f in update_key_list :
                if f == "startTime":
                    updated_values['starttime'] = input_data.get('start').split('T')[1]
                    pretty_updated[f.upper()] = input_data.get('start')
                elif f == "endTime":
                    updated_values['endtime'] = input_data.get('end').split('T')[1]
                    pretty_updated[f.upper()] = input_data.get('end')
                else:
                    updated_values[f] = input_data.get(f)
                    pretty_updated[f.upper()] = input_data.get(f)
                logger.info(f"update_key_list ------========> {f} || {input_data.get(f)}")
            
            ## occurance will  be marked only once if we choose to update only one event time in meeting, but we can't change occurance to once in db as this is part of series of event, so deletiing it.
            if 'occurrence' in updated_values:
                del updated_values['occurrence']
                del pretty_updated['occurrence'.upper()]
            #this paramter is for code purpose, no use for USER mails
            del pretty_updated['meeting_last_updated_on'.upper()]
            pretty_updated_values = json.dumps(pretty_updated, indent=4)

            recurring = input_data.get("recurring")
            occurrence = input_data.get("occurrence")
            logger.info(f"updated_values ------> {updated_values} +++++++++++ pretty_updated_values ---> {pretty_updated_values}")
            if recurring and occurrence == "entire series":
                # Step 1: Fetch the series_key array for the specified meeting
                projection = {
                    f"meetings.{key}.series_key": 1
                }

                user_document = self.get_mongo_client_db().find_one({"user_id": self.user_id}, projection)

                if not user_document:
                    logger.error(f"User document with user_id '{self.user_id}' not found.")
                    return

                series_keys = user_document.get("meetings", {}).get(key, {}).get("series_key", [])

                if not series_keys:
                    logger.error(f"No series_keys found for meeting '{key}'.")
                    return

                logger.info(f"Series Keys: {series_keys}")

                # Step 2: Fetch the Status of each meeting in series_keys
                # Construct projection to include only the Status of each series_key
                status_projection = {f"meetings.{skey}.Status": 1 for skey in series_keys}

                user_document_status = self.get_mongo_client_db().find_one({"user_id": self.user_id}, status_projection)

                if not user_document_status:
                    logger.error(f"User document with user_id '{self.user_id}' not found in status projection.")
                    return

                # Filter series_keys where Status == 'Y'
                active_series_keys = []
                for skey in series_keys:
                    meeting = user_document_status.get("meetings", {}).get(skey, {})
                    status = meeting.get("Status")
                    if status == "Y":
                        active_series_keys.append(skey)
                    else:
                        logger.debug(f"Skipping meeting '{skey}' with Status '{status}'.")

                if not active_series_keys:
                    logger.info("No active meetings with Status 'Y' found in the series.")
                    return

                logger.info(f"Active Series Keys to Update: {active_series_keys}")

                # Step 3: Construct the $set dictionary for updates
                set_dict = {
                    "last_updated_on": now_time  # Update the last updated timestamp
                }
                for skey in active_series_keys:
                    for field, value in updated_values.items():
                        set_dict[f"meetings.{skey}.{field}"] = value

                # Perform the update operation
                self.get_mongo_client_db().update_one(
                    {
                        "user_id": self.user_id,
                    },
                    {
                        "$set": set_dict
                    }
                )
                
                # Send professional update email for entire series
                fname = input_data.get('fname', 'User')
                lname = input_data.get('lname', '')
                email_subject, email_body = EmailTemplates.event_updated_entire_series(fname, lname, title, pretty_updated_values)
                self.send_email_by_celery([[input_data.get('email_id'), email_subject, email_body]], input_data.get('partyBEmail'))

                if input_data.get("partyBEmail"):
                    partyBEmail_list = input_data.get("partyBEmail").split(',')
                    if len(partyBEmail_list)>1:
                        task_group = group(execute_query.s({'partyBEmail':partyBEmail, 'set_dict':set_dict}, 'update') for partyBEmail in partyBEmail_list)
                        result = task_group.apply_async()
                    else:
                        self.get_mongo_client_db().update_one(
                                        {
                                            "email": partyBEmail_list[0],
                                        },
                                        {
                                            "$set": set_dict
                                        },
                                        upsert=False
                                    )

            else:
                set_dict = {
                                "last_updated_on": now_time
                            }
                for field, value in updated_values.items():
                    set_dict[f"meetings.{key}.{field}"] = value
                self.get_mongo_client_db().update_one(
                    {
                        "user_id": self.user_id,
                        # f"meetings.{key}": {"$exists": True}  # Check if the key exists
                    },
                    {
                        "$set": set_dict
                    }
                )
                
                # Send professional update email for single event
                fname = input_data.get('fname', 'User')
                lname = input_data.get('lname', '')
                email_subject, email_body = EmailTemplates.event_updated_single(fname, lname, title, pretty_updated_values)
                self.send_email_by_celery([[input_data.get('email_id'), email_subject, email_body]], input_data.get('partyBEmail'))
    
                if input_data.get("partyBEmail"):
                    partyBEmail_list = input_data.get("partyBEmail").split(',')
                    if len(partyBEmail_list)>1:
                        email_data=[]
                        task_group = group(execute_query.s({'partyBEmail':partyBEmail, 'set_dict':set_dict}, 'update') for partyBEmail in partyBEmail_list)
                        # Trigger the tasks
                        result = task_group.apply_async()
                    else:
                        self.get_mongo_client_db().update_one(
                                        {
                                            "email": partyBEmail_list[0],
                                        },
                                        {
                                            "$set": set_dict
                                        },
                                        upsert=False
                                    )
            
            return True
        except Exception as err:
            logger.error(f"errrooorr at udpate_event_for_user event --------> {traceback.format_exc()}")
            return False

    def send_email_by_celery(self, email_data, cc_emails=None):
        try:
            logger.info(f"send_email_by_celery ---- email_data ==== > {email_data}")
            send_email_celery.delay(email_data[0][0], email_data[0][1] ,email_data[0][-1], cc_emails)
            return True
        except Exception as err:
            logger.error(f"errrooorr at send_email_by_celery event --------> {traceback.format_exc()}")
            return False
