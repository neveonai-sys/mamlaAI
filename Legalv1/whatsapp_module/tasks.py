import os
import shutil
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
import traceback
import requests
import logging
import datetime
from celery import shared_task
from pydub import AudioSegment

# from whatsapp_module.models import sessions_col
from core.init_clients import get_mongo_client, get_supabase_client

logger = logging.getLogger('django')



def get_mongo_client_db():
    mongo = get_mongo_client()
    if not mongo:
        return ''
    db = mongo['legaldb']
    return db

@shared_task(
    bind=True,
    name="process_audio_async",
    rate_limit="5/m",  # e.g., limit to 5 tasks per minute per worker
    max_retries=3      # if you want automatic retries on exceptions
)
def process_audio_async(self, phone_number, audio_path, selected_court):
    """
    Background task to analyze audio for volume, transcribe it, and check for abuse.
    If invalid, send user a 'bad audio' message and delete.
    If valid, move to /audio_dir and update DB.
    """
    try:
        # 1) Quick volume check with pydub
        audio = AudioSegment.from_file(audio_path)
        loudness_dbfs = audio.dBFS  # average loudness
        if loudness_dbfs < -50.0:
            reason = "Audio is too quiet or silent."
            return reject_audio(phone_number, audio_path, reason)

        # 2) Optional: Transcribe with OpenAI
        wav_path = audio_path.replace('.ogg', ".wav")
        logger.info(f"process_audio_async ||||||| wav_path ========>>>>> {wav_path}")
        audio.export(wav_path, format="wav")
        transcription_text = transcribe_with_openai(wav_path)
        logger.info(f"OpenAI transcription: {transcription_text}")

        # 3) Check for abusive content or banned words
        banned_words = ["dog", "fuck"]
        if any(bad in transcription_text.lower() for bad in banned_words):
            reason = "Inappropriate or abusive content found."
            return reject_audio(phone_number, audio_path, reason)

        # 4) If audio passes all checks, move to /audio_dir
        final_dir = os.path.join('../../../', "audio_input")
        os.makedirs(final_dir, exist_ok=True)

        final_audio_path = os.path.join(final_dir, os.path.basename(audio_path))
        logger.info(f"process_audio_async ||||||| final_audio_path ========>>>>> {final_audio_path}")
        shutil.move(audio_path, final_audio_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)

        # 5) Update DB with final audio path
        get_mongo_client_db()['whatsapp_chat_sessions'].update_one(
            {"phone_number": phone_number, "active": True},
            {
                "$push": {
                    "updates": {
                        "message_type": "record",
                        "court": selected_court,
                        "update": f"[Audio file saved at: {final_audio_path}]",
                        "transcription":transcription_text.lower() or '',
                        "time": datetime.datetime.now(datetime.timezone.utc)
                    }
                }
            }
        )

        # 6) Send success message
        # wpp_obj = Whatsappmessageformulation(phone_number)
        send_whatsapp_message(phone_number,"Your audio has been successfully processed.")
        logger.info(f"Audio successfully processed for {phone_number}")

    except Exception as exc:
        logger.exception(f"Error in process_audio_async: {exc}")
        reason = f"An error occurred: {str(exc)}"
        reject_audio(phone_number, audio_path, reason)

def transcribe_with_openai(wav_path):
    try:
        with open(wav_path, "rb") as audio_file:
            transcript = client.audio.transcribe("whisper-1", audio_file)
        return transcript.get("text", "")
    except Exception as e:
        return f"TranscriptionError: {str(e)}"

def reject_audio(phone_number, audio_path, reason):
    """
    Send 'bad audio' message to user, delete files, update session if needed.
    """
    logger.warning(f"Rejecting audio for {phone_number}: {reason}")
    if os.path.exists(audio_path):
        os.remove(audio_path)
    wav_path = audio_path + ".wav"
    if os.path.exists(wav_path):
        os.remove(wav_path)

    # wpp_obj = Whatsappmessageformulation(phone_number)
    send_whatsapp_message(phone_number,f"Your audio file was rejected: {reason}")
    return False

