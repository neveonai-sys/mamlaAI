import json
import os
import re
import traceback
# from openai import OpenAI
import requests
# from striprtf.striprtf import rtf_to_text
import time
# from docx import Document
import io
import base64
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.units import inch
import datetime
# from multiprocessing import Process
from core.init_clients import get_mongo_client, get_mongo_db
from core.llm_client import chat_complete
from create_drafts.tasks import send_email_celery
from search_facility.routes.handlesearch import Handlesearch
from core.email_templates import EmailTemplates
# from transformers import BertTokenizer, BertForSequenceClassification, pipeline
# import torch
import logging
logger = logging.getLogger('django')

# Load pre-trained BERT model and tokenizer for classification (required or not)
# tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
# model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)
# classifier = pipeline('text-classification', model=model, tokenizer=tokenizer)

class Createupdatefetchdrafts:
    def __init__(self,base_path,user_id):
        self.base_path=base_path
        self.user_id = user_id

    def get_mongo_client_db(self):
        mongo = get_mongo_client()
        if mongo is None:
            raise Exception("Mongo client is not initialized.")
        db = get_mongo_db()
        return db

    def fetch_distinct_draft_types(self):
        return self.get_mongo_client_db()['draft_content_data'].distinct('draft_type')
    
    def fetch_all_docs_by_draft_type(self, draft_type):
        file_names_cursor = self.get_mongo_client_db()['draft_content_data'].find(
                        {'draft_type': draft_type},
                        {'_id': 0, 'filename': 1}
                    )

        # Extract file names from the cursor
        file_names = [doc['filename'] for doc in file_names_cursor]
        return file_names

    def read_files(self,draft_file_name, draft_type, preview=False):
        """
            using opensearch to get content of files
        """
        search_obj = Handlesearch()
        content = ''
        logger.info(f"read_files  ----> draft_file_name === {draft_file_name} || draft_type === {draft_type} || preview === {preview}")
        if not preview:
            content = search_obj.search_document_by_filename_and_draft_type(draft_file_name, draft_type)
        if not len(content) or preview:
            # Define the query criteria
            query = {
                "filename": draft_file_name,
                "draft_type": draft_type
            }

            # Retrieve the document based on the query
            document = self.get_mongo_client_db()['draft_content_data'].find_one(query)
            logger.info(f"read_files  ----> document === {document} ---- query ----{query}")
            # Check if a document is found and print the content
            if document:
                content = document.get("content")

        return content


    def create_openai_promt(self, promt_type, raw_text, user_details=None, user_suggestion=None):
        """
        promt_type:
          'req_fileds'         - extract required fields from draft text as JSON
          'create_final_draft' - fill draft with user-supplied field values
          'update_template'    - update draft with user suggestion
        """
        try:
            start_time = time.time()

            if promt_type == 'req_fileds':
                scenario = 'create_drafts:extract_fields'
                messages = [
                    {
                        "role": "system",
                        "content": "You are a legal assistant. Your task is to go through the provided draft text and extract all the necessary fields that need to be filled in, in accordance with Indian laws.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Based on the sample text, '''{raw_text}''', extract all the necessary fields needed to be filled in "
                            "and create a JSON with the field name as the key and an empty string as the value. "
                            "For each field, determine if it's required or can be left blank, suggest a data type (str, int, datetime). "
                            "If the field represents a year, day, date, or month, mark it as datetime. "
                            "Write a 5-20 word description based on the document's context.\n\n"
                            "Return the result in the following JSON format:\n"
                            "{\n"
                            '  "field_name": {\n'
                            '      "required": "True/False",\n'
                            '      "datatype": "str/int/datetime",\n'
                            '      "desc": "Short description"\n'
                            "  },\n"
                            "  ...\n"
                            "}\n\n"
                            "Return ONLY the JSON object. Do not include any explanatory text before or after."
                        ),
                    },
                ]

            elif promt_type == 'create_final_draft':
                scenario = 'create_drafts:fill_draft'
                messages = [
                    {
                        "role": "system",
                        "content": "You are a legal assistant. Your task is to help fill in a draft petition in accordance with Indian laws.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Fill this draft: '''{raw_text}''', using the details from the JSON: '''{user_details}'''. "
                            "Use the JSON values to replace the respective keys or similar keys found in the draft. "
                            "Return only the completed draft text."
                        ),
                    },
                ]

            elif promt_type == 'update_template':
                scenario = 'create_drafts:update_draft'
                messages = [
                    {
                        "role": "system",
                        "content": "You are a legal assistant. Your task is to update a draft petition in accordance with Indian laws based on the user's suggestion.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Update this existing draft: '''{raw_text}''', using the suggestion '''{user_suggestion}''' given by the end user. "
                            "Create the final draft without making any other changes on your own. "
                            "If someone asks to add a field, add the field as you see fit and place eight dots after it (........) "
                            "so the user knows they need to fill in details there. "
                            "Understand the existing draft and use the suggestion correctly to create the updated draft. "
                            "Return only the updated draft text."
                        ),
                    },
                ]

            else:
                logger.error(f"create_openai_promt: unknown promt_type '{promt_type}'")
                return {}

            assistant_content = chat_complete(
                messages=messages,
                app_scenario=scenario,
                temperature=0,
                max_tokens=1024,
            )
            assistant_content = re.sub(r'```json\s*|\s*```', '', assistant_content)
            duration = time.time() - start_time
            logger.info(f"create_openai_promt [{promt_type}] done in {duration:.2f}s")
            return assistant_content
        except Exception as err:
            logger.error(f"create_openai_promt ERROR --> {err} || {traceback.format_exc()}")
            return {}
        except Exception as err:
            logger.error(f"create_openai_promt ERROR --> {err} || {traceback.format_exc()}")
            return assistant_content

    # # Function to classify if a field is required based on the document's context
    # def classify_field(self, assistant_content, document_text):
    #     try:
    #         # Combine field name with the document to provide context
    #         input_text = f"""This is example json for you to understand the format: {{
    #       "field_name": {{
    #           "required": "True/False",
    #           "datatype": "str/int/datetime",
    #           "desc": "Short description"
    #       }},
    #       ...
    #     }}.
    #     Now go through this actual nested json: {assistant_content}. And update the "required" in each fields to "True\False" based on each "field_name"   refering the following document context: {document_text}. And return the complete json as it is with the updated fields."""
            
    #         # Use the classifier pipeline
    #         result = classifier(input_text)
    
    #         logger.info(f""" classified result ----> {result} """)
            
    #         return result #"True" if result[0]['label'] == 'LABEL_1' else "False"
    #     except:
    #         logger.error(traceback.format_exc())
    #         return assistant_content

    def get_raw_template(self,draft_type,draft_file_name):
        """
            -draft_type: type of draft as in agreement or bond
            -draft_file_name: the file selected that need to be drafted
            ----This API first get the string of texts of the file then call the API to transform in pdf byte and sent back to UI for preview
        """
        try:
            if draft_file_name.startswith('/'):
                draft_file_name = draft_file_name[1:]
            content = self.read_files(draft_file_name, draft_type, preview=True)
            buffer = self.create_pdf_with_reportlab(content,draft_file_name,to_email=None)
            return buffer
        except Exception as err:
            logger.error(f"get_raw_fields ERROR --> {traceback.format_exc()}")
            return ''

    def get_updated_template(self,suggestion,pdf_bytes_base64,draft_file_name):
        """
            -pdf_bytes_base64: pdf file template in bytes
            -suggestion: suggestion given by user for change in draft
            ----This API first get the pdf_bytes_base64 convert it to texts and take suggestions and call LLM to get new template bytes
        """
        ## gpt-4-turbo
        try:
            # Decode the base64 string to get the binary PDF data
            pdf_bytes = base64.b64decode(pdf_bytes_base64)
            
            # Read the PDF using PyPDF2 to extract text (if needed)
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)
            pdf_text = ""
            # Extract text from each page of the PDF
            for page in pdf_reader.pages:
                pdf_text += page.extract_text()
            
            updated_content = self.create_openai_promt(promt_type='update_template',raw_text=pdf_text,user_suggestion=suggestion)
            buffer = self.create_pdf_with_reportlab(updated_content,draft_file_name,to_email=None)
            return buffer
        except Exception as err:
            logger.error(f"get_raw_fields ERROR --> {traceback.format_exc()}")
            return ''
        
    def check_required_fields_exists(self,draft_type, draft_file_name, pdf_bytes_base64=None):
        """
            -draft_type: type of draft as in agreement or bond
            -draft_file_name: the file selected that need to be drafted
            ---This API will connect to database and check if req_fields for this combntn available if yes fetch it else will trigger openAI to create the fields and then insert them into DB.
        """
        try:
            # Check if the draft exists in the database
                # try:
                if pdf_bytes_base64:
                    # Decode the base64 string to get the binary PDF data
                    pdf_bytes = base64.b64decode(pdf_bytes_base64)
                    
                    # Read the PDF using PyPDF2 to extract text (if needed)
                    pdf_file = io.BytesIO(pdf_bytes)
                    pdf_reader = PdfReader(pdf_file)
                    pdf_text = ""
                    # Extract text from each page of the PDF
                    for page in pdf_reader.pages:
                        pdf_text += page.extract_text()
                    required_fields = self.create_openai_promt(promt_type='req_fileds',raw_text=pdf_text)
                else:
                    draft = self.get_mongo_client_db()['drafts_metadata'].find_one({"draft_type":draft_type,"draft_file_name":draft_file_name})
                    # Drafts.objects.get(draft_type=draft_type, draft_file_name=draft_file_name)
                    logger.info(f"DRAFFTTTTT ------> {draft}")
                    
                    # If required_fields already exist, return them
                    if draft:
                        if not draft.get('required_fields'):
                            draft['required_fields'] = [self.get_raw_fields(draft_type,draft_file_name)]
                            # draft.save()
                            result = self.get_mongo_client_db()['drafts_metadata'].update_one(
                                        {"draft_type":draft_type,"draft_file_name":draft_file_name},  # Filter by the user ID (or any other criteria)
                                        {"$set": {"required_fields": draft['required_fields'], "last_updated_on": datetime.datetime.now()}}  # Add the new field
                                    )

                        # logger.info(f"check_required_fields_exists |||| in TRY --> required_fields --> {draft['required_fields']}")
                        return draft['required_fields']
                
                    else:
                        # If the draft does not exist, create a new entry with the required fields
                        required_fields = [self.get_raw_fields(draft_type,draft_file_name)]
                        # logger.info(f" --------------- draft_type:{draft_type},draft_file_name:{draft_file_name},required_fields:{required_fields}")
                        if required_fields!=['']:
                            data = {
                                    "draft_type": draft_type,  # Key and value should be in quotes
                                    "draft_file_name": draft_file_name,  # Same here
                                    "required_fields": required_fields,
                                    "last_updated_on": datetime.datetime.now()
                                }
                            result = self.get_mongo_client_db()['drafts_metadata'].insert_one(data)
                        # logger.info(f"check_required_fields_exists |||| in EXCEPT --> required_fields --> {required_fields}")
                return required_fields

        except Exception as err:
            logger.error(f"check_required_fields_exists ERROR --> {err}\n{traceback.format_exc()}")
            return False
        
    def get_raw_fields(self,draft_type,draft_file_name):
        """
            -draft_type: type of draft as in agreement or bond
            -draft_file_name: the file selected that need to be drafted
            ----This API first get the string of texts of the file then call the API to create req_fields using openAI
        """
        try:
            if draft_file_name.startswith('/'):
                draft_file_name = draft_file_name[1:]
            content = self.read_files(draft_file_name, draft_type)
            return self.create_openai_promt(promt_type='req_fileds',raw_text=content)
        except Exception as err:
            logger.error(f"get_raw_fields ERROR --> {traceback.format_exc()}")
            return ''
        
    
    def create_pdf_with_reportlab(self,doc_text,file_name,to_email=None):
        """
            -doc_text: strig of text
            ----API to convert text to PDF, then writes in IO buffer
        """
        try:
            # Create an in-memory buffer
            buffer = io.BytesIO()

            # Set up document
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)

            # Use styles for text formatting
            styles = getSampleStyleSheet()
            style_normal = styles['Normal']
            style_normal.fontName = 'Helvetica'  # Set font, can be replaced with any available font

            # Split input text by lines and create paragraphs
            flowables = []
            lines = doc_text.split('\n')  # Split by lines in original text
            for line in lines:
                paragraph = Paragraph(line, style_normal)
                flowables.append(paragraph)
                flowables.append(Spacer(1, 0.2 * inch))  # Add space between paragraphs

            # Build the document with all flowables (Paragraphs)
            doc.build(flowables)

            # Move the buffer's position to the start
            buffer.seek(0)

            # Send professional draft email with attachment
            if to_email:
                try:
                    encoded_file = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    # Professional email for draft delivery
                    subject = "Your Legal Draft is Ready - Mamla.ai"
                    body = """Dear User,

Your requested legal draft has been prepared and is attached to this email.

The document is attached as a PDF file for your review. Please review it carefully and let us know if you need any modifications.

To request changes or for any assistance, please log in to your Mamla.ai dashboard.

Best regards,
The Mamla.ai Team

---
Need help? Contact us at support@mamla.ai
Visit us: https://mamla.ai"""
                    send_email_celery.delay(to_email, subject, body, file_name, encoded_file)
                except Exception as e:
                    logger.error(f" at triggering mail {e}")

            return buffer
        except Exception as err:
            logger.error(traceback.format_exc())
            logger.error(f"create_pdf_with_reportlab ERROR --> {err}")
            return ''
        
    
    def auto_save_drafts(self,data):
        """
            save the semi filled drafts
        """
        try:
            draft_type = data.get('type')
            filename = data.get('filename')
            form_data = data.get('form_data')
            req_fields = data.get('req_fields')
            
            draft_key = f"{draft_type}_{filename}"
            logger.info(f" auto_save_drafts --- >>> draft_key - {draft_key}")

            existing_indexes = self.get_mongo_client_db()['user_draft_data'].index_information()
            if "user_id" not in existing_indexes:
                self.get_mongo_client_db()['user_draft_data'].create_index([("user_id", 1)])
            
            # Update or insert the draft using atomic operations
            update_result = self.get_mongo_client_db()['user_draft_data'].update_one(
                {'user_id': self.user_id},
                {
                    '$set': {
                        f'saved_drafts.{draft_key}.form_data': form_data,
                        f'saved_drafts.{draft_key}.req_fields': req_fields
                    },
                    '$inc': {'total_drafts_created': 1}  # Increment only if inserting a new draft
                },
                upsert=True  # Insert if the document does not exist
            )
            logger.info(f" auto_save_drafts --- >>> update_result - {update_result}")
            if update_result.upserted_id:
                # A new user document was created and the draft was inserted
                return {'message': 'Draft auto-saved successfully'}
            elif update_result.modified_count > 0:
                # Existing draft was updated
                return {'message': 'Draft auto-saved successfully'}
            else:
                # No changes were made (this can happen if the data is identical)
                return {'message': 'Draft is already up-to-date'}
        except Exception as err:
            logger.error(f"auto_save_drafts ERROR --> {traceback.format_exc()}")
            return {'error': err}


    def load_previously_saved_draft(self,draft_type,filename):
        """
            -- fetch the semi filled form of the selected type
        """
        try:
            draft_key = f"{draft_type}_{filename}"
            logger.info(f"load_previously_saved_draft ---> key ====> {draft_key}")

            existing_indexes = self.get_mongo_client_db()['user_draft_data'].index_information()
            if "user_id" not in existing_indexes:
                self.get_mongo_client_db()['user_draft_data'].create_index([("user_id", 1)])
            # Use MongoDB's projection to retrieve only the specific draft
            user_doc = self.get_mongo_client_db()['user_draft_data'].find_one(
                {'user_id': self.user_id, f'saved_drafts.{draft_key}': {'$exists': True}},
                {f'saved_drafts.{draft_key}.form_data': 1, f'saved_drafts.{draft_key}.req_fields': 1, '_id': 0}
            )
            
            if not user_doc or 'saved_drafts' not in user_doc or draft_key not in user_doc['saved_drafts']:
                raise Exception('Draft not found')
            
            draft = user_doc['saved_drafts'][draft_key]
            form_data = draft.get('form_data', {})
            req_fields = draft.get('req_fields', {})
            
            return {'form_data': form_data, 'req_fields': req_fields}
        except Exception as err:
            logger.error(f"load_previously_saved_draft ERROR  || {err} ||| --> {traceback.format_exc()}")
            return {'err':err}


    def get_previously_semi_filled_saved_drafts(self):
        """
            -- get list of semi filled forms
        """
        try:
            existing_indexes = self.get_mongo_client_db()['user_draft_data'].index_information()
            if "user_id" not in existing_indexes:
                self.get_mongo_client_db()['user_draft_data'].create_index([("user_id", 1)])

            user_doc = self.get_mongo_client_db()['user_draft_data'].find_one(
                            {'user_id': self.user_id},
                            {'_id': 0, 'saved_drafts': 1}
                        )
            
            if not user_doc or 'saved_drafts' not in user_doc:
                # No drafts found
                return {'saved_drafts': []}
            
            saved_drafts = user_doc['saved_drafts']
            draft_list = []
            
            # Iterate through the saved_drafts dictionary and extract type and filename
            for key in saved_drafts:
                # Assuming key format: "<draft_type>_<filename>"
                if '_' in key:
                    draft_type, filename = key.split('_', 1)
                    draft_list.append({
                        'type': draft_type,
                        'filename': filename
                    })
            
            return {'saved_drafts': draft_list}
        except Exception as err:
            logger.error(f"get_previously_semi_filled_saved_drafts ERROR --> {traceback.format_exc()}")
            return {'err':err}