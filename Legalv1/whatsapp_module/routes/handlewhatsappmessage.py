import datetime
from typing import Optional, Dict, List
import json
import re
import time
import os
import requests
import logging
import traceback
from pydub import AudioSegment

from core.init_clients import get_mongo_client, get_supabase_client
from whatsapp_module.tasks import process_audio_async

logger = logging.getLogger('django')

ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
APP_SECRET = os.getenv('APP_SECRET')
APP_ID = os.getenv('APP_ID')

MESSAGE_COUNT = {}
MAX_MESSAGES = 10
TIME_WINDOW = 60  # in seconds

SESSION_TIMEOUT = 20  # minutes

MAX_TEXT_LENGTH = 500
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
ALLOWED_CHARS_PATTERN = re.compile(r'[^a-zA-Z0-9\s.,!?@#:_-]')


class Whatsappmessageformulation:
    """
    Main class for sending/receiving WhatsApp messages, session data, etc.
    """

    def __init__(self, incoming_user_number: str):
        self.incoming_user_number = incoming_user_number
        self._user_details = self._fetch_user_details()

    def get_mongo_client_db(self):
        mongo = get_mongo_client()
        if not mongo:
            return None
        return mongo["legaldb"]

    def _fetch_user_details(self) -> Dict[str, Optional[str]]:
        """
        1) Query Supabase by phone => get user_id, phone, fname, lname, email.
        2) Then query Mongo by user_id => get user_type, default_court, court_list, etc.
        Combine them.
        """
        ph_num = self.incoming_user_number
        if ph_num.startswith("91"):
            ph_num = ph_num[2:]

        supabase = get_supabase_client()
        user_resp = (
            supabase.table("user_metadata")
            .select("user_id, phone, first_name, last_name, email")
            .eq("phone", ph_num)
            .execute()
        )
        sup_data = user_resp.data
        if not sup_data:
            return {}

        sup_user = sup_data[0]
        user_id = sup_user.get("user_id")
        if not user_id:
            return {}
        logger.info(f"sup_user ---------->>>>> {sup_user}")
        db = self.get_mongo_client_db()
        # if not db:
        #     return {}

        mongo_profile = db["user_details"].find_one({"user_id": user_id})
        if not mongo_profile:
            return {}
        logger.info(f"mongo_profile ---------->>>>> {mongo_profile}")
        user_details = {
            "user_id": user_id,
            "fname": sup_user.get("first_name"),
            "lname": sup_user.get("last_name"),
            "email": sup_user.get("email"),
            "phone": sup_user.get("phone"),
            "user_type": mongo_profile.get("user_type"),
            "default_court": mongo_profile.get("default_court"),
            "court_list": mongo_profile.get("courts", [])
        }
        return user_details

    def get_user_details(self) -> Dict[str, Optional[str]]:
        return self._user_details

    def send_whatsapp_message(self, payload: dict):
        try:
            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            resp = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
            logger.info(f"WhatsApp API response: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"send_whatsapp_message ERROR: {e}\n{traceback.format_exc()}")

    def send_text_message(self, text: str):
        payload = {
            "messaging_product": "whatsapp",
            "to": self.incoming_user_number,
            "type": "text",
            "text": {"body": text}
        }
        self.send_whatsapp_message(payload)

    def send_interactive_buttons(self, body_text: str, buttons: List[dict]):
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": self.incoming_user_number,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body_text},
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {"id": b["id"], "title": b["title"]}
                            } for b in buttons
                        ]
                    }
                }
            }
            self.send_whatsapp_message(payload)
        except Exception as e:
            logger.error(f"send_interactive_buttons ERROR: {e}\n{traceback.format_exc()}")

    def send_interactive_list(self, header_text: str, body_text: str, items: list):
        """
        Send an interactive list message with up to 100 items (10 sections × 10 rows).
        Each item is a dict like {"id": "some_id", "title": "Display Title"}.
        """
        try:
            # WhatsApp limit: 10 sections, each up to 10 rows => 100 items total
            max_total_items = 100
            if len(items) > max_total_items:
                self.send_text_message(
                    f"You have {len(items)} items, but WhatsApp only supports 100 in a single list. "
                    "Showing the first 100 items only."
                )
                items = items[:max_total_items]

            # Break items into chunks of 10 for each section
            chunk_size = 10
            sections = []
            for start_i in range(0, len(items), chunk_size):
                chunk = items[start_i: start_i + chunk_size]

                section_index = len(sections) + 1
                section_rows = []
                for row_item in chunk:
                    row_dict = {
                        "id": row_item["id"],    # the 'list_reply' ID user sees in the webhook
                        "title": row_item["title"]
                    }
                    # Optionally, you can do: row_dict["description"] = "short desc"
                    section_rows.append(row_dict)

                # Title for each section
                section_title = f"Section {section_index}"
                sections.append({
                    "title": section_title,
                    "rows": section_rows
                })

                # If we already have 10 sections, stop
                if len(sections) == 10:
                    break

            payload = {
                "messaging_product": "whatsapp",
                "to": self.incoming_user_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {"type": "text", "text": header_text},
                    "body": {"text": body_text},
                    "footer": {"text": "Select an item below."},
                    "action": {
                        "button": "View",
                        "sections": sections
                    }
                }
            }

            self.send_whatsapp_message(payload)
        except Exception as e:
            logger.error(f"send_interactive_list ERROR: {e}\n{traceback.format_exc()}")


    def sanitize_input(self, input_str: str) -> str:
        if not input_str:
            return ""
        input_str = input_str.strip()[:MAX_TEXT_LENGTH]
        input_str = HTML_TAG_PATTERN.sub("", input_str)
        input_str = ALLOWED_CHARS_PATTERN.sub("", input_str)
        return input_str

    def rate_limit_check(self) -> bool:
        now = time.time()
        if self.incoming_user_number not in MESSAGE_COUNT:
            MESSAGE_COUNT[self.incoming_user_number] = []
        MESSAGE_COUNT[self.incoming_user_number] = [
            t for t in MESSAGE_COUNT[self.incoming_user_number]
            if (now - t) < TIME_WINDOW
        ]
        if len(MESSAGE_COUNT[self.incoming_user_number]) >= MAX_MESSAGES:
            return False
        MESSAGE_COUNT[self.incoming_user_number].append(now)
        return True

    def get_session(self) -> Optional[dict]:
        db = self.get_mongo_client_db()
        # if not db:
        #     return None
        return db['whatsapp_chat_sessions'].find_one({
            "phone_number": self.incoming_user_number,
            "active": True
        })

    def start_session(self):
        db = self.get_mongo_client_db()
        # if not db:
        #     return
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        db['whatsapp_chat_sessions'].update_many(
            {"phone_number": self.incoming_user_number, "active": True},
            {
                "$set": {
                    "active": False,
                    "ended_at": now_utc,
                    "end_reason": "new_session"
                }
            }
        )
        user_fname = self._user_details.get("fname", "")
        user_lname = self._user_details.get("lname", "")
        session_data = {
            "phone_number": self.incoming_user_number,
            "user_name": f"{user_fname} {user_lname}",
            "active": True,
            "messages": [],
            "started_at": now_utc,
            "last_interaction": now_utc,
            "state": None
        }
        db['whatsapp_chat_sessions'].insert_one(session_data)

    def update_session(self, user_msg=None, bot_msg=None):
        db = self.get_mongo_client_db()
        # if not db:
        #     return

        now_time = datetime.datetime.now(datetime.timezone.utc)
        update_fields = {"$set": {"last_interaction": now_time}}

        if user_msg:
            update_fields.setdefault("$push", {}).setdefault("messages", []).append(
                {"sender": "user", "text": user_msg, "time": now_time}
            )
        if bot_msg:
            update_fields.setdefault("$push", {}).setdefault("messages", []).append(
                {"sender": "bot", "text": bot_msg, "time": now_time}
            )

        db['whatsapp_chat_sessions'].update_one(
            {"phone_number": self.incoming_user_number, "active": True},
            update_fields
        )

    def end_session(self, reason="user_end"):
        db = self.get_mongo_client_db()
        # if not db:
        #     return
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        db['whatsapp_chat_sessions'].update_one(
            {"phone_number": self.incoming_user_number, "active": True},
            {
                "$set": {
                    "active": False,
                    "state": "end",
                    "ended_at": now_utc,
                    "end_reason": reason
                }
            }
        )

    def check_session_timeout(self) -> bool:
        s = self.get_session()
        if not s:
            return False
        last_inter = s.get("last_interaction")
        if not last_inter:
            return False
        if last_inter.tzinfo is None:
            last_inter = last_inter.replace(tzinfo=datetime.timezone.utc)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        if (now_utc - last_inter) > datetime.timedelta(minutes=20):
            return True
        return False

    def greet_user_as_per_usertype(self, user_type):
        fname = self._user_details.get("fname", "")
        if user_type == "Paralegal":
            self.send_interactive_buttons(
                f"Welcome {fname}! Please choose what your update is regarding:",
                [
                    {"id": "court",        "title": "Court"},
                    {"id": "clientlawyer", "title": "Client/Lawyer"},
                    {"id": "task",         "title": "Task Update"}
                ]
            )
            self.update_session(bot_msg="Please choose: Court, Client/Lawyer, or Task Update.")
        elif user_type == "Client":
            self.send_interactive_buttons(
                f"Welcome {fname}! Please choose the service you want:",
                [
                    {"id": "case",         "title": "Case Update"},
                    {"id": "certfiedcopy", "title": "Apply Certified Copy"}
                ]
            )
            self.update_session(bot_msg="Please choose: Case Update or Apply Certified Copy.")
        else:
            self.send_text_message(f"Hi {fname}, user type not recognized.")
            self.end_session("invalid_usertype")

    def get_courts_for_user(self, courts: list):
        if not courts:
            self.send_text_message("No courts assigned. Ending session.")
            self.end_session("no_courts")
            return

        if len(courts) > 3:
            lines = ["You have multiple courts. Please type the exact court name from this list:"]
            for c in courts:
                lines.append(f"- {c}")
            self.send_text_message("\n".join(lines))
            self.update_session(bot_msg="Please type the exact court name.")
        else:
            buttons = [{"id": c, "title": c[:20]} for c in courts]
            self.send_interactive_buttons("Select a court to update:", buttons)
            self.update_session(bot_msg="Please select a court.")

    def ask_message_type(self):
        self.send_interactive_buttons(
            "How would you like to provide the update?",
            [
                {"id": "type",   "title": "Type Message"},
                {"id": "record", "title": "Record Message"}
            ]
        )
        self.update_session(bot_msg="How would you like to provide the update?")

    def ask_anything_more(self):
        self.send_interactive_buttons(
            "Anything more or end?",
            [
                {"id": "more", "title": "More"},
                {"id": "end",  "title": "End"}
            ]
        )
        self.update_session(bot_msg="Anything more or end?")

    def download_whatsapp_media(self, media_id: str):
        try:
            url = f"https://graph.facebook.com/v16.0/{media_id}"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                return None
            media_url = r.json().get("url")
            if not media_url:
                return None
            response = requests.get(media_url, headers=headers, stream=True)
            return response
        except Exception as e:
            logger.error(f"download_whatsapp_media ERROR: {e}\n{traceback.format_exc()}")
            return None

    def handle_incoming_audio_message(self, media_content, session_data):
        try:
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{self.incoming_user_number}_{timestamp_str}_audio.ogg"

            temp_dir = os.path.join(os.getcwd(), "temp_audio")
            os.makedirs(temp_dir, exist_ok=True)
            temp_audio_path = os.path.join(temp_dir, file_name)

            media_content.raise_for_status()
            with open(temp_audio_path, "wb") as f:
                for chunk in media_content.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = os.path.getsize(temp_audio_path)
            if file_size < 500:
                os.remove(temp_audio_path)
                return -1

            audio_seg = AudioSegment.from_file(temp_audio_path, format="ogg")
            length_ms = len(audio_seg)
            length_seconds = length_ms / 1000.0

            if 3 <= length_seconds <= 90:
                process_audio_async.delay(
                    self.incoming_user_number,
                    temp_audio_path,
                    session_data.get("selected_court")
                )
            return length_seconds
        except Exception as e:
            logger.error(f"handle_incoming_audio_message ERROR: {e}\n{traceback.format_exc()}")
            return -1

    def get_state_district_court_list(self, state=None, district=None):
        db = self.get_mongo_client_db()
        # if not db:
        #     return {}

        try:
            if state and not district:
                query = {"state_name": state}
                distinct_districts = db['state_district_court_data'].distinct("district_name", filter=query)
                distinct_districts.sort()
                # Wrap into objects for consistency:
                return {"districts": [{"id": idx, "name": d} for idx, d in enumerate(distinct_districts, start=1)]}
            if state and district:
                query = {"state_name": state, "district_name": district}
                distinct_courts = db['state_district_court_data'].distinct("court_name", filter=query)
                distinct_courts.sort()
                return {"courts": [{"id": idx, "name": c} for idx, c in enumerate(distinct_courts, start=1)]}
            distinct_states = db['state_district_court_data'].distinct("state_name")
            distinct_states.sort()
            return {"states": [{"id": idx, "name": s} for idx, s in enumerate(distinct_states, start=1)]}
        except Exception as e:
            logger.error(f"get_state_district_court_list ERROR: {e}\n{traceback.format_exc()}")
            return {}

    def prompt_select_state(self):
        data = self.get_state_district_court_list()
        all_states = data.get("states", [])
        if not all_states:
            self.send_text_message("No states found in the database. Please try again later.")
            return
        lines = ["Please select your State by copying EXACTLY one of the following:"]
        for st in all_states:
            lines.append(f"- {st}")
        self.send_text_message("\n".join(lines))
    
    def prompt_select_state_v2(self):
        data = self.get_state_district_court_list()
        all_states = data.get("states", [])

        if not all_states:
            self.send_text_message("No states found in the database.")
            return

        # Build list items: each state is {"id": state_name, "title": state_name}
        items = [{"id": st, "title": st} for st in all_states]

        # If it's up to 100 states, let's show an interactive list
        if len(items) <= 100:
            self.send_interactive_list(
                header_text="Select Your State",
                body_text="Please choose a state:",
                items=items
            )
        else:
            # If for some reason you have >100 states, fallback to manual text or 
            # do multi-page approach. For simplicity:
            self.send_text_message("Too many states to show interactively. Please type the state name.")


    def prompt_select_district(self, selected_state: str):
        data = self.get_state_district_court_list(state=selected_state)
        districts = data.get("districts", [])
        if not districts:
            self.send_text_message("No districts found for this state. Try another or contact support.")
            return

        lines = [
            f"State: {selected_state}",
            "Now select your District (copy EXACTLY):"
        ]
        for d in districts:
            lines.append(f"- {d}")
        self.send_text_message("\n".join(lines))

    def prompt_select_district_v2(self, selected_state: str):
        data = self.get_state_district_court_list(state=selected_state)
        districts = data.get("districts", [])
        if not districts:
            self.send_text_message("No districts for that state.")
            return

        items = [{"id": d, "title": d} for d in districts]

        if len(items) <= 100:
            self.send_interactive_list(
                header_text="Select District",
                body_text=f"State: {selected_state}",
                items=items
            )
        else:
            self.send_text_message("Too many districts. Please type it out or refine your choice.")


    def prompt_select_court(self, selected_state: str, selected_district: str):
        data = self.get_state_district_court_list(state=selected_state, district=selected_district)
        courts = data.get("courts", [])
        if not courts:
            self.send_text_message("No courts found for this district. Try another or contact support.")
            return

        lines = [
            f"State: {selected_state}",
            f"District: {selected_district}",
            "Now select your Court (copy EXACTLY):"
        ]
        for c in courts:
            lines.append(f"- {c}")
        self.send_text_message("\n".join(lines))

    def prompt_select_court_v2(self, selected_state: str, selected_district: str):
        data = self.get_state_district_court_list(state=selected_state, district=selected_district)
        courts = data.get("courts", [])
        if not courts:
            self.send_text_message("No courts found for that district.")
            return

        items = [{"id": c, "title": c} for c in courts]

        if len(items) <= 100:
            self.send_interactive_list(
                header_text="Select Court",
                body_text=f"State: {selected_state} | District: {selected_district}",
                items=items
            )
        else:
            self.send_text_message("Too many courts. Please type it manually.")

    def update_user_default_court(self, phone_number: str, new_court: str):
        db = self.get_mongo_client_db()
        # if not db:
        #     return

        user_id = self._user_details.get("user_id")
        if not user_id:
            return

        try:
            db["user_details"].update_one(
                {"user_id": user_id},
                {"$set": {"default_court": new_court}}
            )
            self._user_details["default_court"] = new_court
        except Exception as e:
            logger.error(f"update_user_default_court ERROR: {e}\n{traceback.format_exc()}")

    def prompt_select_state_with_keys(self):
        """Send the user a list of states with an assigned 2-digit key (e.g., S1, S2)."""
        data = self.get_state_district_court_list()
        all_states = data.get("states", [])
        logger.info(f"Enumerating states: {[s['name'] for s in all_states]}")
        if not all_states:
            self.send_text_message("No states found in the database. Please try again later.")
            return

        mapping = {}
        message_lines = ["Please select your State by replying with the assigned id:"]
        for idx, state_obj in enumerate(all_states, start=1):
            assigned_id = f"S{idx}"
            state_data = {
                "state_id": state_obj["id"],
                "state_name": state_obj["name"],
                "state_platform_assigned_id": assigned_id
            }
            mapping[assigned_id] = state_data
            message_lines.append(f"{assigned_id}: {state_obj['name']}")

        self.send_text_message("\n".join(message_lines))
        db = self.get_mongo_client_db()
        db["whatsapp_chat_sessions"].update_one(
            {"phone_number": self.incoming_user_number, "active": True},
            {"$set": {"state_mapping": mapping, "state": "awaiting_state_key_selection"}}
        )
        logger.info(f"mapping keys: {list(mapping.keys())}")

    def handle_state_key_selection(self, user_input: str):
        """Process the user's state key and ask for confirmation."""
        db = self.get_mongo_client_db()
        sess = db["whatsapp_chat_sessions"].find_one({
            "phone_number": self.incoming_user_number, "active": True})
        mapping = sess.get("state_mapping", {})
        selected_state = mapping.get(user_input.strip())
        if not selected_state:
            self.send_text_message("Invalid selection. Please try again.")
            self.prompt_select_state_with_keys()
            return

        self.send_interactive_buttons(
            f"You selected: {selected_state['state_name']}. Is that correct?",
            [
                {"id": "keep_state", "title": "Keep"},
                {"id": "change_state", "title": "Change"}
            ]
        )
        db["whatsapp_chat_sessions"].update_one(
            {"phone_number": self.incoming_user_number, "active": True},
            {"$set": {"temp_selected_state": selected_state, "state": "awaiting_state_confirmation"}}
        )

    def handle_state_confirmation(self, user_input: str):
        """Confirm or re-prompt the state selection based on user input."""
        db = self.get_mongo_client_db()
        sess = db["whatsapp_chat_sessions"].find_one({
            "phone_number": self.incoming_user_number, "active": True})
        if user_input.lower() in ["keep", "keep_state"]:
            final_state = sess.get("temp_selected_state")
            db["whatsapp_chat_sessions"].update_one(
                {"phone_number": self.incoming_user_number, "active": True},
                {"$set": {"selected_state": final_state["state_name"],
                          "state": "awaiting_district_selection"},
                 "$unset": {"state_mapping": "", "temp_selected_state": ""}}
            )
            self.send_text_message(f"State {final_state['state_name']} confirmed. Now selecting district.")
            self.prompt_select_district_with_keys(final_state["state_name"])
        elif user_input.lower() in ["change", "change_state"]:
            self.prompt_select_state_with_keys()
        else:
            self.send_text_message("Invalid response. Please reply with 'Keep' or 'Change'.")

    def prompt_select_district_with_keys(self, selected_state: str):
        """Send the user a list of districts (for the given state) with an assigned key (e.g., D1, D2)."""
        data = self.get_state_district_court_list(state=selected_state)
        districts = data.get("districts", [])
        if not districts:
            self.send_text_message("No districts found for the selected state. Please try again later.")
            return

        mapping = {}
        message_lines = [f"Selected State: {selected_state}\nPlease select your District by replying with the assigned id:"]
        for idx, district_obj in enumerate(districts, start=1):
            assigned_id = f"D{idx}"
            district_data = {
                "district_id": district_obj["id"],
                "district_name": district_obj["name"],
                "district_platform_assigned_id": assigned_id
            }
            mapping[assigned_id] = district_data
            message_lines.append(f"{assigned_id}: {district_obj['name']}")

        self.send_text_message("\n".join(message_lines))
        db = self.get_mongo_client_db()
        db["whatsapp_chat_sessions"].update_one(
            {"phone_number": self.incoming_user_number, "active": True},
            {"$set": {"district_mapping": mapping, "state": "awaiting_district_key_selection"}}
        )

    def handle_district_key_selection(self, user_input: str):
        """Process the user's district key and ask for confirmation."""
        db = self.get_mongo_client_db()
        sess = db["whatsapp_chat_sessions"].find_one({
            "phone_number": self.incoming_user_number, "active": True})
        mapping = sess.get("district_mapping", {})
        selected_district = mapping.get(user_input.strip())
        if not selected_district:
            self.send_text_message("Invalid selection. Please try again.")
            self.prompt_select_district_with_keys(sess.get("selected_state"))
            return

        self.send_interactive_buttons(
            f"You selected: {selected_district['district_name']}. Is that correct?",
            [
                {"id": "keep_district", "title": "Keep"},
                {"id": "change_district", "title": "Change"}
            ]
        )
        db["whatsapp_chat_sessions"].update_one(
            {"phone_number": self.incoming_user_number, "active": True},
            {"$set": {"temp_selected_district": selected_district, "state": "awaiting_district_confirmation"}}
        )

    def handle_district_confirmation(self, user_input: str):
        """Confirm or re-prompt the district selection based on user input."""
        db = self.get_mongo_client_db()
        sess = db["whatsapp_chat_sessions"].find_one({
            "phone_number": self.incoming_user_number, "active": True})
        if user_input.lower() in ["keep", "keep_district"]:
            final_district = sess.get("temp_selected_district")
            db["whatsapp_chat_sessions"].update_one(
                {"phone_number": self.incoming_user_number, "active": True},
                {"$set": {"selected_district": final_district["district_name"],
                          "state": "awaiting_court_selection"},
                 "$unset": {"district_mapping": "", "temp_selected_district": ""}}
            )
            self.send_text_message(f"District {final_district['district_name']} confirmed. Now selecting court.")
            self.prompt_select_court_with_keys(sess.get("selected_state"), final_district["district_name"])
        elif user_input.lower() in ["change", "change_district"]:
            self.prompt_select_district_with_keys(sess.get("selected_state"))
        else:
            self.send_text_message("Invalid response. Please reply with 'Keep' or 'Change'.")

    def prompt_select_court_with_keys(self, selected_state: str, selected_district: str):
        """Send the user a list of courts (for the given state and district) with an assigned key (e.g., C1, C2)."""
        data = self.get_state_district_court_list(state=selected_state, district=selected_district)
        courts = data.get("courts", [])
        if not courts:
            self.send_text_message("No courts found for the selected district. Please try again later.")
            return

        mapping = {}
        message_lines = [f"Selected District: {selected_district}\nPlease select your Court by replying with the assigned id:"]
        for idx, court_obj in enumerate(courts, start=1):
            assigned_id = f"C{idx}"
            court_data = {
                "court_id": court_obj["id"],
                "court_name": court_obj["name"],
                "court_platform_assigned_id": assigned_id
            }
            mapping[assigned_id] = court_data
            message_lines.append(f"{assigned_id}: {court_obj['name']}")

        self.send_text_message("\n".join(message_lines))
        db = self.get_mongo_client_db()
        db["whatsapp_chat_sessions"].update_one(
            {"phone_number": self.incoming_user_number, "active": True},
            {"$set": {"court_mapping": mapping, "state": "awaiting_court_key_selection"}}
        )

    def handle_court_key_selection(self, user_input: str):
        """Process the user's court key and ask for confirmation."""
        db = self.get_mongo_client_db()
        sess = db["whatsapp_chat_sessions"].find_one({
            "phone_number": self.incoming_user_number, "active": True})
        mapping = sess.get("court_mapping", {})
        selected_court = mapping.get(user_input.strip())
        if not selected_court:
            self.send_text_message("Invalid selection. Please try again.")
            self.prompt_select_court_with_keys(sess.get("selected_state"), sess.get("selected_district"))
            return

        self.send_interactive_buttons(
            f"You selected: {selected_court['court_name']}. Is that correct?",
            [
                {"id": "keep_court", "title": "Keep"},
                {"id": "change_court", "title": "Change"}
            ]
        )
        db["whatsapp_chat_sessions"].update_one(
            {"phone_number": self.incoming_user_number, "active": True},
            {"$set": {"temp_selected_court": selected_court, "state": "awaiting_court_confirmation"}}
        )

    def handle_court_confirmation(self, user_input: str):
        """Confirm or re-prompt the court selection based on user input."""
        db = self.get_mongo_client_db()
        sess = db["whatsapp_chat_sessions"].find_one({
            "phone_number": self.incoming_user_number, "active": True})
        if user_input.lower() in ["keep", "keep_court"]:
            final_court = sess.get("temp_selected_court")
            db["whatsapp_chat_sessions"].update_one(
                {"phone_number": self.incoming_user_number, "active": True},
                {"$set": {"selected_court": final_court["court_name"],
                          "state": "awaiting_message_type"},
                 "$unset": {"court_mapping": "", "temp_selected_court": ""}}
            )
            self.send_text_message(f"Court {final_court['court_name']} confirmed. Proceeding with your update.")
            # Continue with the usual flow (for example, ask for message type)
            # self.ask_message_type()
            self.update_session(bot_msg="How would you like to provide the update?")
        elif user_input.lower() in ["change", "change_court"]:
            self.prompt_select_court_with_keys(sess.get("selected_state"), sess.get("selected_district"))
        else:
            self.send_text_message("Invalid response. Please reply with 'Keep' or 'Change'.")

    def ask_additional_instructions(self):
        """Ask if user wants to provide instructions via text/audio or skip."""
        self.send_interactive_buttons(
            "Would you like to provide additional instructions?",
            [
                {"id": "type",   "title": "Type"},
                {"id": "record", "title": "Record"},
                {"id": "skip",   "title": "Skip"}
            ]
        )

    def handle_instructions_text(self, instructions: str):
        """Store text instructions in session so we can put them in the order."""
        db = self.get_mongo_client_db()
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        db["whatsapp_chat_sessions"].update_one(
            {"phone_number": self.incoming_user_number, "active": True},
            {
                "$set": {"user_instructions": instructions},
                "$push": {
                    "messages": {
                        "sender": "user",
                        "text": f"Instructions: {instructions}",
                        "time": now_utc
                    }
                }
            }
        )

