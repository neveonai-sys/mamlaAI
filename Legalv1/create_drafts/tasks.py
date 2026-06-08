import logging
import traceback
from io import BytesIO
import base64

import requests
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def send_email_celery(to_email, subj, body, file_name=None, attach_files=None):
    try:
        payload = {
            "to_emails": to_email,
            "subject": subj,
            "body": body,
        }
        logger.debug("send_email_celery to=%s subject=%s", to_email, subj)
        url = f"{settings.FRONTEND_URL}/api/utils/send-email/"
        files = {}
        if attach_files:
            file_data = base64.b64decode(attach_files)
            file_buffer = BytesIO(file_data)
            files = {
                ("attachments", (file_name.split(".")[0] + ".pdf", file_buffer, "application/pdf"))
            }
        response = requests.request("POST", url, data=payload, files=files)
        logger.info("send_email_celery response status=%s", response.status_code)
    except Exception as err:
        logger.error("send_email_celery failed: %s\n%s", err, traceback.format_exc())
