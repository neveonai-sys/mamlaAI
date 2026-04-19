# import json
# import uuid
import os
# import re
import traceback
import datetime
import random
import jwt
import uuid
import logging
import string
import requests
# from django.conf import settings
from Legalv1.settings import FRONTEND_URL
from users.tasks import send_email_celery, update_onboarded_user_details, request_to_whatsapp_url, insert_new_user_details, create_userdetails_in_supabase_public_table
# from utilities.routes.utils import Handutilities
from core.init_clients import get_mongo_client, get_mongo_db, get_supabase_client
from core.email_templates import EmailTemplates

# Get the logger for this module
logger = logging.getLogger('django')

class Handleusermetadata:
    def __init__(self) -> None:
        pass

    def get_mongo_client_db(self):
        mongo = get_mongo_client()
        if not mongo:
            return ''
        db = get_mongo_db()
        return db

    def check_user_exists(self, key, val):
        try:
            supabase = get_supabase_client()
            if key == "phone":
                val = int(val)
            user = supabase.table("user_metadata").select("*").eq(key, val).execute()
            # logger.info(f"check_user_exists ---->>> {user}")
            res = {}
            if user.data:
                res['fname'] = user.data[0].get("first_name")
                res['lname'] = user.data[0].get("last_name")
                res['email_id'] = user.data[0].get("email")
                res['phone_number'] = user.data[0].get("phone")
                res['user_id'] = user.data[0].get("user_id")
                res['user_type'] = user.data[0].get("user_type")
            return res
        except Exception as err:
            logger.error(traceback.format_exc())
            return {}

    def sign_in_supabase(self, username_or_email, password):
        """
        By default, sign_in_with_password expects an email. If you want to login by 'username',
        either store username as an email or do a custom approach. 
        For simplicity, assume 'username' == actual email for sign in.
        """
        try:
            supabase = get_supabase_client()
            result = supabase.auth.sign_in_with_password(
                {"email": username_or_email, "password": password}
            )
            # logger.info(f"sign_in_supabase ---->>> {result}")
            if not result.user:
                raise Exception("Invalid credentials from Supabase sign_in.")
            res = {"access_token":result.session.access_token, "refresh_token":result.session.refresh_token, "fname":result.user.user_metadata.get('fname'), "lname":result.user.user_metadata.get('lname'), "user_id":result.user.user_metadata.get('user_id'), "user_type":result.user.user_metadata.get('user_type'), "email":result.user.email, "phone":result.user.user_metadata.get('phone')}

            if self.verify_user_status_in_mongo(res.get("user_id")):
                return res
            else:
                return False
        except Exception as err:
            logging.error(traceback.format_exc())
            return False
        
    def sign_out_supabase(self, scope):
        """
        Sign out a user from Supabase. 
        """
        try:
            supabase = get_supabase_client()
            options = { "scope": scope }
            supabase.auth.sign_out(options)
            return True
        except Exception as err:
            logger.error(traceback.format_exc())
            return False
    
    def reset_password(self, new_password, recovery_access_token):
        """
        Reset the password for a user. 
        """
        try:
            supabase = get_supabase_client()
            response = supabase.auth.update_user(recovery_access_token,{
                    "password": new_password
                    }
                )
            return True
        except Exception as err:
            logger.error(traceback.format_exc())
            return False

    def generate_password_reset_link(self, email_id):
        """
        Trigger supabase to generate reset link.
        The redirect_to URL must also be listed in the Supabase dashboard under
        Authentication → URL Configuration → Allowed Redirect URLs, otherwise
        Supabase falls back to the Site URL and strips the path.
        The frontend handles this fallback via a hash-detection redirect in AppContent.js.
        """
        try:
            supabase = get_supabase_client()
            redirect_url = f"{FRONTEND_URL}/reset-password"
            response = supabase.auth.reset_password_for_email(
                email_id,
                options={"redirect_to": redirect_url},
            )
            logger.info(f"generate_password_reset_link: reset link sent to {email_id}, redirect_to={redirect_url}")
            return True
        except Exception as err:
            logger.error(traceback.format_exc())
            return False

    def decode_supabase_jwt(self, token: str):
        """
        Decodes the Supabase JWT using the project's JWT secret.
        Raises an exception if invalid.
        """
        # Typically, Supabase uses HS256. Confirm in your Supabase JWT settings.
        # If you're unsure or want partial verification, see the docs re: options.
        try:
            payload = jwt.decode(
                token,
                os.getenv('SUPABASE_JWT_TOKEN'),
                algorithms=["HS256"],  # or a list if you have more
                options={"verify_aud": False}  # or True if you want to check "aud"
            )
            return payload
        except Exception as e:
            logger.error(traceback.format_exc())
            raise ValueError(f"Invalid token: {str(e)}")
        
    def verify_user_status_in_mongo(self, user_id):
        try:
            user = self.get_mongo_client_db()['user_details'].find_one({"user_id": user_id})
            if not user:
                return False
            # logger.info(f"verify_user_status_in_mongo -----> {user}")
            if user.get("user_status")=="A":
                return True
            return False
        except Exception as err:
            logger.error(traceback.format_exc())
            return False

    def verify_supabase_token(self,access_token: str):
        """
        Minimal approach: call supabase.auth.get_user(access_token)
        to see if it's valid.
        """
        supabase = get_supabase_client()
        resp = supabase.auth.get_user(access_token)
        if not resp or "user" not in resp:
            raise Exception("Invalid or expired Supabase token.")
        return resp["user"]
    

    def create_newuser_and_insert_metadata(self, phone_number, fname, lname, email, password, user_type, whatsappOptIn, agreedTnC, user_status, barcode_id=None, case_ids=[], state=None, district=None, courts=[], user_id=None, prefilled=False, organization=None):
        try:
            dtmstr = datetime.datetime.now(datetime.timezone.utc)
            user_id = user_id or self.generate_username(fname.lower(),lname.lower())+'_'+dtmstr.strftime("%Y%m%d%H%M%S")

            supabase = get_supabase_client()

            response = supabase.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "phone": phone_number,
                    "options": {
                        "data": {
                            "user_id": user_id,
                            "fname": fname,
                            "lname": lname,
                            "phone": phone_number,
                            "user_type": user_type,
                        }
                    },
                }
            )

            ## if client is not boarded by lawyer
            if not prefilled:
                user_details = {
                            "supabase_userid": response.user.id,
                            "supabase_created_at": response.user.created_at,
                            "user_id": user_id,
                            "phone_number": phone_number,
                            "user_type": user_type,
                            "whatsappOptIn": whatsappOptIn,
                            "agreedTnC": agreedTnC,
                            "user_status": user_status,
                            "barcode_id": barcode_id,
                            "organization": organization,
                            "case_ids": case_ids,
                            "state": state,
                            "district": district,
                            "courts": courts
                        }

                insert_new_user_details.delay(user_details)

                user_details_for_metadata = {
                            "user_id": user_id,
                            "fname": fname,
                            "lname": lname,
                            "phone": phone_number,
                            "email": email,
                            "user_type": user_type
                }

                create_userdetails_in_supabase_public_table.delay(user_details_for_metadata)
            else:
                user_details = {
                            "supabase_userid": response.user.id,
                            "supabase_created_at": response.user.created_at,
                            "user_id": user_id,
                            "phone_number": phone_number,
                            "whatsappOptIn": whatsappOptIn,
                            "agreedTnC": agreedTnC,
                            "user_status": 'A'
                        }

                update_onboarded_user_details.delay(user_details)
            return True
        except Exception as err:
            logger.error(traceback.format_exc())
            return False


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

    def send_whatsapp_message(self, phone_number):
        """
        Send a WhatsApp message. Return True if delivered, False if not.
        For demonstration, assume it's always successful.
        """
        payload = {
                "messaging_product": "whatsapp",
                "to": f'91{phone_number}',
                "type": "template",
                "template": {
                    "name": "onboard_user_template",
                    "language": {
                        "code": "en_US"
                    }
                }
            }

        logger.info(f"[DEBUG] Sending WhatsApp message PAYLOAD --> {payload}'")
        chk = request_to_whatsapp_url(payload)
        logger.info(f"[DEBUG] Sending WhatsApp message chk --> {chk}'")
        if chk.status_code == 200:
            return True
        else:
            return False
        
    def user_by_username_from_mongodb(self, username):
        try:
            user = self.get_mongo_client_db()['user_details'].find_one({"username": username})
            return user
        except Exception as err:
            logger.error(traceback.format_exc())
            return False
    
    def fetch_user_by_userid_from_suapbase(self, user_id):
        try:
            headers = {
                    "apikey": self.key,
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                }

            # Construct the URL for fetching a user (this endpoint format is illustrative;
            # refer to Supabase or GoTrue documentation for exact endpoints)
            url = f"{self.url}/auth/v1/admin/users/{user_id}"

            response = requests.get(url, headers=headers)
            if response.ok:
                user_data = response.json()
            return user_data
        except Exception as err:
            logger.error(traceback.format_exc())
            return False
        
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

            # Also include cases created directly in the cases collection
            # (create_case writes to `cases` with lawyer_id but does NOT update user_details.case_ids)
            for cdoc in self.get_mongo_client_db()['cases'].find({'lawyer_id': user_id}, {'_id': 1}):
                case_ids.add(str(cdoc['_id']))

            # Batch-fetch case titles for all known case IDs (single query)
            case_title_map = {}
            case_ids_list = list(case_ids)
            if case_ids_list:
                for cdoc in self.get_mongo_client_db()['cases'].find(
                    {'_id': {'$in': case_ids_list}}, {'_id': 1, 'title': 1}
                ):
                    case_title_map[str(cdoc['_id'])] = cdoc.get('title', '')

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
            cases_without_client = [
                {'case_id': cid, 'case_title': case_title_map.get(cid, '')}
                for cid in (case_ids - mapped_case_ids)
                if cid
            ]
            clients_without_case_ids = list(client_ids - mapped_client_ids)
            
            # Fetch client details for clients_without_case_ids and mapped_client_ids
            # Combine both sets to minimize the number of queries
            required_client_ids = set(clients_without_case_ids) | mapped_client_ids
            if required_client_ids:
                
                supabase = get_supabase_client()
                user_resp = supabase.table("user_metadata").select('first_name, last_name, phone, user_id').in_("user_id",required_client_ids).execute()
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
            # Prepare clientIds_without_case with client details
            clients_without_case = []
            for client_id in clients_without_case_ids:
                val = clients.get(client_id)
                if val:
                    clients_without_case.append({
                        **val,
                        'client_id': client_id,
                        'user_id': client_id,
                        'fname': val.get('Fname', ''),
                        'lname': val.get('Lname', ''),
                    })
            # Prepare case_client_map with client details
            # case_client_map_with_details = {
            #     case_id: clients.get(client_id, {'Fname': '', 'Lname': '', 'phone_number': ''})
            #     for case_id, client_id in case_client_map.items()
            # }

            # Build case_client_map_with_details, copying dicts to avoid shared-reference mutation bugs
            # and including case_title from the batch fetch above.
            case_client_map_with_details = {}
            for case_id, client_id in case_client_map.items():
                base = dict(clients.get(client_id, {'Fname': '', 'Lname': '', 'phone_number': ''}))
                base['case_title'] = case_title_map.get(case_id, '')
                case_client_map_with_details[case_id] = base

            # To avoid N+1, batch-fetch metadata for all client_ids in case_client_map
            # client_ids = list(case_client_map.keys())
            client_ids = list(case_client_map.values())  # these are the actual client IDs
            if client_ids:
                supabase = get_supabase_client()
                meta_resp = (
                  supabase
                    .table("user_metadata")
                    .select("user_id, email")
                    .in_("user_id", client_ids)
                    .execute()
                )
                email_map = {row["user_id"]: row["email"] for row in meta_resp.data}
            else:
                email_map = {}
        
            # Now enrich each entry with email and status
            for case_id, client_details in case_client_map_with_details.items():
                # look up the client_id that this case maps to:
                client_id = case_client_map[case_id]

                # assign email (or empty if not found)
                client_details["email"] = email_map.get(client_id, "")
                client_details["client_id"] = client_id
                client_details["user_id"] = client_id
                client_details["fname"] = client_details.get("Fname", "")
                client_details["lname"] = client_details.get("Lname", "")

                # fetch that client’s status from Mongo
                status_doc = self.get_mongo_client_db()['user_details'].find_one(
                    {'user_id': client_id},
                    {'user_status': 1}
                )
                client_details["status"] = status_doc.get("user_status") if status_doc else ""
            
            return cases_without_client, clients_without_case, case_client_map_with_details
        except Exception as err:
            logger.error(traceback.format_exc())
            return [], [], {'':{}}
        
    
    def create_client_by_lawyer(self, creator_id,fname,lname,user_type,phonenumber=None,email=None,case_id=[]):
        try:

            dtmstr = datetime.datetime.now(datetime.timezone.utc)
            client_user_id = self.generate_username(fname.lower(),lname.lower())+'_'+dtmstr.strftime("%Y%m%d%H%M%S")

            # supabase = get_supabase_client()
            # Create client user with a temporary password or no password
            user_details = {
                    "supabase_id": '',
                    "user_type": user_type,
                    "whatsappOptIn": '',
                    "agreedTnC": '',
                    "onboarding_time": dtmstr,
                    "last_updated_on": dtmstr,
                    "user_status": 'P',
                    "meetings":{},
                    }

            self.get_mongo_client_db()['user_details'].update_one(
                {"user_id": client_user_id},
                {
                    "$setOnInsert": {"user_id": client_user_id},
                    "$set": user_details,
                },
                upsert=True
            )

            user_details_for_metadata = {
                        "user_id": client_user_id,
                        "fname": fname,
                        "lname": lname,
                        "phone": phonenumber,
                        "email": email,
                        "user_type": user_type
            }

            create_userdetails_in_supabase_public_table.delay(user_details_for_metadata)
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
            lawyer_name = self.check_user_exists("user_id", creator_id)
            lawyer_fname = lawyer_name.get('fname', 'your lawyer') if lawyer_name else 'your lawyer'
            lawyer_lname = lawyer_name.get('lname', '') if lawyer_name else ''
            
            email_subject, email_body = EmailTemplates.client_signup_invitation(
                fname, lawyer_fname, lawyer_lname, signup_link
            )
            send_email_celery.delay(email, email_subject, email_body)

            sms_body = f"Hello {fname}, you've been onboarded by LegalAI. Complete your signup: {signup_link}"
            # send_whatsapp_message.delay(phonenumber, sms_body)
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

    def get_feedback(self, user_id, user_inputs):
        try:
            overall_feedback = user_inputs.get('overallFeedback', '')
            overall_rating = user_inputs.get('overallRating', 0)
            components = user_inputs.get('components', [])

            feedback_doc = {
                "overallFeedback": overall_feedback,
                "overallRating": overall_rating,
                "components": components,
                "user_id":user_id,
                "created_at": datetime.datetime.now(datetime.timezone.utc)
                }
            logger.info(f"feedback_doc ---> {feedback_doc}")
            result = self.get_mongo_client_db()['feedback_collection'].insert_one(feedback_doc)
            return True
        except Exception as err:
            logger.error(f"{err} ==> {traceback.format_exc()}")
            return False
