# from django.shortcuts import render
from django.http import JsonResponse
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.base import MIMEBase
# from email import encoders
# from smtplib import SMTP, SMTPException
# from utilities.models import state_district_court_collection
# import os
import logging
# import json
# import requests
from django.views.decorators.csrf import csrf_exempt
# from concurrent.futures import ThreadPoolExecutor, as_completed
from django.http import JsonResponse
# from django.views import View
from utilities.routes.utils import Handutilities
from utilities.tasks import update_state_district_court_data

logger = logging.getLogger('django')

@api_view(['POST'])
def send_mail_page(request):
    try:
        context = {}
        req_body = request.data
        # if request.method == 'POST':
        address = req_body.get('address')
        subject = req_body.get('subject')
        message = req_body.get('message')

        if address and subject and message:
            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER, [address])
                context['result'] = 'Email sent successfully'
            except Exception as e:
                context['result'] = f'Error sending email: {e}'
        else:
            context['result'] = 'All fields are required'
            raise Exception('All fields are required')
        
        return JsonResponse({'Status': "Mail Send Successfully!"})
    except Exception as err:
        print(f"send_mail_page ERROR --> {err}",flush=True)
        return JsonResponse({'status': 'fail', 'message': []}, status=400)
    

@api_view(['POST'])
def send_email_v2(request):
    data = request.data
    from_email = settings.EMAIL_HOST_USER
    to_emails = data.get('to_emails', [])
    cc_emails = data.get('cc_emails', [])
    bcc_emails = data.get('bcc_emails', [])
    subject = data.get('subject', '')
    body = data.get('body', '')

    # Handle attachments
    attachments = request.FILES.getlist('attachments')

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[to_emails],
        cc=[cc_emails],
        bcc=[bcc_emails],
    )

    # Attach files if any
    for attachment in attachments:
        email.attach(attachment.name, attachment.read(), attachment.content_type)

    print(f"send_email ----------> {email}")

    try:
        email.send()
        return Response({"message": "Email sent successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['POST'])
def send_email(request):
    try:
        data = request.data
        logger.info(f"IN UTILITIESS SEND MAIL -----------> {data}")
        attachments = request.FILES.getlist('attachments')
        obj = Handutilities()
        if attachments:
            res = obj.initiate_email(data,attachments)
        else:
            res = obj.initiate_email(data)
        return Response(res, status=status.HTTP_200_OK)
    except Exception as err:
        logger.error(f" errorr sending email ---> {err}")
        return Response({"error": str(err)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
def state_district_courtlist(request):
    update_state_district_court_data.delay()
    return JsonResponse({"message": "Data fetching and storing in progress"}, status=200)

