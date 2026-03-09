# Create your views here.
# from rest_framework import status
from rest_framework.decorators import api_view
# from rest_framework.response import Response
from django.http import JsonResponse
# import jwt
from django.core.mail import send_mail
import requests
# from datetime import datetime
# import calendar
import traceback
from .routes.createupdateevents import Eventmanagement
# from celery import chain
# from django.conf import settings
from supabase_required import supabase_required
from django_ratelimit.decorators import ratelimit
from core.email_templates import EmailTemplates, format_datetime_for_email
import logging

logger = logging.getLogger('django')

@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='5/m', block=True)  # Limit to 5 requests per minute per user
def create_event(request):
    """
   {"title":"newwww","start":"2024-09-17T22:01","end":"2024-09-24T00:03","partyBEmail":" ajmrlegaly@gmail.com","meetinglink":"VideoCall","caseId":"121313","Status":"Y","Task_type":"Client Meeting","send_remainder":"Email","email_id":"mems650@gmail.com"}
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = request.data
        logger.info(data)
        email_id = supa_user.get('email')
        fname = supa_user.get('fname')
        lname = supa_user.get('lname')
        data['fname'] = fname
        data['lname'] = lname
        data['email_id'] = email_id

        start_datetime = data.get('start', '')
        end_datetime = data.get('end', '')

        party_b_email = data.get('partyBEmail', '')

        obj = Eventmanagement(user_id)
        create_status = obj.create_new_event(data)

        ##TODO: move sending mail to another file...
        if create_status.get('mssg'):
            logger.info(f" ======= create_status ==== {create_status} ")
            email_data = []
            
            # Format dates for professional display
            formatted_start = format_datetime_for_email(start_datetime)
            formatted_end = format_datetime_for_email(end_datetime)
            
            if party_b_email:
                # Email to user with party B involved
                email_subject, email_body = EmailTemplates.event_created_with_party(
                    fname, lname, formatted_start, formatted_end, create_status.get('meet_link')
                )
                email_data.append([email_id, email_subject, email_body])
                logger.info(f" ======= create_status party_b_email ==== EMAIL SENT ")
                obj.send_email_by_celery(email_data, party_b_email)
            else:
                # Solo task/event
                email_subject, email_body = EmailTemplates.event_created_solo(
                    fname, lname, formatted_start, formatted_end, create_status.get('meet_link')
                )
                email_data.append([email_id, email_subject, email_body])
                logger.info(f" ======= create_status no party_b_email ==== EMAIL SENT ")
                obj.send_email_by_celery(email_data)
        else:
            raise Exception
        return JsonResponse({"message": "Event created successfully"}, status=201)
    except Exception as err:
        logger.error(f"errrooorr at create event --------> {traceback.format_exc()}")
        return JsonResponse({'status': 'fail', 'message': str(err)}, status=500)

@api_view(['GET'])
@supabase_required
def fetch_event(request):
    try:
        # email_id = request.GET.get('email_id')
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        startdate = request.GET.get('start_date')
        enddate = request.GET.get('end_date')
        obj = Eventmanagement(user_id)

        '''
        # Get the current date to determine the current month and year
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        # Define the start and end dates for the current month
        start_date = f"{current_year}-{current_month:02d}-01"
        # To get the last day of the current month, you can use the calendar module
        
        last_day = calendar.monthrange(current_year, current_month)[1]
        end_date = f"{current_year}-{current_month:02d}-{last_day:02d}"

        start_dt = datetime.strptime(startdate, "%Y-%m-%d")
        end_dt = datetime.strptime(enddate, "%Y-%m-%d")
        '''

        meeting_list = obj.get_all_events_for_user(startdate, enddate)
        return JsonResponse({"events": meeting_list}, status=201)
    except Exception as err:
        logger.error(f"errrooorr at fetch_event event --------> {traceback.format_exc()}")
        return JsonResponse({"events": []}, status=500)


@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='5/m', block=True)
def update_event(request):
    try:
        logger.info(f"""update_event ---> {request.data} """)
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = request.data
        email_id = supa_user.get('email')
        fname = supa_user.get('fname')
        lname = supa_user.get('lname')
        data['fname'] = fname
        data['lname'] = lname
        data['email_id'] = email_id
        # email_id = data.get('email_id')
        obj = Eventmanagement(user_id)
        chk = obj.update_event_for_user(data)
        if chk:
            return JsonResponse({"mssg": "Successfully Updated"}, status=201)
        else:
            return JsonResponse({"mssg": "Meeting Not Found"}, status=401)
    except Exception as err:
        logger.error(f"errrooorr at update_event event --------> {traceback.format_exc()}")
        return JsonResponse({"mssg": f"""Failed to udpate, {err}"""}, status=500)  


@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='5/m', block=True)
def delete_event(request):
    try:
        logger.info(f"""delete_event ---> {request.data} """)
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = request.data.get('data')
        email_id = supa_user.get('email')
        fname = supa_user.get('fname')
        lname = supa_user.get('lname')
        data['fname'] = fname
        data['lname'] = lname
        data['email_id'] = email_id
        obj = Eventmanagement(user_id)
        chk = obj.delete_event_for_user(data)
        if chk:
            return JsonResponse({"mssg": "Successfully deleted"}, status=201)
        else:
            return JsonResponse({"mssg": "Meeting Not Found"}, status=401)
    except Exception as err:
        logger.error(f"errrooorr at delete_event event --------> {traceback.format_exc()}")
        return JsonResponse({"mssg": f"""Failed to delete, {err}"""}, status=500)   

def send_event_reminder(event):
    message = f"""Reminder for event: {event.title} at {event.start_date.strftime('%Y-%m-%d')} from {event.start_time} to {event.end_time}"""

    # Send Email Reminder
    if event.send_reminder in ['Email', 'Both'] and event.party_b_email:
        send_mail(
            'Event Reminder',
            message,
            'from@example.com',  # Replace with your actual email settings
            [event.party_b_email],
            fail_silently=False,
        )

    # Send WhatsApp Reminder using a service like Twilio
    if event.send_reminder in ['WhatsApp', 'Both']:
        send_whatsapp_message(event.phone_number, message)

def send_whatsapp_message(phone_number, message):
    # Example using Twilio API (ensure you replace with actual implementation)
    account_sid = 'your_account_sid'
    auth_token = 'your_auth_token'
    from_whatsapp_number = 'whatsapp:+14155238886'  # Your Twilio number
    to_whatsapp_number = f'whatsapp:+{phone_number}'
    
    requests.post(
        f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json',
        data={
            'From': from_whatsapp_number,
            'To': to_whatsapp_number,
            'Body': message,
        },
        auth=(account_sid, auth_token)
    )
