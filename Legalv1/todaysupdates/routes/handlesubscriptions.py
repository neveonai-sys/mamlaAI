import os
# import math
# from io import BytesIO
# from docx import Document
# from pdfminer.high_level import extract_text as extract_text_from_pdf
from core.init_clients import get_mongo_client, get_mongo_db
import datetime
import json
import traceback
import logging
logger = logging.getLogger('django')

# api_key = os.getenv('OPENAI_API_KEY')

class CreateandmanageSubscription:
    def __init__(self):
        pass

    def get_mongo_client_db(self):
        mongo = get_mongo_client()
        if not mongo:
            return ''
        db = get_mongo_db()
        return db

    def get_user_subscriptions(self, user_id):
        try:
            user_doc = self.get_mongo_client_db()['user_details'].find_one(
                            {"user_id": user_id},  # Filter by user_id
                            {"subscribed_courts": 1, "_id": 0}  # Projection to include only case_ids and exclude _id
                        )
            # logger.info(f"user_doc --->>>> {user_doc}")
            if not user_doc:
                return []
            subscribed_courts = user_doc.get("subscribed_courts", [])
            return subscribed_courts
        except Exception as e:
            logger.error(traceback.print_exc())
            raise Exception(str(e))

    def get_paralegal_courts(self, user_id):
        try:
            user_doc = self.get_mongo_client_db()['user_details'].find_one(
                            {"user_id": user_id},  # Filter by user_id
                            {"courts": 1, "_id": 0}  # Projection to include only case_ids and exclude _id
                        )
            # logger.info(f"user_doc --->>>> {user_doc}")
            if not user_doc:
                return []
            courts = user_doc.get("courts", [])
            return courts
        except Exception as e:
            logger.error(traceback.print_exc())
            raise Exception(str(e))
        
    def subscribe_court_and_verify_existence_and_cout(self, user_id, court):
        try:
            user_doc = self.get_mongo_client_db()['user_details'].find_one(
                            {"user_id": user_id},  # Filter by user_id
                            {"subscribed_courts": 1, "_id": 0}  # Projection to include only case_ids and exclude _id
                        )
            # if not user_doc:
            #     raise Exception("User not found")
            subscribed_courts = user_doc.get("subscribed_courts", [])
            if len(subscribed_courts) >= 4:
                raise Exception("Max 4 courts allowed")
            if court in subscribed_courts:
                # Already subscribed
                raise Exception(subscribed_courts)
            subscribed_courts.append(court)
            self.get_mongo_client_db()['user_details'].update_one(
                {"user_id": user_id},
                {"$set": {"subscribed_courts": subscribed_courts}}
            )
            return  subscribed_courts
        except Exception as e:
            logger.error(traceback.print_exc())
            raise Exception(str(e))
        
    def unsubscribe_court_and_verify_existence(self, user_id, court):
        try:
            user_doc = self.get_mongo_client_db()['user_details'].find_one(
                            {"user_id": user_id},  # Filter by user_id
                            {"subscribed_courts": 1, "_id": 0}  # Projection to include only case_ids and exclude _id
                        )
            # if not user_doc:
            #     raise Exception("User not found")
            subscribed_courts = user_doc.get("subscribed_courts", [])
            if court not in subscribed_courts:
                raise Exception("Court not subscribed")
            subscribed_courts.remove(court)
            self.get_mongo_client_db()['user_details'].update_one(
                {"user_id": user_id},
                {"$set": {"subscribed_courts": subscribed_courts}}
            )
            return subscribed_courts
        except Exception as e:
            logger.error(traceback.print_exc())
            raise Exception(str(e))
        
    def fetch_updates_for_subscribed_courts(self, user_id, start_date_str, end_date_str, requested_court):
        try:
            user_doc = self.get_mongo_client_db()['user_details'].find_one(
                            {"user_id": user_id},  # Filter by user_id
                            {"subscribed_courts": 1, "_id": 0}  # Projection to include only case_ids and exclude _id
                        )
            logger.info(f"fetch_updates_for_subscribed_courts === user_doc --->>>> {user_doc}")
            if not user_doc:
                return []
            subscribed_courts = user_doc.get("subscribed_courts", [])

            if not subscribed_courts:
                # If user not subscribed to any courts, return empty
                return []

            # 1. Date Range
            # If not provided, default to today's date
            now = datetime.datetime.now()
            if start_date_str and end_date_str:
                # parse the user-supplied date range
                start_of_day = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
                # we assume they mean the very start of that day
                start_of_day = start_of_day.replace(hour=0, minute=0, second=0)
                
                end_of_day = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
                # we assume they mean the end of that day
                end_of_day = end_of_day.replace(hour=23, minute=59, second=59)
            else:
                # default to "today"
                start_of_day = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
                end_of_day = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)

            # 2. Court Filter
            # If `requested_court` is given, ensure it's in the subscribed_courts
            if requested_court and requested_court in subscribed_courts:
                courts_filter = [requested_court]
            else:
                # no single-court preference or invalid preference => all subscribed
                courts_filter = subscribed_courts

            # 3. Aggregation Pipeline in `whatsapp_chat_sessions`
            pipeline = [
                {
                    "$match": {
                        "updates": {
                            "$elemMatch": {
                                "court": {"$in": courts_filter},
                                "time": {"$gte": start_of_day, "$lte": end_of_day}
                            }
                        }
                    }
                },
                {"$unwind": "$updates"},
                {
                    "$match": {
                        "updates.court": {"$in": courts_filter},
                        "updates.time": {"$gte": start_of_day, "$lte": end_of_day}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "court": "$updates.court",
                        "update": "$updates.update",
                        "transcription": "$updates.transcription",
                        "time": "$updates.time",
                        "paralegal": "$user_name",      # Or whichever field identifies the paralegal
                        "message_type": "$updates.message_type"  # If your doc has message_type at root
                    }
                }
            ]

            cursor = self.get_mongo_client_db()['whatsapp_chat_sessions'].aggregate(pipeline)
            updates_list = list(cursor)
            logger.info(f"""pipeline ----->>>> {pipeline}\nupdates_list ----->>> {updates_list} """)
            final_updates = []
            for upd in updates_list:
                audio_url = None
                # If it's audio, parse the path from "update" field
                # e.g. "[Audio file saved at: ../../../audio_input/<file.ogg>]"
                # We'll interpret $message_type as "record" => audio
                # (If that field is actually stored within each "updates" array item, adjust accordingly.)
                if upd.get("message_type") == "record" or "audio" in upd.get("update", "").lower():
                    update_str = upd.get("update", "")
                    if update_str.startswith("[Audio file saved at:"):
                        audio_path = update_str.replace("[Audio file saved at:", "").replace("]", "").strip()
                        filename = audio_path.split('/')[-1]
                        # e.g. "/static/audio_input/<filename>"
                        audio_url = f"/home/pronoys/products/audio_input/{filename}"

                final_updates.append({
                        "court": upd.get("court"),
                        "update": upd.get("update"),          # raw update text or audio placeholder
                        "message_type": upd.get("message_type"),
                        "transcription": upd.get("transcription") or "",  # ensure empty string if none
                        "paralegal": upd.get("paralegal"),
                        "time": upd.get("time").isoformat() if isinstance(upd.get("time"), datetime.datetime) else str(upd.get("time")),
                        "audio_url": audio_url
                    })
            return final_updates
        except Exception as e:
            logger.error(traceback.print_exc())
            raise Exception(str(e))
        
    def paralegal_update_court_subscription(self, user_id, court):
        try:
            user_doc = self.get_mongo_client_db()['user_details'].find_one({"user_id": user_id})
            if not user_doc:
                return []
            if user_doc.get("user_type") != "Paralegal":
                return []
            if not court:
                return []
            subscribed_courts = user_doc.get("courts", [])
            if len(subscribed_courts) >= 3:
                raise Exception("Max 3 courts allowed")
            if court not in subscribed_courts:
                subscribed_courts.append(court)
                self.get_mongo_client_db()['user_details'].update_one(
                    {"user_id": user_id},
                    {"$set": {"subscribed_courts": subscribed_courts}}
                )
            return subscribed_courts
        except Exception as e:
            logger.error(traceback.print_exc())
            raise Exception(str(e))
        
    def paralegal_remove_court_subscription(self, user_id, court):
        try:
            user_doc = self.get_mongo_client_db()['user_details'].find_one({"user_id": user_id})
            if not user_doc:
                return []
            if user_doc.get("user_type") != "Paralegal":
                return []
            if not court:
                return []
            subscribed_courts = user_doc.get("courts", [])
            if court in subscribed_courts:
                subscribed_courts.remove(court)
                self.get_mongo_client_db()['user_details'].update_one(
                    {"user_id": user_id},
                    {"$set": {"subscribed_courts": subscribed_courts}}
                )
            return subscribed_courts
        except Exception as e:
            logger.error(traceback.print_exc())
            raise Exception(str(e))
        
    def fetch_paralegal_court_updates(self, user_id, start_date_str, end_date_str, requested_court):
        try:
            user_doc = self.get_mongo_client_db()['user_details'].find_one({"user_id": user_id})
            logger.info(f"fetch_paralegal_court_updates === user_doc --->>>> {user_doc}")
            if not user_doc:
                return []
            # we can identify paralegal by phone_number or user_id
            paralegal_phone = user_doc.get("phone_number")  # or user_id       

            # default date range = today
            now = datetime.datetime.now()
            if start_date_str and end_date_str:
                start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
                start_of_day = start_dt.replace(hour=0, minute=0, second=0)
                end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
                end_of_day = end_dt.replace(hour=23, minute=59, second=59)
            else:
                start_of_day = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
                end_of_day = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)

            # For the "court" filter, if not provided, we fetch all
            court_filter = {}
            if requested_court:
                court_filter = {"$eq": requested_court}
            else:
                court_filter = {"$exists": True}  # match any court

            pipeline = [
                {
                    "$match": {
                        # Only documents where "phone_number" (paralegal) matches
                        "phone_number": f"91{paralegal_phone}",
                        "updates": {
                            "$elemMatch": {
                                "court": court_filter,
                                "time": {"$gte": start_of_day, "$lte": end_of_day}
                            }
                        }
                    }
                },
                {"$unwind": "$updates"},
                {
                    "$match": {
                        "phone_number": f"91{paralegal_phone}",
                        "updates.court": court_filter,
                        "updates.time": {"$gte": start_of_day, "$lte": end_of_day}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "court": "$updates.court",
                        "update": "$updates.update",
                        "transcription": "$updates.transcription",
                        "time": "$updates.time",
                        "message_type": "$updates.message_type",
                        "paralegal": "$phone_number"
                    }
                }
            ]

            cursor = self.get_mongo_client_db()['whatsapp_chat_sessions'].aggregate(pipeline)
            updates_list = list(cursor)

            # logger.info(f"fetch_paralegal_court_updates ||| pipeline ----> {pipeline} || updates_list ===> {updates_list}")

            final_updates = []
            for upd in updates_list:
                audio_url = None
                if upd.get("message_type") == "record":
                    update_str = upd.get("update", "")
                    if update_str.startswith("[Audio file saved at:"):
                        path_str = update_str.replace("[Audio file saved at:", "").replace("]", "").strip()
                        filename = path_str.split('/')[-1]
                        audio_url = f"/static/audio_input/{filename}"

                final_updates.append({
                    "court": upd.get("court"),
                    "update": upd.get("update"),
                    "transcription": upd.get("transcription") or "",
                    "message_type": upd.get("message_type"),
                    "paralegal": upd.get("paralegal"),
                    "time": upd.get("time").isoformat() if isinstance(upd.get("time"), datetime.datetime) else str(upd.get("time")),
                    "audio_url": audio_url
                })

            return final_updates
        except Exception as e:
            logger.error(traceback.print_exc())
            raise Exception(str(e))
