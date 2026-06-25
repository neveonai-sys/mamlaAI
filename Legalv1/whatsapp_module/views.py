import datetime
import hashlib
import hmac
import json
import logging
import os
import re
import time
from bson import ObjectId
import traceback
import requests

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from whatsapp_module.routes.handlewhatsappmessage import Whatsappmessageformulation
from core.init_clients import get_mongo_client, get_mongo_db

logger = logging.getLogger('django')

ALLOWED_MESSAGE_TYPES = ["text", "interactive", "audio"]


def get_mongo_client_db():
    mongo = get_mongo_client()
    if not mongo:
        return None
    return get_mongo_db()


def verify_request_signature(request):
    signature = request.META.get("HTTP_X_HUB_SIGNATURE_256")
    if not signature:
        logger.warning("No signature header found. Returning 403.")
        return False
    try:
        sha_name, signature_value = signature.split("=", 1)
    except ValueError:
        logger.warning("Malformed signature header. Returning 403.")
        return False

    if sha_name != "sha256":
        logger.warning("Unsupported signature method. Returning 403.")
        return False

    mac = hmac.new(os.getenv("APP_SECRET").encode("utf-8"), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, signature_value):
        logger.warning("Signature mismatch. Returning 403.")
        return False
    return True


def validate_whatsapp_payload(data):
    if "entry" not in data or not isinstance(data["entry"], list):
        return False
    if not data["entry"]:
        return False
    entry = data["entry"][0]
    if "changes" not in entry or not isinstance(entry["changes"], list):
        return False
    if not entry["changes"]:
        return False
    change = entry["changes"][0]
    if "value" not in change or not isinstance(change["value"], dict):
        return False
    return True


