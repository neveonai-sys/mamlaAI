import os
# import pymongo
import traceback
import base64
import resend
# from twilio.rest import Client as TwilioClient
import logging
# from bson.objectid import ObjectId
import requests
import re
import json
from django.conf import settings
from core.llm_client import chat_complete
# from utilities.tasks import request_to_whatsapp_url
logger = logging.getLogger('django')

class Handutilities:
    def __init__(self) -> None:
        pass

    def openai_create_data(self, raw_text):
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a legal assistant. Your task is to create a concise description of draft content in accordance with Indian laws.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Read this draft content: '''{raw_text}''' "
                        "and create a 50-word description that gives a brief overview of what this draft is about, "
                        "in the context of Indian law. Return only the description text, no extra commentary."
                    ),
                },
            ]
            assistant_content = chat_complete(
                messages=messages,
                app_scenario="utilities:describe_draft",
                temperature=0,
                max_tokens=1024,
            )
            logger.info(f"openai_create_data result: {assistant_content}")
            return assistant_content
        except Exception as err:
            logger.error(f"openai_create_data ERROR --> {err} || {traceback.format_exc()}")
            return {}
        

    def send_notification(self,user, meeting, reminder_type):
        # Email Notification
        if user.get('sendReminder') in ['Both', 'Email'] and not reminder_type == "daily_consolidated":
            self.send_notification_email(user['partyBEmail'],user['email'], meeting, reminder_type)

        elif reminder_type == "daily_consolidated":
            self.send_consolidated_notification(user, meeting)
        
        # SMS Notification ##TODO : SMS isn't implemented yet
        """
        if user.get('sendReminder') in ['Both', 'WhatsApp']:
            self.send_notification_sms(user['fname']user['phone_number'], meeting, reminder_type)
        """

    def send_notification_email(self, partyBEmail, to_email, meeting, reminder_type):
        try:
            subject = f"Reminder: Your meeting '{meeting['title']}' is coming up"
            if reminder_type == "hourly":
                subject += " in 1 hour."
                body = f"Hello ,\n\nYour meeting '{meeting['title']}' is scheduled to start at {meeting['meeting_start_date'].strftime('%Y-%m-%d %H:%M')}.\n\nBest regards,\nYour Team"
            elif reminder_type == "quarterly":
                subject += " in 15 minutes."
                body = f"Hello ,\n\nYour meeting '{meeting['title']}' is scheduled to start at {meeting['meeting_start_date'].strftime('%Y-%m-%d %H:%M')}.\n\nBest regards,\nYour Team"

            data = dict()
            data['to_emails'] = to_email
            data['cc_emails'] = partyBEmail if partyBEmail else ''
            data['subject'] = subject
            data['body'] = body
            logger.info(f"send_notification_email --> data ------> {data}")
            self.initiate_email(data)
        except Exception as e:
                # Handle email sending errors
                logger.error(f"Error send_notification_email to {to_email}: {e}")


    # def send_notification_sms(self,to_phone, meeting, reminder_type):
    #     from twilio.rest import Client as TwilioClient
    #     # Example using Twilio
    #     account_sid = 'your_twilio_account_sid'
    #     auth_token = 'your_twilio_auth_token'
    #     twilio_client = TwilioClient(account_sid, auth_token)
        
    #     if reminder_type == "hourly":
    #         message_body = f"Reminder: Your meeting '{meeting['title']}' is in 1 hour at {meeting['meeting_start_date'].strftime('%H:%M')}."
    #     elif reminder_type == "quarterly":
    #         message_body = f"Reminder: Your meeting '{meeting['title']}' is in 15 minutes at {meeting['meeting_start_date'].strftime('%H:%M')}."
        
    #     try:
    #         message = twilio_client.messages.create(
    #             body=message_body,
    #             from_='+1234567890',  # Your Twilio number
    #             to=to_phone
    #         )
    #     except Exception as e:
    #         # Handle SMS sending errors
    #         print(f"Error sending SMS to {to_phone}: {e}")

    def send_notification_sms(self, phone_number, meeting, reminder_type):
        """
        Send a WhatsApp message. Return True if delivered, False if not.
        For demonstration, assume it's always successful.
        """
        if reminder_type == "hourly":
            message_body = f"Reminder: Your meeting '{meeting['title']}' is in 1 hour at {meeting['meeting_start_date'].strftime('%H:%M')}."
        elif reminder_type == "quarterly":
            message_body = f"Reminder: Your meeting '{meeting['title']}' is in 15 minutes at {meeting['meeting_start_date'].strftime('%H:%M')}."

        payload = {
            "messaging_product": "whatsapp",
            "to": f'91{phone_number}',
            "text": {"body": message_body}
        }
        logger.info(f"[DEBUG] Sending WhatsApp message PAYLOAD --> {payload}'")
        chk = self.request_to_whatsapp_url(payload)
        logger.info(f"[DEBUG] Sending WhatsApp message chk --> {chk}'")
        if chk.status_code == 200:
            return True
        else:
            return False
        
    def request_to_whatsapp_url(self,payload):
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
            logging.info(f"WhatsApp API response in UTILS: {response.status_code}, {response.text}")
            return response
        except Exception as err:
            logger.error(traceback.format_exc())
            logger.error(f"EERROR SHAREDD TASKKKK AT request_whatsapp_url in UTILS USEEERRSSSS ---->  {err}")
            return {"error": str(err)}

    def send_consolidated_notification(self,user, meeting):
        # import smtplib
        # from email.mime.text import MIMEText
        try:
        
            subject = f"Daily Summary: Updated Meetings for Today"
            body = f"Hello,\n\nHere are your updated meetings for today:\n\n{meeting['consolidated_meetings']}\n\nBest regards,\nYour Team"
                        
            data = dict()
            data['to_emails'] = user['email']
            data['cc_emails'] = user['partyBEmail'] if user['partyBEmail'] else ''
            data['subject'] = subject
            data['body'] = body
            logger.info(f"send_consolidated_notification --> data ------> {data}")
            self.initiate_email(data)
        except Exception as e:
            # Handle email sending errors
            logger.error(f"Error send_consolidated_notification to {user['email']}: {e}")


    def initiate_email(self, data, attachments=None):
        try:
            resend.api_key = settings.RESEND_API_KEY
            to_emails = [e.strip() for e in data.get('to_emails', '').split(',') if e.strip()]
            cc_emails  = [e.strip() for e in data.get('cc_emails',  '').split(',') if e.strip()]
            bcc_emails = [e.strip() for e in data.get('bcc_emails', '').split(',') if e.strip()]
            subject = data.get('subject', '')
            body    = str(data.get('body', ''))

            logger.info(f"initiate_email all data ----- {data} =========== {to_emails}, {cc_emails}, {bcc_emails}")

            params = {
                "from":    settings.EMAIL_FROM,
                "to":      to_emails,
                "subject": subject,
                "html":    body.replace('\n', '<br>'),
            }
            if cc_emails:
                params["cc"] = cc_emails
            if bcc_emails:
                params["bcc"] = bcc_emails

            if attachments:
                params["attachments"] = [
                    {
                        "filename": att.name,
                        "content":  base64.b64encode(att.read()).decode(),
                    }
                    for att in attachments
                ]

            logger.info(f"SEND EMAIL via Resend ---> to={to_emails}")
            result = resend.Emails.send(params)
            return {"message": "Email sent successfully", "id": result.get("id")}
        except Exception as err:
            logger.error(f"error sending email ---> {err}")
            return {"error": str(err)}