def send_whatsapp_message(phone_number, message):
    """
    Send a WhatsApp message. Return True if delivered, False if not.
    For demonstration, assume it's always successful.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "text": {"body": message}
    }
    logger.info(f"[DEBUG] Sending WhatsApp message PAYLOAD in AUDIO TASKS --> {payload}'")
    chk = request_to_whatsapp_url(payload)
    logger.info(f"[DEBUG] Sending WhatsApp message chk  in AUDIO TASKS --> {chk}'")
    if chk.status_code == 200:
        return True
    else:
        return False

def request_to_whatsapp_url(payload):
    ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
    PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
    WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    try:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        logging.info(f"send_whatsapp_message -----  in AUDIO TASKS  --->>>> {headers} == payload == {payload}")
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
        logging.info(f"WhatsApp API response: {response.status_code}, {response.text}")
        return response
    except Exception as err:
        logger.error(traceback.format_exc())
        logger.error(f"EERROR SHAREDD TASKKKK AT request_whatsapp_url USEEERRSSSS  in AUDIO TASKS ---->  {err}")


@shared_task
def assign_orders_evening():
    """
    Celery task to be run each evening:
    1) Find all 'pending' orders created today.
    2) For each order, fetch paralegals who have the same 'court' in their court_list.
    3) Send each paralegal a WhatsApp message to see if they want to accept the order.
    """
    try:
        mongo = get_mongo_client()
        if not mongo:
            return

        db = mongo['legaldb']
        today_start = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        supabase = get_supabase_client()

        pending_orders = list(db['service_orders'].find({
            "status": "pending",
            "created_at": {"$gte": today_start}
        }))

        for order in pending_orders:
            court = order.get("court")
            order_id = order.get("order_id")
            if not court or not order_id:
                continue

            paralegals_cursor = db['user_details'].find({"user_type": "Paralegal","courts": { "$in": [court] }})
            paralegals = list(paralegals_cursor)

            for pl in paralegals:
                phone_number = supabase.table("user_metadata").select("phone").eq("user_id",pl.get('user_id')).execute().data[0].get('phone')
                # phone_number = pl.get('phone_number')
                if not phone_number:
                    continue

                if not phone_number.startswith("91"):
                    phone_number = "91" + phone_number

                # wmsg = Whatsappmessageformulation(phone_number)
                # Send them a text with instructions to accept or ignore via free-text commands:
                body_text = (
                    f"New order request:\n"
                    f"OrderID: {order_id}\n"
                    f"CaseID: {order.get('case_id', 'N/A')}\n"
                    f"Court: {court}\n"
                    f"Service: {order.get('service_type', 'N/A')}\n\n"
                    f"Reply with:\n"
                    f"'accept {order_id}' to take this order\n"
                    f"'ignore {order_id}' to skip it."
                )
                # wmsg.send_text_message(body_text)
                send_whatsapp_message(phone_number,body_text)

    except Exception as e:
        logger.error("assign_orders_evening ERROR:", e)
        logger.error(traceback.format_exc())


@shared_task
def paralegal_reminder_task():
    """
    Celery task to be run every 2 hours:
    1) Find all 'assigned' orders that are NOT 'completed'.
    2) Send a reminder to the assigned paralegal to update or complete the order.
    """
    try:
        mongo = get_mongo_client()
        if not mongo:
            return
        db = mongo['legaldb']

        assigned_orders = list(db['service_orders'].find({"status": "assigned"}))
        for order in assigned_orders:
            paralegal_phone = order.get('paralegal_phone')
            if not paralegal_phone:
                continue

            if not paralegal_phone.startswith("91"):
                    paralegal_phone = "91" + paralegal_phone

            order_id = order.get('order_id')
            case_id = order.get('case_id', 'N/A')
            # wmsg = Whatsappmessageformulation(paralegal_phone)
            send_whatsapp_message(paralegal_phone,
                f"Reminder: You have an active order (ID: {order_id}, Case: {case_id}) "
                f"that is still not completed.\nPlease provide an update."
            )

    except Exception as e:
        logger.error("paralegal_reminder_task ERROR:", e)
        logger.error(traceback.format_exc())


@shared_task
def notify_clients_end_of_day():
    """
    Celery task to be run at end-of-day:
    1) Find all orders that are 'completed' *today*.
    2) Send a final summary/update back to the client who placed it.
    """
    try:
        mongo = get_mongo_client()
        if not mongo:
            return
        db = mongo['legaldb']

        today_start = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        completed_orders = list(db['service_orders'].find({
            "status": "completed",
            "updated_at": {"$gte": today_start}
        }))

        for order in completed_orders:
            client_phone = order.get('client_phone')
            if not client_phone:
                continue

            if not client_phone.startswith("91"):
                    client_phone = "91" + client_phone

            order_id = order.get('order_id')
            case_id = order.get('case_id', 'N/A')
            updates_list = order.get('updates', [])
            # Build a small summary of all updates
            # Each item might look like {"time": <datetime>, "by": <phone>, "text": "..."}
            summary_lines = []
            for idx, upd in enumerate(updates_list, start=1):
                t = upd.get("time", "")
                txt = upd.get("text", "")
                summary_lines.append(f"Update #{idx} @ {t}: {txt}")

            final_msg = (
                f"Hello! Here is the final update for your order {order_id}:\n"
                f"Case ID: {case_id}\n\n" +
                "\n".join(summary_lines) +
                "\n\nThank you for using our service!"
            )

            # wmsg = Whatsappmessageformulation(client_phone)
            send_whatsapp_message(client_phone, final_msg)

    except Exception as e:
        logger.error("notify_clients_end_of_day ERROR:", e)
        logger.error(traceback.format_exc())