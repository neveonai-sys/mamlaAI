# from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import resend
import base64
import logging
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from utilities.routes.utils import Handutilities
from utilities.tasks import update_state_district_court_data

logger = logging.getLogger('django')

@api_view(['POST'])
def send_mail_page(request):
    try:
        req_body = request.data
        address = req_body.get('address')
        subject = req_body.get('subject')
        message = req_body.get('message')

        if not all([address, subject, message]):
            raise Exception('All fields are required')

        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from":    settings.EMAIL_FROM,
            "to":      [address],
            "subject": subject,
            "html":    f"<p>{message}</p>",
        })
        return JsonResponse({'Status': "Mail Send Successfully!"})
    except Exception as err:
        print(f"send_mail_page ERROR --> {err}", flush=True)
        return JsonResponse({'status': 'fail', 'message': str(err)}, status=400)


@api_view(['POST'])
def send_email_v2(request):
    data = request.data
    to_emails  = data.get('to_emails', [])
    cc_emails  = data.get('cc_emails', [])
    bcc_emails = data.get('bcc_emails', [])
    subject    = data.get('subject', '')
    body       = data.get('body', '')
    attachments = request.FILES.getlist('attachments')

    try:
        resend.api_key = settings.RESEND_API_KEY
        params = {
            "from":    settings.EMAIL_FROM,
            "to":      to_emails if isinstance(to_emails, list) else [to_emails],
            "subject": subject,
            "html":    body.replace('\n', '<br>'),
        }
        if cc_emails:
            params["cc"] = cc_emails if isinstance(cc_emails, list) else [cc_emails]
        if bcc_emails:
            params["bcc"] = bcc_emails if isinstance(bcc_emails, list) else [bcc_emails]
        if attachments:
            params["attachments"] = [
                {"filename": att.name, "content": base64.b64encode(att.read()).decode()}
                for att in attachments
            ]
        result = resend.Emails.send(params)
        return Response({"message": "Email sent successfully", "id": result.get("id")}, status=status.HTTP_200_OK)
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

