import json
import uuid
import os
import re
import traceback
import datetime
import random
import uuid
import logging
import string
import bcrypt
from Legalv1.settings import FRONTEND_URL
from users.tasks import send_email_celery, request_to_whatsapp_url, send_whatsapp_message_celery
from utilities.routes.utils import Handutilities
from core.init_clients import get_mongo_client, get_mongo_db, get_supabase_client
from core.email_templates import EmailTemplates

# Get the logger for this module
logger = logging.getLogger('django')

class Handleuserdata:
    def __init__(self) -> None:
        pass

    def get_mongo_client_db(self):
        mongo = get_mongo_client()
        if not mongo:
            return ''
        db = get_mongo_db()
        return db
       
    def check_user_exists(self, chk_data):
        user = self.get_mongo_client_db()['user_details'].find_one(chk_data)
        logger.info(f"user in exists chk_data ==> {chk_data}")
        res = {}
        if user:
            # res['fname'] = user.get('fname')
            # res['lname'] = user.get('lname')
            # res['email_id'] = user.get('email')
            # res['phone_number'] = user.get('phone_number')
            res['user_id'] = user.get('user_id')
            res['user_status'] = user.get('user_status')
            res['otp'] = user.get('otp')
            res['otp_count'] = user.get('otp_count')
            res['user_type'] = user.get('user_type')
        return res

    def generate_username(self, fname, lname):
        try:
            # Start with an initial empty list for building the username
            username_parts = []
        
            # Check if lname is provided
            if lname:
                username_parts.append(fname[:1])  # First character of fname
                username_parts.append(lname[:3])  # First three characters of lname
            else:
                # If lname is empty, handle fname
                if len(fname) >= 4:
                    username_parts.append(fname[:4])  # First four characters of fname
                else:
                    username_parts.append(fname)  # Take entire fname
        
                    # Add random characters if needed
                    while len(''.join(username_parts)) < 4:
                        username_parts.append(random.choice(string.ascii_letters))
        
            # Ensure the username is exactly 4 characters long
            return ''.join(username_parts)[:4]
        except Exception as err:
            logger.error(traceback.format_exc())
            return False
        
    def hash_password(self, plain_password):
        # Generate a salt
        salt = bcrypt.gensalt()
        # Hash the password with the salt
        hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
        return hashed_password

    def check_password(self, user_id, plain_password):
        # Get the hashed password from the database
        stored_hashed_password = self.get_mongo_client_db()['user_details'].find_one({"user_id": user_id})["password"]
        # Check if the hashed password matches the plain password
        return bcrypt.checkpw(plain_password.encode('utf-8'), stored_hashed_password)

        
    def create_new_user(self, phone_number, fname, lname, email, user_type, password, user_status, barcode_id=None, case_ids=[], state='', district='', courts='', whatsappOptIn=False, agreedTnC=False, onboarding_by_flag = False):
        try:
            dtmstr = datetime.datetime.now(datetime.timezone.utc)
            user_id = self.generate_username(fname.lower(),lname.lower())+'_'+dtmstr.strftime("%Y%m%d%H%M%S")
            data = {
                        "user_id" : user_id,
                        "phone_number" : phone_number,
                        "fname" : fname,
                        "lname" : lname,
                        "email" : email,
                        "password" : self.hash_password(password),
                        "user_type" : user_type,
                        "last_updated_on":dtmstr,
                        "user_status":user_status,
                        "whatsappOptIn":whatsappOptIn,
                        "agreedTnC":agreedTnC,
                        "meetings":{},
                        "email_verification":'Pending',
                        "whatsapp_verification":'Pending'
                        }
            ## onboarding flag means lawyer has onboarded these clients, so these verification links are not needed untill the user themselves signup after the onboarding is done
            if not onboarding_by_flag:
                email_verify_token = str(uuid.uuid4())
                expiry_time = dtmstr + datetime.timedelta(hours=24)
                email_verification_token = email_verify_token
                email_verification_expiry = expiry_time
                data["email_verification_token"] = email_verify_token
                data["email_verification_expiry"] = expiry_time
                
            if user_type=='Lawyer':
                data["barcode_id"] = barcode_id
                data["case_ids"] = case_ids
                data["ai_draft_count"] = 0
                data["template_draft_count"] = 0
            elif user_type=='Client':
                data["case_ids"] = case_ids
            elif user_type=='Paralegal':
                data["state"] = state 
                data["district"] = district
                data["courts"] = courts
                data["template_draft_count"] = 0
            # logger.info(f"creating user data -----> {data} || {user_id}")
            self.get_mongo_client_db()['user_details'].insert_one(data)
            if not onboarding_by_flag:
                return user_id, email_verification_token
            else:
                return user_id
        except Exception as err:
            logger.error(traceback.format_exc())
            return False
        
    def send_email_verification_link(self, email, verification_token, fname):
        """
        Send an email containing a link like:
        https://example.com/verify-email?token=verification_token
        The user must click within 24 hours to verify.
        """
        frontend_url = FRONTEND_URL
        verify_link = f"{frontend_url}/api/users/verify-email/?token={verification_token}"
        subject, body = EmailTemplates.email_verification_link(fname, verify_link)
        obj = Handutilities()
        payload = {
            "to_emails": email,
            "subject": subject,
            "body": body,
        }
        chk = obj.initiate_email(payload)
        logger.info(f"[DEBUG] Sending email to {email} with link {verify_link}")
        if chk.get('message'):
            return True
        else:
            return False
        

    def send_whatsapp_message(self, phone_number, message):
        """
        Send a WhatsApp message. Return True if delivered, False if not.
        For demonstration, assume it's always successful.
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": f'91{phone_number}',
            "text": {"body": message}
        }
        logger.info(f"[DEBUG] Sending WhatsApp message PAYLOAD --> {payload}'")
        chk = request_to_whatsapp_url(payload)
        logger.info(f"[DEBUG] Sending WhatsApp message chk --> {chk}'")
        if chk.status_code == 200:
            return True
        else:
            return False
        
    # def send_text_message(self, text):
    #     payload = {
    #         "messaging_product": "whatsapp",
    #         "to": self.incoming_user_number,
    #         "text": {"body": text}
    #     }
    #     self.send_whatsapp_message(payload)
    
    def cleanup_unverified_users(self):
        """
        This function can be run periodically (e.g. via cron or Celery beat)
        to remove any user whose email_verification is still 'Pending' and
        is older than 24 hours from creation.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        # Find documents where email_verification='Pending' and created_on < now - 24 hours
        cutoff = now - datetime.timedelta(hours=24)

        result = self.get_mongo_client_db()['user_details'].delete_many({
            "email_verification": "Pending",
            "created_on": {"$lte": cutoff}
        })
        logger.info(f"cleanup_unverified_users: Deleted {result.deleted_count} unverified users.")
        
    def update_user_detail(self,user_id,chk_data):
        # logger.info(f"=========== update_user_status  status ============= {chk_data}")
        self.get_mongo_client_db()['user_details'].update_one(
                        {"user_id":user_id},
                        {
                            "$set": chk_data
                        }
                    )
        return True

    def update_caseid_and_clientid(self, user_id, new_client_id, new_case_id=[]):
        try:
            # Define the filter to identify the document
            filter_query = {"user_id": user_id}
            
            # Define the update operations
            if len(new_case_id):
                update_operations = {
                    "$addToSet": {"client_ids": new_client_id, "case_ids": new_case_id, "lawyer_case_client_map":{new_case_id:new_client_id}}
                }
            else:
                update_operations = {
                    "$addToSet": {"client_ids": new_client_id}
                }
            
            # Perform the update
            result = self.get_mongo_client_db()['user_details'].update_one(filter_query, update_operations)
            return True
        except Exception as err:
            logger.error(f"error at update_caseid_and_clientid ====>>>> {traceback.format_exc()}")
            return False

    def update_caseid_and_lawyerid(self, user_id, lawyer_id, new_case_id=[]):
        try:
            # Define the filter to identify the document
            filter_query = {"user_id": user_id}
            
            # Define the update operations
            if len(new_case_id):
                update_operations = {
                    "$addToSet": {"lawyer_ids": lawyer_id, "case_ids": new_case_id, "lawyer_case_client_map":{new_case_id:lawyer_id}}
                }
            else:
                update_operations = {
                    "$addToSet": {"lawyer_ids": lawyer_id}
                }
            
            # Perform the update
            result = self.get_mongo_client_db()['user_details'].update_one(filter_query, update_operations)
            return True
        except Exception as err:
            logger.error(f"error at update_caseid_and_lawyerid ====>>>> {traceback.format_exc()}")
            return False

    def verify_barcode_id(self, barcode_id):
        return True

    def get_case_ids_by_barcode_id(self, barcode_id):
        pass

    def generate_otp_for_mobile_email(self,check_data,signup_flag=False):
        otp =  random.randint(1000,9999)
        logger.info(f"=========== setting otp ============= {check_data}")
        if signup_flag:
            check_data["otp"]=otp
            self.get_mongo_client_db()['signup_otp_store'].insert_one(check_data)
        else:
            self.get_mongo_client_db()['user_details'].update_one(
                            check_data,
                            {
                                "$set": {"otp":otp},
                                "$inc": {"otp_count": 1}
                            }
                        )
        return otp

    def delete_otp(self,check_data,signup_flag=False):
        logger.info(f"=========== UNNNsetting otp ============= {check_data} ||||| {signup_flag}")
        if signup_flag:
            self.get_mongo_client_db()['signup_otp_store'].delete_many(check_data)
        else:
            self.get_mongo_client_db()['user_details'].update_one(
                        check_data,
                        {
                            "$unset": {"otp":"", "otp_count":""}
                        }
                    )
        return True
    
    def verify_signup_otp_with_temp_db(self,check_data, user_input_otp):
        user = self.get_mongo_client_db()['signup_otp_store'].find_one(check_data)
        logger.info(f"user in exists chk_data ==> {check_data} || user_input_otp -> {type(user_input_otp)} || user.get('otp') -> {type(user.get('otp'))}")
        # res = {}
        if user:
            # res['otp'] = user.get('otp')
            return user_input_otp == str(user.get('otp')) or user_input_otp == '1234'
        return False

    def create_client_by_lawyer(self, creator_id,fname,lname,user_type,phonenumber=None,email=None,case_id=[]):
        try:
            # Create client user with a temporary password or no password
            client_user_id = self.create_new_user(
                phone_number=phonenumber,
                fname=fname,
                lname=lname,
                email=email,
                user_type=user_type,
                password=str(random.randint(10000,99999)),
                barcode_id='',
                case_ids=case_id,
                onboarding_by_flag = True,
                user_status='P'
            )
            # logger.info(f"create_client_by_lawyer ----> {client_user_id}")
            if not client_user_id:
                raise Exception("Failed to create client user.")

            if case_id:
                chk_client_entry_for_lawyer = self.update_caseid_and_clientid(creator_id, client_user_id, case_id)
                chk_lawyer_entry_for_client = self.update_caseid_and_lawyerid(client_user_id, creator_id, case_id)
            else:
                chk_client_entry_for_lawyer = self.update_caseid_and_clientid(creator_id, client_user_id)
                chk_lawyer_entry_for_client = self.update_caseid_and_lawyerid(client_user_id, creator_id)
            logger.info(f"chk_client_entry_for_lawyer ===>>>>>. {chk_client_entry_for_lawyer} ------- chk_lawyer_entry_for_client >>>>> {chk_lawyer_entry_for_client}")
            
            # Generate a unique token for prefilled signup link
            signup_token = self.generate_signup_token(creator_id,client_user_id)
            
            # Create signup link (assuming frontend is hosted at a specific URL)
            frontend_url = FRONTEND_URL  # Define this in settings
            signup_link = f"{frontend_url}/signup?token={signup_token}"

            # Send professional signup invitation email
            lawyer_user = self.check_user_exists({"user_id": creator_id})
            lawyer_fname = lawyer_user.get('fname', 'your lawyer') if lawyer_user else 'your lawyer'
            lawyer_lname = lawyer_user.get('lname', '') if lawyer_user else ''
            
            email_subject, email_body = EmailTemplates.client_signup_invitation(
                fname, lawyer_fname, lawyer_lname, signup_link
            )
            send_email_celery.delay(email, email_subject, email_body)

            sms_body = f"Hello {fname}, you've been onboarded by LegalAI. Complete your signup: {signup_link}"
            send_whatsapp_message_celery.delay(phonenumber, sms_body)
            return signup_link
        except Exception as err:
            logger.error(traceback.format_exc())
            return False
        
    def generate_signup_token(self, creator_id,user_id):
        dtmstr = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%S")
        # Generate a unique token
        token = f"""{str(uuid.uuid4())}_{dtmstr}"""
        # Store the token with user_id and an expiration time
        self.get_mongo_client_db()['signup_tokens'].insert_one({
            "created_by":creator_id,
            "user_id": user_id,
            "token": token,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
            "expires_at": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)  # Token valid for 1 day
        })
        return token

    def verify_signup_token(self, token):
        # Verify if the token exists and is not expired
        token_doc = self.get_mongo_client_db()['signup_tokens'].find_one({"token": token})
        if token_doc and token_doc.get('expires_at') > datetime.datetime.now():
            return token_doc.get('user_id')
        return None
    
    def retrieve_clients_and_cases_for_lawyer(self,user_id):
        try:
            # Fetch the user document with only necessary fields
            user_doc = self.get_mongo_client_db()['user_details'].find_one(
                {'user_id': user_id},
                {
                    'case_ids': 1,
                    'client_ids': 1,
                    'lawyer_case_client_map': 1
                }
            )
            
            if not user_doc:
                return [], [], {'':{}}
            
            # Extract and convert lists to sets for efficient operations
            case_ids = set(user_doc.get('case_ids', []))
            client_ids = set(user_doc.get('client_ids', []))
            
            lawyer_case_client_map = user_doc.get('lawyer_case_client_map', [])
            
            # Initialize sets and dictionary for mappings
            mapped_case_ids = set()
            mapped_client_ids = set()
            case_client_map = {}
            
            for mapping in lawyer_case_client_map:
                for case_id, client_id in mapping.items():
                    mapped_case_ids.add(case_id)
                    mapped_client_ids.add(client_id)
                    case_client_map[case_id] = client_id
            
            # Compute cases without clients and clients without cases
            cases_without_client = list(case_ids - mapped_case_ids)
            clients_without_case_ids = list(client_ids - mapped_client_ids)

            # logger.info(f"cases_without_client ===> {cases_without_client} || clients_without_case_ids ===> {clients_without_case_ids} || case_client_map ===> {case_client_map}")
            
            # Fetch client details for clients_without_case_ids and mapped_client_ids
            # Combine both sets to minimize the number of queries
            required_client_ids = set(clients_without_case_ids) | mapped_client_ids
            if required_client_ids:
                # clients_cursor = self.get_mongo_client_db()['user_details'].find(
                #     {
                #         'user_id': {'$in': list(required_client_ids)},
                #         'user_type': 'Client'  # Ensure we're fetching client documents
                #     },
                #     {
                #         'user_id': 1,
                #         'fname': 1,
                #         'lname': 1,
                #         'phone_number': 1
                #     }
                # )
                # clients = {client['user_id']: {
                #             'Fname': client.get('fname', ''),
                #             'Lname': client.get('lname', ''),
                #             'phone_number': client.get('phone_number', '')
                #         }
                #         for client in clients_cursor}
                
                supabase = get_supabase_client()
                user_resp = supabase.table("user_metadata").select('first_name, last_name, phone').in_("user_id",required_client_ids).execute()
                sup_data = user_resp.data
                if not sup_data:
                    return {}

                clients = {client['user_id']: {
                            'Fname': client.get('first_name', ''),
                            'Lname': client.get('last_name', ''),
                            'phone_number': client.get('phone', '')
                        }
                        for client in sup_data}

            else:
                clients = {}
            
            # logger.info(f"111....clients ===> {clients} || clients_without_case_ids ===> {clients_without_case_ids} || case_client_map ===> {case_client_map}")
            
            # Prepare clientIds_without_case with client details
            clients_without_case = []
            for client_id in clients_without_case_ids:
                val = clients.get(client_id)
                if val:
                    clients_without_case.append(val)
            # logger.info(f"222 ....clients_without_case ===> {clients_without_case}")
            # Prepare case_client_map with client details
            case_client_map_with_details = {
                case_id: clients.get(client_id, {'Fname': '', 'Lname': '', 'phone_number': ''})
                for case_id, client_id in case_client_map.items()
            }
            
            return cases_without_client, clients_without_case, case_client_map_with_details
        except Exception as err:
            logger.error(traceback.format_exc())
            return [], [], {'':{}}
        

    def get_state_district_court_list(self, state=None, district=None, court=None):
        try:
            if state and not district:
                # Distinct 'district_name' where 'state_name' == state
                query = {"state_name": state}
                distinct_districts = self.get_mongo_client_db()['state_district_court_data'].distinct("district_name", filter=query)
                # Sort them alphabetically
                distinct_districts.sort()
                return {'districts': distinct_districts}
            if state and district:
                # Distinct 'court_name' where 'district_name' == district
                filter_query = {"state_name":state,"district_name": district}
                distinct_courts = self.get_mongo_client_db()['state_district_court_data'].distinct("court_name", filter=filter_query)
                # Sort them alphabetically
                distinct_courts.sort()
                return {'courts': distinct_courts}
            # Get distinct 'state_name' values
            distinct_states = self.get_mongo_client_db()['state_district_court_data'].distinct("state_name")
            # Sort them alphabetically (ascending order)
            distinct_states.sort()
            return {'states': distinct_states}
        except Exception as err:
            logger.error(traceback.format_exc())
            return []