@csrf_exempt
@api_view(["GET", "POST"])
def whatsapp_webhook(request):
    # 1) Verification handshake (GET)
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == os.getenv("VERIFY_TOKEN"):
                logger.info("WEBHOOK_VERIFIED")
                return HttpResponse(challenge, status=200)
            else:
                logger.info("VERIFICATION_FAILED")
                return JsonResponse({"status": "error", "message": "Verification failed"}, status=403)
        else:
            logger.info("MISSING_PARAMETER")
            return JsonResponse({"status": "error", "message": "Missing parameters"}, status=400)

    # 2) Incoming messages/notifications (POST)
    if request.method == "POST":
        if not verify_request_signature(request):
            return HttpResponse("Invalid signature", status=403)

        try:
            data = json.loads(request.body.decode("utf-8"))
            logger.info(f"Incoming webhook data: {data}")
        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON", status=400)

        if not validate_whatsapp_payload(data):
            return HttpResponse("Invalid payload structure", status=400)

        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes.get("value", {})

        # If it's only a 'statuses' update, just ACK
        if value.get("statuses"):
            return HttpResponse("Status update received", status=200)

        messages = value.get("messages", [])
        contacts = value.get("contacts", [{}])
        phone_number = contacts[0].get("wa_id")

        if not phone_number:
            return HttpResponse("No phone number found", status=400)

        # Initialize the handler
        obj = Whatsappmessageformulation(phone_number)
        user_info = obj.get_user_details()

        if not user_info:
            obj.send_text_message("Please signup in our application to explore this functionality. Regards, MamlaAI")
            return HttpResponse("User not found", status=200)

        if not obj.rate_limit_check():
            return HttpResponse("Too many requests, please slow down.", status=429)

        if obj.check_session_timeout():
            obj.send_text_message("Session expired. Please say hi or hello to start over.")
            obj.end_session("timeout")
            return HttpResponse("OK", status=200)

        session = obj.get_session()
        if not messages:
            return HttpResponse("No messages to process", status=200)

        msg = messages[0]
        message_type = msg.get("type")
        if message_type not in ALLOWED_MESSAGE_TYPES:
            return HttpResponse("Message type not allowed", status=400)

        user_text = ""
        user_choice = ""

        # Extract user input
        if message_type == "text":
            user_text = obj.sanitize_input(msg["text"]["body"])
        elif message_type == "interactive":
            i_type = msg["interactive"]["type"]
            if i_type == "button_reply":
                user_choice = obj.sanitize_input(msg["interactive"]["button_reply"]["id"])
            elif i_type == "list_reply":
                user_choice = obj.sanitize_input(msg["interactive"]["list_reply"]["id"])
            else:
                return HttpResponse("Unsupported interactive type", status=400)
        elif message_type == "audio":
            audio_info = msg.get("audio", {})
            media_id = audio_info.get("id")
            if not media_id:
                obj.send_text_message("Invalid audio message. No media_id found.")
                return HttpResponse("OK", status=200)

            db = get_mongo_client_db()
            message_id = msg.get("id")
            already = db["whatsapp_chat_sessions"].find_one({
                "phone_number": phone_number,
                "processed_message_ids": message_id
            })
            if already:
                logger.info(f"Ignoring already processed audio message {message_id}")
                return HttpResponse("OK", status=200)
            db["whatsapp_chat_sessions"].update_one(
                {"phone_number": phone_number, "active": True},
                {"$addToSet": {"processed_message_ids": message_id}}
            )

        user_input = user_choice or user_text

        # If no active session
        if not session:
            if user_input.lower() in ["hi", "hello"]:
                obj.start_session()
                obj.update_session(user_msg=user_input)

                # Based on user_type
                if user_info.get("user_type") == "Paralegal":
                    obj.greet_user_as_per_usertype("Paralegal")
                    get_mongo_client_db()["whatsapp_chat_sessions"].update_one(
                        {"phone_number": phone_number, "active": True},
                        {"$set": {"state": "awaiting_update_topic"}}
                    )
                else:
                    # Non-paralegal
                    obj.send_interactive_buttons(
                        "What would you like to do?",
                        [
                            {"id": "created", "title": "Today Tasks"},
                            {"id": "new",     "title": "New Task"}
                        ]
                    )
                    get_mongo_client_db()["whatsapp_chat_sessions"].update_one(
                        {"phone_number": phone_number, "active": True},
                        {"$set": {"state": "awaiting_non_paralegal_service_choice"}}
                    )
                return HttpResponse("OK", status=200)
            else:
                # Not hi/hello
                obj.send_text_message("Please start by saying 'hi' or 'hello'.")
                return HttpResponse("OK", status=200)

        # There is an active session
        s = obj.get_session()
        state = s.get("state")
        user_type = user_info.get("user_type")
        court_list = user_info.get("court_list", [])

        # If user typed 'end' or 'exit'
        if user_input.lower() in ["end", "exit"]:
            obj.send_text_message("Thank you. Goodbye.")
            obj.end_session("user_end")
            return HttpResponse("OK", status=200)

        # Paralegal accept/ignore
        accept_match = re.match(r"^accept\s+([0-9a-f]{5,})$", user_input, re.IGNORECASE)
        ignore_match = re.match(r"^ignore\s+([0-9a-f]{5,})$", user_input, re.IGNORECASE)
        if accept_match:
            order_id = accept_match.group(1)
            assigned = handle_paralegal_accept_order(order_id, phone_number)
            if assigned:
                obj.send_text_message(f"Order {order_id} assigned to you successfully.")
            else:
                obj.send_text_message(f"Order {order_id} is either invalid or already taken.")
            return HttpResponse("OK", status=200)
        if ignore_match:
            order_id = ignore_match.group(1)
            obj.send_text_message(f"You chose to ignore order {order_id}.")
            return HttpResponse("OK", status=200)

        logger.info(f"STATE: {state} | user_input: {user_input} | user_type: {user_type}")
        obj.update_session(user_msg=user_input)

        # --------------------------
        # KEY-BASED Court selection
        # --------------------------
        if state == "awaiting_state_key_selection":
            obj.handle_state_key_selection(user_input)
            return HttpResponse("OK", status=200)

        elif state == "awaiting_state_confirmation":
            obj.handle_state_confirmation(user_input)
            return HttpResponse("OK", status=200)

        elif state == "awaiting_district_key_selection":
            obj.handle_district_key_selection(user_input)
            return HttpResponse("OK", status=200)

        elif state == "awaiting_district_confirmation":
            obj.handle_district_confirmation(user_input)
            return HttpResponse("OK", status=200)

        elif state == "awaiting_court_key_selection":
            obj.handle_court_key_selection(user_input)
            return HttpResponse("OK", status=200)

        elif state == "awaiting_court_confirmation":
            # non-paralegal continuity
            obj.handle_court_confirmation(user_input)
            s2 = obj.get_session()
            new_state = s2.get("state")
            if user_type != "Paralegal" and s2.get("role") is None and new_state not in [
                "awaiting_court_key_selection",
                "awaiting_state_key_selection",
                "awaiting_district_key_selection"
            ]:
                chosen_court = s2.get("selected_court", "")
                # Only if the user specifically came from "no" default usage do we prompt them
                # But you can ask them unconditionally if you'd like:
                obj.send_interactive_buttons(
                    f"You selected '{chosen_court}'. Update your default court to this one?",
                    [
                        {"id": "yes_update_default", "title": "Yes"},
                        {"id": "no_keep_old",        "title": "No"}
                    ]
                )
                get_mongo_client_db()["whatsapp_chat_sessions"].update_one(
                    {"phone_number": phone_number, "active": True},
                    {"$set": {"state": "awaiting_decision_new_default"}}
                )
            return HttpResponse("OK", status=200)

        elif state == "awaiting_decision_new_default":
            # user picks "yes_update_default" or "no_keep_old"
            chosen_court = s.get("selected_court", "")
            if user_input.lower() in ["yes_update_default", "yes"]:
                if chosen_court:
                    obj.update_user_default_court(phone_number, chosen_court)
                    obj.send_text_message(f"Your default court is now '{chosen_court}'.")
                else:
                    obj.send_text_message("No valid court to set as default.")
            elif user_input.lower() in ["no_keep_old", "no"]:
                obj.send_text_message("Keeping your old default court.")
            else:
                obj.send_text_message("Invalid choice. Please select Yes or No.")
                return HttpResponse("OK", status=200)

            # Now that we've handled default court updating, we proceed to the next step
            # => ask them how they'd like to provide the main query
            get_mongo_client_db()["whatsapp_chat_sessions"].update_one(
                {"phone_number": phone_number, "active": True},
                {"$set": {"state": "awaiting_query_method"}}
            )
            obj.send_interactive_buttons(
                "How would you like to provide your query?",
                [
                    {"id": "type",   "title": "Type Message"},
                    {"id": "record", "title": "Audio Message"}
                ]
            )
            # obj.ask_message_type()
            return HttpResponse("OK", status=200)

        # ------------------------------------------------------------------
        #  Non-Paralegal Flow 
        # ------------------------------------------------------------------
        if user_type != "Paralegal":

            # 1) Service choice: "Today's Created Tasks" or "Create New Task"
            if state == "awaiting_non_paralegal_service_choice":
                if user_input.lower() == "created":
                    # Show tasks created by them today
                    today_start = datetime.datetime.now(datetime.timezone.utc).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    db = get_mongo_client_db()
                    created_orders = list(db['service_orders'].find({
                        "client_phone": phone_number,
                        "created_at": {"$gte": today_start},
                        "status": {"$ne": "deleted"}  # Exclude deleted
                    }))

                    if not created_orders:
                        obj.send_text_message("No tasks found that you created today.")
                        obj.send_text_message("Thank you. Goodbye.")
                        obj.end_session("non_paralegal_viewed_tasks")
                        return HttpResponse("OK", status=200)
                    else:
                        lines = ["Your tasks created today:"]
                        for i, od in enumerate(created_orders, start=1):
                            lines.append(f"{i}) Order {od['order_id']} | Court: {od.get('court','N/A')} | Query: {od.get('query','N/A')}")
                        lines.append("If you want to delete any, type delete-<ORDERID>, e.g. delete-ABC123")
                        lines.append("Otherwise, type 'end' to finish.")
                        obj.send_text_message("\n".join(lines))

                        valid_ids = [o["order_id"] for o in created_orders]
                        db["whatsapp_chat_sessions"].update_one(
                            {"phone_number": phone_number, "active": True},
                            {
                                "$set": {
                                    "state": "awaiting_non_paralegal_delete_command",
                                    "todays_created_orders": valid_ids
                                }
                            }
                        )
                    return HttpResponse("OK", status=200)

                elif user_input.lower() == "new":
                    obj.send_interactive_buttons(
                        "Please choose the type of task:",
                        [
                            {"id": "case",          "title": "Case Update"},
                            {"id": "certifiedcopy", "title": "Certified Copy"}
                        ]
                    )
                    get_mongo_client_db()["whatsapp_chat_sessions"].update_one(
                        {"phone_number": phone_number, "active": True},
                        {"$set": {"state": "awaiting_non_paralegal_new_task_type"}}
                    )
                    return HttpResponse("OK", status=200)

                else:
                    obj.send_text_message("Invalid choice. Please select 'created' or 'new'.")
                    return HttpResponse("OK", status=200)

            # 2) Deletion Flow
            elif state == "awaiting_non_paralegal_delete_command":
                if user_input.lower().startswith("delete-"):
                    parts = user_input.split("-", 1)
                    if len(parts) != 2:
                        obj.send_text_message("Invalid format. Type delete-<ORDERID>, e.g. delete-ABC123.")
                        return HttpResponse("OK", status=200)
                    order_id_to_delete = parts[1].strip()
                    valid_list = s.get("todays_created_orders", [])
                    if order_id_to_delete not in valid_list:
                        obj.send_text_message("Invalid order ID or not in today's tasks.")
                        obj.send_text_message("Type 'end' to finish or delete-<ORDERID> again.")
                        return HttpResponse("OK", status=200)

                    obj.send_interactive_buttons(
                        f"Are you sure you want to delete order {order_id_to_delete}?",
                        [
                            {"id": "confirm_delete", "title": "Yes"},
                            {"id": "cancel_delete",  "title": "No"}
                        ]
                    )
                    get_mongo_client_db()["whatsapp_chat_sessions"].update_one(
                        {"phone_number": phone_number, "active": True},
                        {
                            "$set": {
                                "state": "awaiting_non_paralegal_delete_confirm",
                                "delete_target_order_id": order_id_to_delete
                            }
                        }
                    )
                    return HttpResponse("OK", status=200)

                elif user_input.lower() == "end":
                    obj.send_text_message("Thank you. Goodbye.")
                    obj.end_session("non_paralegal_viewed_tasks_end")
                    return HttpResponse("OK", status=200)

                else:
                    obj.send_text_message("Invalid input. Type delete-<ORDERID> or 'end'.")
                    return HttpResponse("OK", status=200)

            elif state == "awaiting_non_paralegal_delete_confirm":
                if user_input.lower() in ["yes", "confirm_delete"]:
                    target_id = s.get("delete_target_order_id")
                    if target_id:
                        db = get_mongo_client_db()
                        db["service_orders"].update_one(
                            {"order_id": target_id},
                            {"$set": {"status": "deleted"}}
                        )
                        obj.send_text_message(f"Order {target_id} has been deleted.")
                    else:
                        obj.send_text_message("No valid order in session to delete.")

                    obj.end_session("non_paralegal_deleted_task")
                    return HttpResponse("OK", status=200)

                elif user_input.lower() in ["no", "cancel_delete"]:
                    obj.send_text_message("Okay, not deleting.")
                    obj.end_session("non_paralegal_cancel_delete")
                    return HttpResponse("OK", status=200)
                else:
                    obj.send_text_message("Please choose Yes or No for deletion.")
                    return HttpResponse("OK", status=200)

            # 3) "Create New Task" → "Case" vs "Certified Copy"
            elif state == "awaiting_non_paralegal_new_task_type":
                if user_input.lower() == "certifiedcopy":
                    obj.send_text_message("Feature for Certified Copy is under development. Goodbye.")
                    obj.end_session("non_paralegal_certcopy_not_ready")
                    return HttpResponse("OK", status=200)
                elif user_input.lower() == "case":
                    default_court = user_info.get('default_court')
                    if default_court:
                        obj.send_interactive_buttons(
                            f"You have a default court: {default_court}.\nUse it?",
                            [
                                {"id": "use_default_court_yes", "title": "Yes"},
                                {"id": "use_default_court_no",  "title": "No"}
                            ]
                        )
                        get_mongo_client_db()["whatsapp_chat_sessions"].update_one(
                            {"phone_number": phone_number, "active": True},
                            {"$set": {"state": "awaiting_use_default_court_decision"}}
                        )
                    else:
                        obj.prompt_select_state_with_keys()
                        get_mongo_client_db()["whatsapp_chat_sessions"].update_one(
                            {"phone_number": phone_number, "active": True},
                            {"$set": {"state": "awaiting_state_key_selection"}}
                        )
                    return HttpResponse("OK", status=200)
                else:
                    obj.send_text_message("Invalid choice. Please select 'case' or 'certifiedcopy'.")
                    return HttpResponse("OK", status=200)

            elif state == "awaiting_use_default_court_decision":
                if user_input.lower() in ["yes", "use_default_court_yes"]:
                    db = get_mongo_client_db()
                    db["whatsapp_chat_sessions"].update_one(
                        {"phone_number": phone_number, "active": True},
                        {
                            "$set": {
                                "selected_court": user_info["default_court"],
                                "state": "awaiting_query_method"
                            }
                        }
                    )
                    obj.send_interactive_buttons(
                        "How would you like to provide your main update?",
                        [
                            {"id": "type",   "title": "Type Message"},
                            {"id": "record", "title": "Audio Message"}
                        ]
                    )
                    # obj.ask_message_type()
                elif user_input.lower() in ["no", "use_default_court_no"]:
                    obj.prompt_select_state_with_keys()
                    db = get_mongo_client_db()
                    db["whatsapp_chat_sessions"].update_one(
                        {"phone_number": phone_number, "active": True},
                        {"$set": {"state": "awaiting_state_key_selection"}}
                    )
                else:
                    obj.send_text_message("Invalid choice. Please select Yes or No.")
                return HttpResponse("OK", status=200)

            # After court is confirmed, we set `awaiting_query_method`.
            elif state == "awaiting_query_method":
                # user picks "type" or "record"
                if user_input.lower() in ["type", "record"]:
                    db = get_mongo_client_db()
                    db["whatsapp_chat_sessions"].update_one(
                        {"phone_number": phone_number, "active": True},
                        {
                            "$set": {
                                "state": "awaiting_query_content",
                                "query_input_type": user_input.lower()
                            }
                        }
                    )
                    obj.send_text_message("Please provide your main query now.")
                else:
                    obj.send_text_message("Invalid choice. Please select 'type' or 'record'.")
                return HttpResponse("OK", status=200)

            elif state == "awaiting_query_content":
                """
                The user is providing the main query. After we get it, 
                we prompt "Save or Edit?"
                """
                db = get_mongo_client_db()
                method = s.get("query_input_type")

                if method == "type":
                    if message_type == "text":
                        db["whatsapp_chat_sessions"].update_one(
                            {"phone_number": phone_number, "active": True},
                            {"$set": {"user_query": user_input}}
                        )
                        # Ask "Save or Edit"
                        obj.send_interactive_buttons(
                            "Got it. Save this task or edit your update?",
                            [
                                {"id": "save_task", "title": "Save"},
                                {"id": "edit_task", "title": "Edit"}
                            ]
                        )
                        db["whatsapp_chat_sessions"].update_one(
                            {"phone_number": phone_number, "active": True},
                            {"$set": {"state": "awaiting_confirm_final"}}
                        )
                    else:
                        obj.send_text_message("Please type your update, not audio.")
                elif method == "record":
                    if message_type == "audio":
                        media_info = msg["audio"]
                        media_id = media_info.get("id")
                        media_content = obj.download_whatsapp_media(media_id)
                        if not media_content:
                            obj.send_text_message("Unable to download audio. Please try again.")
                            return HttpResponse("OK", status=200)

                        length_seconds = obj.handle_incoming_audio_message(media_content, s)
                        if length_seconds == -1:
                            obj.send_text_message("Corrupt audio. Please try again.")
                        elif length_seconds < 3:
                            obj.send_text_message("Audio too short (<3s). Please record again.")
                        elif length_seconds > 90:
                            obj.send_text_message("Audio too long (>90s). Please shorten it.")
                        else:
                            db["whatsapp_chat_sessions"].update_one(
                                {"phone_number": phone_number, "active": True},
                                {"$set": {"user_query": "[Audio message attached]"}}
                            )
                            # Now "Save or Edit"
                            obj.send_interactive_buttons(
                                "Got it. Save this task or edit your update?",
                                [
                                    {"id": "save_task", "title": "Save"},
                                    {"id": "edit_task", "title": "Edit"}
                                ]
                            )
                            db["whatsapp_chat_sessions"].update_one(
                                {"phone_number": phone_number, "active": True},
                                {"$set": {"state": "awaiting_confirm_final"}}
                            )
                    else:
                        obj.send_text_message("Please record your update (audio).")
                else:
                    obj.send_text_message("Something is off with your update method. Please start over.")

                return HttpResponse("OK", status=200)

            elif state == "awaiting_confirm_final":
                """
                The user chooses 'save_task' or 'edit_task'
                """
                if user_input.lower() in ["save_task", "save"]:
                    # finalize the order in DB
                    finalize_non_paralegal_order(phone_number)
                    obj.send_text_message("Your new task has been created successfully. Thank you!")
                    obj.end_session("non_paralegal_new_task_done")

                elif user_input.lower() in ["edit_task", "edit"]:
                    # go back so they can re-provide the main query
                    db = get_mongo_client_db()
                    db["whatsapp_chat_sessions"].update_one(
                        {"phone_number": phone_number, "active": True},
                        {"$set": {"state": "awaiting_query_content"}}
                    )
                    obj.send_text_message("Please provide your main query again.")
                else:
                    obj.send_text_message("Invalid choice. Please pick 'Save' or 'Edit'.")

                return HttpResponse("OK", status=200)

            # If we haven't matched any known non-paralegal states:
            obj.send_text_message("Something went wrong or not implemented. Please say 'hi' to start over.")
            obj.end_session("unexpected_state")
            return HttpResponse("OK", status=200)

        # ------------------------------------------------------------------
        # Paralegal Flow (Unchanged)
        # ------------------------------------------------------------------
        if state == "awaiting_update_topic":
            if user_type != "Paralegal":
                obj.send_text_message("You do not have paralegal privileges. Ending session.")
                obj.end_session("not_paralegal")
                return HttpResponse("OK", status=200)

            if user_input not in ["court", "clientlawyer", "task"]:
                obj.send_text_message("Invalid choice. Please choose 'court', 'clientlawyer', or 'task'.")
                return HttpResponse("OK", status=200)

            db = get_mongo_client_db()
            db["whatsapp_chat_sessions"].update_one(
                {"phone_number": phone_number, "active": True},
                {"$set": {"role": user_input}}
            )

            if user_input == "court":
                if not court_list:
                    obj.send_text_message("No courts assigned to you. Ending session.")
                    obj.end_session(reason="no_courts")
                else:
                    obj.get_courts_for_user(court_list)
                    db["whatsapp_chat_sessions"].update_one(
                        {"phone_number": phone_number, "active": True},
                        {"$set": {"state": "awaiting_court_selection"}}
                    )
            elif user_input == "clientlawyer":
                obj.send_text_message("Feature not implemented yet. Please pick something else.")
                db["whatsapp_chat_sessions"].update_one(
                    {"phone_number": phone_number, "active": True},
                    {"$set": {"state": "awaiting_update_topic"}}
                )
            else:  # "task"
                obj.send_text_message("Do you want to check 'pending' tasks or 'completed' tasks today?")
                obj.update_session(bot_msg="Type 'pending' or 'completed'.")
                db["whatsapp_chat_sessions"].update_one(
                    {"phone_number": phone_number, "active": True},
                    {"$set": {"state": "awaiting_task_command"}}
                )
            return HttpResponse("OK", status=200)

        elif state == "awaiting_court_selection":
            selected_court = user_input
            valid_courts = court_list
            if selected_court not in valid_courts:
                obj.send_text_message("Invalid court selection. Please choose a valid court.")
                obj.get_courts_for_user(court_list)
            else:
                db = get_mongo_client_db()
                db["whatsapp_chat_sessions"].update_one(
                    {"phone_number": phone_number, "active": True},
                    {"$set": {"selected_court": selected_court, "state": "awaiting_message_type"}}
                )
                obj.ask_message_type()
            return HttpResponse("OK", status=200)

        elif state == "awaiting_message_type":
            msg_type = user_input
            if msg_type not in ["type", "record"]:
                obj.send_text_message("Invalid choice. Please choose 'type' or 'record'.")
                obj.ask_message_type()
            else:
                db = get_mongo_client_db()
                db["whatsapp_chat_sessions"].update_one(
                    {"phone_number": phone_number, "active": True},
                    {"$set": {"state": "awaiting_update_content"}}
                )
                obj.send_text_message("Please provide your update now.")
                obj.update_session(bot_msg="Please provide your update now.")
            return HttpResponse("OK", status=200)

        elif state == "awaiting_update_content":
            if user_input in ["audio_error", "invalid_audio"]:
                obj.send_text_message("Please provide a valid update.")
            else:
                db = get_mongo_client_db()
                if message_type == "text":
                    db["whatsapp_chat_sessions"].update_one(
                        {"phone_number": phone_number, "active": True},
                        {"$push": {
                            "updates": {
                                "message_type": message_type,
                                "court": s.get("selected_court"),
                                "update": user_input,
                                "time": datetime.datetime.now(datetime.timezone.utc)
                            }
                        },
                            "$set": {"state": "awaiting_more_or_end"}}
                    )
                elif message_type == "audio":
                    media_content = obj.download_whatsapp_media(media_id)
                    if not media_content:
                        obj.send_text_message("Unable to retrieve your audio message. Please try again.")
                        return HttpResponse("OK", status=200)

                    length_seconds = obj.handle_incoming_audio_message(media_content, s)
                    if length_seconds == -1:
                        obj.send_text_message("Corrupt Audio.")
                        obj.ask_anything_more()
                        return HttpResponse("OK", status=200)
                    elif length_seconds < 3:
                        obj.send_text_message("Audio is too short (<3 seconds). Please record a longer message.")
                        obj.ask_anything_more()
                        return HttpResponse("OK", status=200)
                    elif length_seconds > 90:
                        obj.send_text_message("Audio is too long (>1.5 min). Please send a shorter recording.")
                        obj.ask_anything_more()
                        return HttpResponse("OK", status=200)

                obj.ask_anything_more()
            return HttpResponse("OK", status=200)

        elif state == "awaiting_task_command":
            db = get_mongo_client_db()
            if user_input not in ["pending", "completed"]:
                obj.send_text_message("Invalid choice. Please type 'pending' or 'completed'.")
                return HttpResponse("OK", status=200)

            if user_input == "pending":
                assigned_orders = list(db['service_orders'].find({
                    "paralegal_phone": phone_number,
                    "status": "assigned"
                }))
                if not assigned_orders:
                    obj.send_text_message("You have no pending orders. Ending session.")
                    obj.end_session("no_pending_orders")
                    return HttpResponse("OK", status=200)

                lines = ["Your pending orders:"]
                for i, od in enumerate(assigned_orders, start=1):
                    lines.append(
                        f"{i}) Order {od['order_id']} | Case: {od.get('case_id', 'N/A')} | Court: {od.get('court')}"
                    )
                lines.append("Type the number of the order you'd like to update.")
                obj.send_text_message("\n".join(lines))

                db["whatsapp_chat_sessions"].update_one(
                    {"phone_number": phone_number, "active": True},
                    {
                        "$set": {
                            "pending_orders_list": [str(o["_id"]) for o in assigned_orders],
                            "state": "awaiting_task_order_selection"
                        }
                    }
                )
            else:  # completed
                today_start = datetime.datetime.now(datetime.timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                comp_orders = list(db['service_orders'].find({
                    "paralegal_phone": phone_number,
                    "status": "completed",
                    "updated_at": {"$gte": today_start}
                }))
                if not comp_orders:
                    obj.send_text_message("No completed orders for today.")
                    obj.end_session("no_completed_orders")
                    return HttpResponse("OK", status=200)

                lines = ["Your completed orders today:"]
                for i, od in enumerate(comp_orders, start=1):
                    lines.append(f"{i}) Order {od['order_id']} (Case: {od.get('case_id','N/A')})")
                lines.append("If you want to re-update any of these, type the number. Otherwise type 'end'.")
                obj.send_text_message("\n".join(lines))

                db["whatsapp_chat_sessions"].update_one(
                    {"phone_number": phone_number, "active": True},
                    {
                        "$set": {
                            "completed_orders_list": [str(o["_id"]) for o in comp_orders],
                            "state": "awaiting_completed_order_pick"
                        }
                    }
                )
            return HttpResponse("OK", status=200)

        elif state == "awaiting_task_order_selection":
            db = get_mongo_client_db()
            sess = obj.get_session()
            pending_ids = sess.get("pending_orders_list", [])

            try:
                idx = int(user_input) - 1
                if idx < 0 or idx >= len(pending_ids):
                    raise ValueError
            except ValueError:
                obj.send_text_message("Invalid choice. Please type the correct number from the list.")
                return HttpResponse("OK", status=200)

            chosen_order_db_id = pending_ids[idx]
            db["whatsapp_chat_sessions"].update_one(
                {"phone_number": phone_number, "active": True},
                {
                    "$set": {
                        "current_order_db_id": chosen_order_db_id,
                        "state": "awaiting_paralegal_update_type"
                    }
                }
            )
            obj.ask_message_type()
            return HttpResponse("OK", status=200)

        elif state == "awaiting_completed_order_pick":
            obj.send_text_message("Re-updating completed orders is not implemented. Ending session.")
            obj.end_session("completed_orders_flow_end")
            return HttpResponse("OK", status=200)

        elif state == "awaiting_paralegal_update_type":
            if user_input not in ["type", "record"]:
                obj.send_text_message("Invalid choice. Please choose 'type' or 'record'.")
                obj.ask_message_type()
                return HttpResponse("OK", status=200)

            get_mongo_client_db()["whatsapp_chat_sessions"].update_one(
                {"phone_number": phone_number, "active": True},
                {"$set": {"state": "awaiting_task_update_content"}}
            )
            obj.send_text_message("Please provide your update now (text or audio).")
            return HttpResponse("OK", status=200)

        elif state == "awaiting_task_update_content":
            db = get_mongo_client_db()
            if message_type == "text":
                finalize_paralegal_order_update(phone_number, user_input, media=None)
                obj.send_text_message("Update received and order marked as completed. Thank you!")
                obj.ask_anything_more()
                db["whatsapp_chat_sessions"].update_one(
                    {"phone_number": phone_number, "active": True},
                    {"$set": {"state": "awaiting_more_or_end"}}
                )
            elif message_type == "audio":
                media_info = msg["audio"]
                media_id = media_info.get("id")
                media_content = obj.download_whatsapp_media(media_id)
                if not media_content:
                    obj.send_text_message("Unable to download your audio. Please try again.")
                    return HttpResponse("OK", status=200)

                length_seconds = obj.handle_incoming_audio_message(media_content, s)
                if length_seconds == -1:
                    obj.send_text_message("Corrupt or invalid audio. Please try again.")
                elif length_seconds < 3:
                    obj.send_text_message("Audio too short (<3s). Please record again.")
                elif length_seconds > 90:
                    obj.send_text_message("Audio too long (>90s). Please shorten your recording.")
                else:
                    finalize_paralegal_order_update(phone_number, "Audio provided", media="some_audio_link")
                    obj.send_text_message("Update received. Order marked as completed. Thank you!")
                obj.ask_anything_more()
                db["whatsapp_chat_sessions"].update_one(
                    {"phone_number": phone_number, "active": True},
                    {"$set": {"state": "awaiting_more_or_end"}}
                )
            return HttpResponse("OK", status=200)

        elif state == "awaiting_more_or_end":
            db = get_mongo_client_db()
            if user_input == "more":
                obj.send_text_message("Please choose 'pending' or 'completed' again.")
                db["whatsapp_chat_sessions"].update_one(
                    {"phone_number": phone_number, "active": True},
                    {"$set": {"state": "awaiting_task_command"}}
                )
            elif user_input == "end":
                obj.send_text_message("Thank you. Goodbye.")
                obj.end_session("user_end")
            else:
                obj.send_text_message("Invalid choice. Type 'more' or 'end'.")
            return HttpResponse("OK", status=200)

        # Fallback
        obj.send_text_message("Something went wrong or not implemented. Please say 'hi' to start over.")
        obj.end_session("unexpected_state")
        return HttpResponse("OK", status=200)


# ---------------- HELPER FUNCTIONS -----------------

def create_new_order(client_phone: str, service_type: str, case_id: str, court: str, instructions: str = None,
                     query: str = None) -> str:
    """
    Creates a new order. 'instructions' is optional text (or note indicating audio).
    'query' is the main user query for 'case update'.
    """
    db = get_mongo_client_db()
    doc = {
        "client_phone": client_phone,
        "service_type": service_type,
        "case_id": case_id or None,
        "court": court,
        "paralegal_phone": None,
        "status": "pending",
        "updates": [],
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
    }
    if instructions:
        doc["instructions"] = instructions
    if query:
        doc["query"] = query

    # generate short 6-digit ID
    import random, string
    short_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    doc["order_id"] = short_id

    res = db['service_orders'].insert_one(doc)
    return short_id


def handle_paralegal_accept_order(order_id: str, paralegal_phone: str) -> bool:
    db = get_mongo_client_db()
    result = db['service_orders'].update_one(
        {"order_id": order_id, "status": "pending"},
        {
            "$set": {
                "paralegal_phone": paralegal_phone,
                "status": "assigned",
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
        }
    )
    return (result.modified_count == 1)


def finalize_paralegal_order_update(paralegal_phone: str, update_text: str, media: str = None):
    db = get_mongo_client_db()
    sess = db["whatsapp_chat_sessions"].find_one({"phone_number": paralegal_phone, "active": True})
    if not sess:
        return

    oid_str = sess.get("current_order_db_id")
    if not oid_str:
        return

    try:
        oid = ObjectId(oid_str)
    except:
        return

    order = db['service_orders'].find_one({"_id": oid})
    if not order:
        return

    now_time = datetime.datetime.now(datetime.timezone.utc)
    update_doc = {
        "time": now_time.isoformat(),
        "by": paralegal_phone,
        "text": update_text
    }
    if media:
        update_doc["media"] = media

    db['service_orders'].update_one(
        {"_id": oid},
        {
            "$set": {
                "status": "completed",
                "updated_at": now_time
            },
            "$push": {
                "updates": update_doc
            }
        }
    )


def finalize_non_paralegal_order(phone_number: str):
    """
    Retrieves chosen location + user_query from the session, 
    then creates the order using 'create_new_order'.
    """
    db = get_mongo_client_db()
    sess = db["whatsapp_chat_sessions"].find_one({"phone_number": phone_number, "active": True})
    if not sess:
        return

    selected_court = sess.get("selected_court") or "Unknown"
    instructions = ""  # we no longer handle instructions
    user_query = sess.get("user_query") or ""

    order_id = create_new_order(
        client_phone=phone_number,
        service_type="non_paralegal_task",
        case_id=None,
        court=selected_court,
        instructions=instructions,
        query=user_query
    )
    logger.info(f"Created new order {order_id} for user {phone_number}")
