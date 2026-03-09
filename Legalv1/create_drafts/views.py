from django.http import JsonResponse, HttpResponse
from rest_framework.decorators import api_view
import os, json
from create_drafts.routes.creatupdatedrafts import Createupdatefetchdrafts
from supabase_required import supabase_required
from django_ratelimit.decorators import ratelimit
import traceback
import logging
logger = logging.getLogger('django')
# Create your views here.

base_path = '../draftdocs/'

@api_view(['GET'])
@supabase_required
def get_available_drafts_list(request):
    """
        -fetch all the draft_type like agreement or bond
    """
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = Createupdatefetchdrafts(base_path=base_path,user_id=user_id)
    dir_list = sorted(obj.fetch_distinct_draft_types())
    if not len(dir_list):
        logger.warning("DRAFTT TYPEEE not found in DB")
        drafts_dir = base_path
        dir_list = os.listdir(drafts_dir)
        dir_list = sorted(dir_list)
    # print(f"dir_list --> {dir_list}",flush=True)

    return JsonResponse({'dir_list': dir_list})


@api_view(['GET'])
@supabase_required
def get_all_drafts_from_drafttype_folder(request):
    """
        -get the draft_type and fetch all documents in the draft_type
    """

    draft_type = request.GET.get('type')
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = Createupdatefetchdrafts(base_path=base_path,user_id=user_id)
    all_files = obj.fetch_all_docs_by_draft_type(draft_type)
    
    if not len(all_files):
        logger.warning("DRAFTTT FILESSS not found in DB")
        all_drafts_path = os.path.join(base_path,draft_type)
        # all_drafts_list = sorted([f for f in os.listdir(all_drafts_path) if not f.endswith('.Identifier')])
        # print(f"all_drafts_list --> {all_drafts_list}",flush=True)
        all_files = []
        for dirpath, dirnames, filenames in os.walk(all_drafts_path):
            # logger.info(f"000000000000000000000000000000000000000000000000  {dirnames} ||| {dirpath} || {filenames[:10]}")
            dirpath = dirpath.replace(all_drafts_path,'')
            for file in filenames:
                if not file.endswith('.Identifier'):
                    all_files.append(os.path.join(dirpath, file))
                    # all_files.append(file)
    all_drafts_list = sorted(all_files)
    return JsonResponse({'all_drafts_list': all_drafts_list})


@api_view(['GET'])
@supabase_required
def fetch_pdftemplate_from_doc(request):
    """
        -received the draft type and doc name selected by user.
        -use it to fetch pdftemplate for user to preview.
    """
    try:
        draft_type = request.GET.get('type')
        file_name = request.GET.get('filename')

        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        obj = Createupdatefetchdrafts(base_path=base_path,user_id=user_id)
        buffer = obj.get_raw_template(draft_type,file_name)

        # logger.info(f"fetch_required_fields_from_doc ============ get_required_fields --> {get_required_fields}")

        # buffer = obj.create_pdf_with_reportlab(text_response,file_name, to_email_id) #obj.tarnsform_openai_text_to_pdf(text_response)

        logger.info(f"fetch_pdftemplate_from_doc ----- ||||||||||| buffer >> {buffer}")
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=f"{file_name}.pdf"'
        logger.info(f"fetch_pdftemplate_from_doc ----- ||||||||||| response >> {response}")
        buffer.close()
        return response

    except Exception as err:
        logger.error(f"fetch_required_fields_from_doc ERROR --> {err}")
        return JsonResponse({'status': 'fail', 'message': []}, status=400)

@api_view(['POST'])
@supabase_required
def update_template_with_suggestions(request):
    """
        -received the draft type and doc name selected by user.
        -use it to fetch pdftemplate for user to preview.
    """
    try:
        # req_body = request.data
        # Get the JSON payload from the request
        payload = json.loads(request.body.decode('utf-8'))
        
        # Extract the base64 PDF bytes and other fields from the payload
        pdf_bytes_base64 = payload.get("pdf_bytes")
        file_name = payload.get("filename")
        suggestion = payload.get("suggestion")
        draft_type = payload.get('type')

        logger.info(f"fetch_pdftemplate_from_doc ----- |||pdf_bytes_base64 -- {len(pdf_bytes_base64)}||| filename -- {file_name}|| draft_type -- {draft_type}")
        
        if not pdf_bytes_base64:
            return JsonResponse({'error': 'No PDF data provided'}, status=400)

        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        obj = Createupdatefetchdrafts(base_path=base_path,user_id=user_id)
        buffer = obj.get_updated_template(suggestion,pdf_bytes_base64,file_name)

        logger.info(f"fetch_pdftemplate_from_doc ----- ||||||||||| buffer >> {buffer}")
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=f"{file_name}.pdf"'
        logger.info(f"fetch_pdftemplate_from_doc ----- ||||||||||| response >> {response}")
        buffer.close()
        return response

    except Exception as err:
        logger.error(f"update_template_with_suggestions ERROR --> {traceback.format_exc()}")
        return JsonResponse({'status': 'fail', 'message': []}, status=400)


