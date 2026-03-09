from celery import shared_task
import requests
import traceback
from io import BytesIO
import base64
from django.conf import settings

@shared_task
def send_email_celery( to_email, subj, body, file_name=None, attach_files=None):
    try:
        payload = {
        "to_emails": to_email,
        "subject": subj,
        "body": body
        }
        
        print(" in shared taskkkssss ---")
        url = f"{settings.FRONTEND_URL}/api/utils/send-email/"
        files={}
        if attach_files:
            file_data = base64.b64decode(attach_files)
            file_buffer = BytesIO(file_data)
            files={
                    ('attachments',(file_name.split('.')[0]+'.pdf',file_buffer,'application/pdf'))
                    }
            # headers = {}
        response = requests.request("POST", url, data=payload, files=files)
        # file_buffer.close()
        print(response.text)
    #     return True
    except Exception as err:
        print(traceback.format_exc())
        print(f"EERROR SHAREDD TASKKKK AT send_email createdrafts ---->  {err}",flush=True)
    #     return False