@api_view(['POST'])
@supabase_required
def fetch_required_fields_from_doc(request):
    """
        -received the draft type and doc name selected by user.
        -use it to fetch required fields for user to fill.
    """
    try:
        req_body = request.data
        draft_type = req_body.get('type')
        file_name = req_body.get('filename')
        pdf_bytes = req_body.get('pdf_bytes')

        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        obj = Createupdatefetchdrafts(base_path=base_path,user_id=user_id)
        get_required_fields = obj.check_required_fields_exists(draft_type,file_name,pdf_bytes)

        # logger.info(f"fetch_required_fields_from_doc ============ get_required_fields --> {get_required_fields}")

        return JsonResponse({'req_fields': get_required_fields})
    except Exception as err:
        logger.error(f"fetch_required_fields_from_doc ERROR --> {traceback.format_exc()}")
        return JsonResponse({'status': 'fail', 'message': []}, status=400)

    
@api_view(['POST'])
@supabase_required
@ratelimit(key='user', rate='5/m', block=True)
def create_final_draft_and_send_pdf(request):
    """
        -received the draft type and doc name selected by user and the req_filed json by the user.
            -- {"type":"Application","item":"Application for cancellation of Warrant.docx","fields":{"Court":"_____","Case Number":"__","Accused Name":"ABC","Date of Absence":"___","Reason for Absence":"__","Sections of Law":"82, 88 of CrPC, 1973; Section 21 of General Clauses Act, 1897","Judgment Reference":"Bombay HC Judgment in Arunkumar N. Chaturvedi v/s The State of Maharashtra & Another, Writ Petition No. 4429 of 2013","Advocate Name":"XYZ"}}
        -use it to create draft and convert to pdf and send it to UI from where user can download it.
    """
    try:
        req_body = request.data
        print(f"create_final_draft_and_send_pdf -----  req_body >> {req_body}",flush=True)
        draft_type = req_body.get('type')
        file_name = req_body.get('item')
        to_email_id = req_body.get('email_id')
        raw_fields = req_body.get('fields')

        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        obj = Createupdatefetchdrafts(base_path=base_path,user_id=user_id)
        # file_path = os.path.join(base_path,draft_type,file_name)
        raw_text = obj.read_files(file_name,draft_type)       
        
        text_response = obj.create_openai_promt(promt_type='create_final_draft',raw_text=raw_text,user_details=raw_fields)
        # print(f"create_final_draft_and_send_pdf ----- ||||||||||| text_response >> {text_response}",flush=True)

        buffer = obj.create_pdf_with_reportlab(text_response,file_name, to_email_id) #obj.tarnsform_openai_text_to_pdf(text_response)

        logger.info(f"tarnsform_openai_text_to_pdf ----- ||||||||||| buffer >> {buffer}")
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="document.pdf"'
        logger.info(f"tarnsform_openai_text_to_pdf ----- ||||||||||| response >> {response}")
        buffer.close()
        return response

    except Exception as err:
        logger.error(f"create_final_draft_and_send_pdf ERROR --> {err}")
        return JsonResponse({'status': 'fail', 'message': []}, status=400)
    


@api_view(['POST'])
@supabase_required
def auto_save(request):
    """
    Saves or updates a draft with the provided data.
    Expected Payload:
    {
        "type": "Report",
        "filename": "Annual_Report_2023.pdf",
        "form_data": { /* ... */ },
        "req_fields": { /* ... */ }
    }
    Response Format:
    {
        "message": "Draft auto-saved successfully"
    }
    """
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    
    required_fields = ['type', 'filename', 'form_data', 'req_fields']
    if not all(field in data for field in required_fields):
        return JsonResponse({'error': 'Missing required fields in payload'}, status=400)
    
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = Createupdatefetchdrafts(base_path=base_path,user_id=user_id)
    chk = obj.auto_save_drafts(data=data)
    
    if 'message' in chk:
        return JsonResponse(chk, status=200)
    else:
        JsonResponse(chk, status=400)


@api_view(["GET"])
@supabase_required
def load_saved_draft(request):
    """
    Loads a specific saved draft based on type and filename.
    Query Parameters:
        - type: The draft type (e.g., Report, Invoice)
        - filename: The draft filename (e.g., Annual_Report_2023.pdf)
    Response Format:
    {
        "form_data": { /* ... */ },
        "req_fields": { /* ... */ }
    }
    """
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    
    draft_type = request.GET.get('type')
    filename = request.GET.get('filename')
    
    if not draft_type or not filename:
        return JsonResponse({'error': 'Missing type or filename parameter'}, status=400)
    
    obj = Createupdatefetchdrafts(base_path=base_path,user_id=user_id)
    chk = obj.load_previously_saved_draft(draft_type=draft_type,filename=filename)
    if not 'err' in chk:
        return JsonResponse(chk, status=200)
    else:
        return JsonResponse(chk, status=404)


@api_view(["GET"])
@supabase_required
def get_saved_drafts(request):
    """
    Retrieves all saved drafts for the authenticated user.
    Response Format:
    {
        "saved_drafts": [
            {"type": "Report", "filename": "Annual_Report_2023.pdf"},
            {"type": "Invoice", "filename": "Invoice_January.pdf"}
            // ... more drafts
        ]
    }
    """
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = Createupdatefetchdrafts(base_path=base_path,user_id=user_id)
    chk = obj.get_previously_semi_filled_saved_drafts()
    
    if not 'err' in chk:
        return JsonResponse(chk, status=200)
    else:
        return JsonResponse(chk, status=404)
