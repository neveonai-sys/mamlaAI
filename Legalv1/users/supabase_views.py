import json
import logging
import datetime
import traceback
from user_agents import parse
from django.middleware import csrf
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from supabase_required import supabase_required
from users.routes.session_manager import SessionManager
# from supabase_required import supabase_required
from rest_framework.decorators import api_view
from users.supabase_admin import admin_update_password
from users.routes.usermetadata import Handleusermetadata
from core.email_templates import EmailTemplates
from core.entitlements import get_entitlement_summary

from core.audit_log import audit_from_request, write_audit_log, ACTION_USER_LOGIN, ACTION_USER_LOGOUT, ACTION_LOGIN_FAILED

logger = logging.getLogger(__name__)


@api_view(['GET'])
@supabase_required
def check_auth(request):
    """
    Verify JWT access token and return authentication status with user and session details.
    """
    try:
        supabase_user = request.supabase_user
        # logger.info(f"Checking authentication for user_id: -------->>>>> {supabase_user}")
        user_id = supabase_user.get("user_id")
        # obj = Handleusermetadata()
        # user = obj.check_user_exists(user_id)
        if user_id:
            session_manager = SessionManager()
            sessions = session_manager.get_sessions(user_id)
            current_token = request.COOKIES.get('access_token')
            session_info = []
            for session in sessions:
                try:
                    login_time = session.get('login_time')
                    last_activity = session.get('last_activity')
                    if not login_time or not last_activity:
                        logger.warning(f"Session missing 'created_at' or 'last_activity': {session}")
                        continue  # Skip sessions without necessary fields

                    is_current = session['access_token'] == current_token

                    session_info.append({
                        'session_id': session['session_id'],
                        'ip_address': session['ip_address'],
                        'location': session['location'],
                        'device_type': session['device_type'],
                        'login_time': login_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'last_activity': last_activity.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_current': is_current
                    })
                except AttributeError as attr_err:
                    logger.error(f"AttributeError while processing session: {traceback.format_exc()}")
                    continue  # Skip this session and proceed with others
                except Exception as e:
                    logger.error(f"Unexpected error while processing session: {traceback.format_exc()}")
                    continue  # Skip this session and proceed with others

            return JsonResponse({
                'isAuthenticated': True,
                'firstname': supabase_user.get('fname'),
                'lastname': supabase_user.get('lname'),
                'email_id': supabase_user.get('email'),
                'user_type': supabase_user.get('user_type'),
                'sessions': session_info,
                'entitlements': get_entitlement_summary(supabase_user),
            })
        raise
    except Exception as err:
        logger.error(traceback.format_exc())
        return JsonResponse({'error message': str(err)}, status=500)


@api_view(['GET'])
@supabase_required
def entitlement_summary(request):
    return JsonResponse(get_entitlement_summary(request.supabase_user))

@api_view(['POST'])
@ratelimit(key='user', rate='5/m', block=True)
def onboarding_new_user(request):
    """
    POST /api/onboard
    Body: { "username": "...", "user_type": "Lawyer", "supabase_id": "...", ...}
    Called after supabase signUp from front-end to store domain data in your local DB.
    """
    try:
        req_body = json.loads(request.body.decode("utf-8"))
        logger.info(f"onboarding_new_user ------->>>> {req_body}")
        phone_number = req_body.get('phonenumber')
        fname = req_body.get('fname') or req_body.get('firstname')
        lname = req_body.get('lname') or req_body.get('lastname')
        email = req_body.get('email')
        password = req_body.get('password')
        user_type = req_body.get("user_type")
        barcode_id = req_body.get('barcode_id', '')
        case_ids = req_body.get('case_ids', [])
        if isinstance(case_ids, str):
            case_ids = case_ids.split(',')

        state = req_body.get('state', '')
        district = req_body.get('district', '')
        courts = req_body.get('courts', [])
        if isinstance(courts, str):
            courts = [courts]
        organization = req_body.get('organization', '')

        whatsapp_opt_in = req_body.get('whatsappOptIn', False)
        agreed_tnc = req_body.get('agreedTnC', False)
        obj = Handleusermetadata()
        chk = obj.create_newuser_and_insert_metadata(phone_number=phone_number, fname=fname, lname=lname, email=email, password=password, user_type=user_type, whatsappOptIn=whatsapp_opt_in, agreedTnC=agreed_tnc, user_status="A", barcode_id=barcode_id, case_ids=case_ids, state=state, district=district, courts=courts, organization=organization)
        if chk:
            return JsonResponse({"message": "Onboarded successfully."}, status=200)
        return JsonResponse({"message": "Onboarding Failed."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@api_view(['POST'])
def supabase_login(request):
    """
    POST /supabase/login/
    {
      "username_or_email": "...",
      "password": "..."
    }
    Returns {
      "access_token": "...",
      "refresh_token": "...",
      "user": {... user info ...}
    }
    """

    try:
        data = json.loads(request.body.decode("utf-8"))
        email = data.get("email")
        password = data.get("password")

        device_type_os = data.get('device_type')

        obj = Handleusermetadata()
        result = obj.sign_in_supabase(email, password)
        # logger.info(f"supabase_login ------>>>> {result}")
        if not result:
            write_audit_log(
                ACTION_LOGIN_FAILED,
                actor_id="",
                ip_address=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                metadata={"reason": "invalid_credentials"},
            )
            return JsonResponse({"error": "Invalid credentials/User Not Found"}, status=401)

        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")
        fname = result.get("fname")
        lname = result.get("lname")
        user_id = result.get("user_id")
        user_type = result.get("user_type")
        email_id = result.get("email_id")

        # Manage sessions
        session_manager = SessionManager()

        # Capture IP address and User-Agent
        ip_address = session_manager.get_client_ip(request)
        user_agent_string = request.META.get('HTTP_USER_AGENT', '')
        user_agent = parse(user_agent_string)
        device_type = f"{session_manager.get_device_type(user_agent)}-{device_type_os}"

        # Get location from IP address (using a geo-IP service)
        location = session_manager.get_location_from_ip(ip_address) or 'N/A'
        
        # Invalidate existing sessions if you want only one active session per user
        # session_manager.invalidate_sessions(user_id)

        # Create new session with encrypted IP and location
        #user_id, access_token, refresh_token, ip_address, location, device_type
        session_manager.create_session(user_id, access_token, refresh_token, ip_address, location, device_type)

        logger.info("User logged in: %s Device: %s IP: %s Location: %s", fname, device_type, ip_address, location)
        write_audit_log(
            ACTION_USER_LOGIN,
            actor_id=user_id,
            actor_type=user_type or "",
            ip_address=ip_address,
            user_agent=user_agent_string,
            metadata={"device_type": device_type, "location": location},
        )

        response = JsonResponse({
            'redirect': 'home',
            'email': email_id,
            'firstname': fname,
            'lastname': lname,
            'user_type': user_type,
            'access_token': access_token,  # used by native (Capacitor) clients only
        })

        # Set the access token in an HttpOnly, Secure cookie
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=True,  # Ensure HTTPS is used in production
            samesite='Lax',
            max_age=86400  # 7 day in seconds
        )

        # Set the refresh token in an HttpOnly, Secure cookie
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            httponly=True,
            secure=True,  # Ensure HTTPS is used in production
            samesite='Lax',
            max_age=604800  # 7 days in seconds
        )

        # Set CSRF token
        csrf_token = csrf.get_token(request)
        response.set_cookie('csrftoken', csrf_token, httponly=False, secure=True, samesite='Lax')
        # logger.info(f" resposne ------------ for ----------- login ----- ======= >>> {response}")
        return response
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=401)

@api_view(['POST'])
def reset_password(request):
    """
    POST 
    Body: { "new_password": """
    data = json.loads(request.body.decode("utf-8"))
    # logger.info(f"reset_password ==>>>> data === {data}")
    new_password = data.get("new_password")
    recovery_access_token = data.get("recovery_access_token") 
    obj = Handleusermetadata()
    # chk = obj.reset_password(passwd, recovery_access_token)
    if not recovery_access_token or not new_password:
            return JsonResponse({"message": "Missing fields"}, status=400)

    # 1) Decode & verify the token
    payload = obj.decode_supabase_jwt(recovery_access_token)
    user_id = payload.get("sub")
    if not user_id:
        return JsonResponse({"message": "Invalid token payload (no sub)"}, status=400)

    # 2) Update the password as an admin
    result = admin_update_password(user_id, new_password)
    # 'result' should contain info about the updated user or an error

    if result.user:  # check if user object is returned
        return JsonResponse({"success": True}, status=200)
    else:
        # Possibly check result.error, etc.
        return JsonResponse({
            "success": False,
            "message": "Failed to update user password"
        }, status=400)

@api_view(['POST'])
def send_reset_password_link(request):
    data = json.loads(request.body.decode("utf-8"))
    logger.info(f"send_reset_password_link ==>>>> data === {data}")
    email_id = data.get("email_id")
    obj = Handleusermetadata()
    chk = obj.generate_password_reset_link(email_id)
    if chk:
        return JsonResponse({"success": True}, status=200)
    return JsonResponse({"message": "Error resetting password."}, status=400)


@api_view(['POST'])
@supabase_required
def sign_out_supabase(request):
    """
    BODY: { "scope": "local"} [default: global], all session of the user will be deleted
    """
    try:
        access_token = request.COOKIES.get('access_token')

        data = json.loads(request.body.decode("utf-8"))
        scope = data.get("scope", "global")
        obj = Handleusermetadata()
        obj.sign_out_supabase(scope)
        
        if not access_token:
            return JsonResponse({'error_message': 'Access token is missing.'}, status=400)
        
        session_manager = SessionManager()
        session_manager.invalidate_session(access_token)
        audit_from_request(request, ACTION_USER_LOGOUT)

        response = JsonResponse({"message": "Successfully logged out."})
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        response.delete_cookie('csrftoken')
        return JsonResponse({"message": "Logged out successfully."}, status=200)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": "Error in signout handling"}, status=400)


@api_view(['POST'])
@supabase_required
def invalidate_session(request):
    """
    Invalidate a specific session by session_id.
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        session_id = request.data.get('session_id')
        if not session_id:
            return JsonResponse({'error_message': 'Session ID is required.'}, status=400)
        
        session_manager = SessionManager()
        res = session_manager.invalidate_session_by_session_id(session_id, user_id)
        
        if 'error' not in res:
            return JsonResponse(res, status=200)
        else:
            return JsonResponse(res, status=400)
    except Exception as e:
        logger.error(f"Error invalidating session: {traceback.format_exc()}")
        return JsonResponse({'error_message': 'An unexpected error occurred.'}, status=500)


@api_view(['POST'])
def check_username(request):
    """
    POST /api/auth/check-username
    Body: { "username": "msaha6" }
    Checks if there's a user in supabase.auth.users with user_metadata.username=msaha6
    Returns { found: true/false, email: "...", phone: "..." } if you want to reveal that
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
        username = body.get("username")
        if not username:
            return JsonResponse({"found": False, "error": "No username provided"}, status=400)

        ## not created yet
        obj = Handleusermetadata()
        user_obj = obj.find_user_by_username(username)
        logger.info(f"User found by username: {user_obj}")
        if not user_obj:
            return JsonResponse({"found": False}, status=200)

        # Optionally, return the user's email or phone if you want front-end to handle OTP
        # For example:
        user_email = user_obj.get("email", "")
        user_phone = user_obj.get("phone", "")
        return JsonResponse({"found": True, "email": user_email, "phone": user_phone}, status=200)
    except Exception as err:
        logger.error(traceback.format_exc())
        return JsonResponse({"found": False}, status=500)

    
@supabase_required
def get_profile(request):
    """
    GET /api/users/get-profile
    Must pass Bearer <access_token>. 
    We link supabase_user by user_metadata.username or supabase_id to domain data.
    """
    from users.models import user_collection
    supa_user = request.supabase_user
    user_meta = supa_user.get("user_metadata", {})
    username = user_meta.get("username", "")
    doc = user_collection.find_one({"username": username}) or {}
    return JsonResponse({
        "username": username,
        "email": supa_user.get("email", ""),
        "user_type": doc.get("user_type", "Client")
        # etc.
    }, status=200)


@api_view(['POST'])
def profile_update_of_client_onboarded_by_lawyer(request):
    """
    The main signup endpoint (no OTP).
    If 'token' is present, treat it as a prefilled signup.
    Otherwise standard signup.
    """
    try:
        req_body = request.data
        token = req_body.get('token')
        phone_number = req_body.get('phonenumber')
        fname = req_body.get('fname') or req_body.get('firstname')
        lname = req_body.get('lname') or req_body.get('lastname')
        email = req_body.get('email')
        user_type = req_body.get('user_type')
        password = req_body.get('password')
        case_ids = req_body.get('case_ids', [])
        if isinstance(case_ids, str):
            case_ids = case_ids.split(',')

        whatsapp_opt_in = req_body.get('whatsappOptIn')
        agreed_tnc = req_body.get('agreedTnC')

        obj = Handleusermetadata()

        # If it's token-based (prefilled) signup
        # if token:
        user_id = obj.verify_signup_token(token)
        if not user_id:
            return JsonResponse({'status': 'fail', 'message': 'Invalid or expired signup token.'}, status=400)

        existing_user = obj.check_user_exists("user_id", user_id)
        if not existing_user:
            return JsonResponse({'status': 'fail', 'message': 'User not found.'}, status=404)

        if not password:
            return JsonResponse({'status': 'fail', 'message': 'Password is required.'}, status=400)
        
        chk = obj.create_newuser_and_insert_metadata(phone_number=phone_number, fname=fname, lname=lname, email=email, password=password, user_type=user_type, whatsappOptIn=whatsapp_opt_in, agreedTnC=agreed_tnc, user_id=user_id, user_status="A", prefilled=True)

        if chk:
            return JsonResponse({"message": "Your signup is completed successfully, please verify from email link and whatsapp."}, status=200)
        else:
            raise Exception("Error in signup")
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({'status': 'fail', 'message': "error in signup"}, status=500)


@api_view(['POST'])
def get_prefilled_data(request):
    """
    Endpoint to fetch prefilled data based on signup token.
    """
    try:
        req_body = request.data
        token = req_body.get('token')

        if not token:
            return JsonResponse({'message': 'Token is required.'}, status=400)
        obj = Handleusermetadata()
        user_id = obj.verify_signup_token(token)
        if not user_id:
            return JsonResponse({'message': 'Invalid or expired token.'}, status=400)
        
        user = obj.check_user_exists("user_id", user_id)
        if not user:
            return JsonResponse({'message': 'User not found.'}, status=404)
        
        prefilled_data = {
            "fname": user.get('fname'),
            "lname": user.get('lname'),
            "phonenumber": user.get('phone_number'),
            "email": user.get('email_id'),
            "user_type": user.get('user_type'),
        }

        return JsonResponse(prefilled_data, status=200)
    except Exception as err:
        logger.error(traceback.format_exc())
        return JsonResponse({'message': str(err)}, status=500)


@api_view(['POST'])
def check_existing_user(request):
    """
    Endpoint to check if a user exists based on phone number or email.
    """
    try:
        req_body = request.data
        phone_number = req_body.get('phonenumber')
        email = req_body.get('email')
        logger.info(f"check_existing_user ====>>>>> {req_body}")
        if not (phone_number or email):
            return JsonResponse({'message': 'Phone number and email are required.'}, status=400)

        obj = Handleusermetadata()
        #check_user_exists(self, key, val)
        if phone_number:
            user = obj.check_user_exists("phone", phone_number)
        else:
            user = obj.check_user_exists("email", email)
        logger.info(f"check_existing_user ==   USER   ]]][[[[[ ==>>>>> {user}")
        if user:
            return JsonResponse({'exists': True}, status=200)
        else:
            return JsonResponse({'exists': False}, status=200)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=500)


@api_view(['POST'])
@supabase_required
def onboard_existing_client(request):
    """
    Endpoint to onboard an existing client by updating their details.
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        req_body = request.data
        logger.info(f"onboard_existing_client ====>>>>> {req_body}")
        client_phone_number = req_body.get('phonenumber')
        client_email = req_body.get('email')
        case_id = req_body.get('case_id')  # Optional

        if not (client_phone_number or client_email):
            return JsonResponse({'message': 'Phone number and email are required.'}, status=400)

        obj = Handleusermetadata()
        if client_phone_number:
            client_user = obj.check_user_exists("phone", client_phone_number)
        else:
            client_user = obj.check_user_exists("email", client_email)

        if not client_user:
            return JsonResponse({'message': 'User does not exist.'}, status=404)
            
        client_user_id = client_user.get('user_id')
        if case_id:
            chk_client_entry_for_lawyer = obj.update_caseid_and_clientid(user_id, client_user_id, case_id)
            chk_lawyer_entry_for_client = obj.update_caseid_and_lawyerid(client_user_id, user_id, case_id)
        else:
            chk_client_entry_for_lawyer = obj.update_caseid_and_clientid(user_id, client_user_id)
            chk_lawyer_entry_for_client = obj.update_caseid_and_lawyerid(client_user_id, user_id)

        return JsonResponse({'message': 'User onboarded successfully.'}, status=200)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=500)
    

@api_view(['POST'])
@supabase_required  # Ensure only authenticated users can onboard clients
def onboard_new_client(request):
    """
    Endpoint for Lawyers to onboard Clients.
    """
    try:
        # Verify that the user is a Lawyer
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        obj = Handleusermetadata()
        user = obj.check_user_exists("user_id", user_id)
        logger.info(f"onboard_new_client  == user ==>>>>> {user}")
        if not user or user.get('user_type') != 'Lawyer':
            return JsonResponse({'message': 'Unauthorized.'}, status=403)
        
        req_body = request.data
        fname = req_body.get('fname')
        lname = req_body.get('lname','')
        phonenumber = req_body.get('phonenumber')
        email = req_body.get('email','')
        case_id = req_body.get('case_id', [])

        # Basic validation
        if not all([fname, phonenumber]):
            return JsonResponse({'message': 'All required fields must be filled.'}, status=400)
        
        # Check if client already exists
        existing_client = obj.check_user_exists("phone", phonenumber)
        if existing_client:
            return JsonResponse({'message': 'Client with this Email/PhoneNumber already exists.'}, status=400)
        
        signup_link = obj.create_client_by_lawyer(creator_id=user_id,fname=fname,lname=lname,user_type='Client',phonenumber=phonenumber,email=email,case_id=case_id)

        return JsonResponse({'message': 'Client onboarded successfully.', 'signup_link': signup_link}, status=201)
    
    except Exception as err:
        logger.error(traceback.format_exc())
        return JsonResponse({'message': "Error creating User"}, status=500)


@api_view(['GET'])
@supabase_required
def filter_cases_clients_with_details(request):
    """
    GET API to filter case and client IDs based on userId and include client details.
    
    Query Parameters:
        - userId: The ID of the user to filter data for.
    
    Returns:
        JSON response with three sections:
            1. caseIds_without_client
            2. clientIds_without_case (with Fname, Lname, phone_number)
            3. case_client_map (caseId mapped to client details)
    """
    supa_user = request.supabase_user
    user_id = supa_user.get('user_id')
    obj = Handleusermetadata()
    cases_without_client, clients_without_case, case_client_map_with_details = obj.retrieve_clients_and_cases_for_lawyer(user_id)
    
    # Prepare the response
    response = {
        'caseIds_without_client': cases_without_client,
        'clientIds_without_case': clients_without_case,
        'case_client_map': case_client_map_with_details
    }
    
    return JsonResponse(response)

@api_view(['POST'])
@supabase_required
def submit_feedback(request):
    """
    Accepts POST requests with JSON payload containing:
    {
      "overallFeedback": <string>,
      "overallRating": <number>,
      "components": [
         { "componentName": <string>, "feedback": <string>, "rating": <number> },
         ...
      ]
    }
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        user_inputs = json.loads(request.body.decode('utf-8'))
        
        obj = Handleusermetadata()
        chk = obj.get_feedback(user_id, user_inputs)
        if chk:
            return JsonResponse({"message": "Feedback submitted successfully"})
        raise Exception("Feedback submission Fail")
    except Exception as e:
        logger.error("Error while inserting feedback:", e)
        return JsonResponse({"message":"Invalid data format or server error."}, status=500)


@api_view(['POST'])
@supabase_required
def add_case_client(request):
    """
    POST { case_id: '...', client_id: '...' }
    Updates the lawyer<->client mapping in Mongo.
    """
    data = json.loads(request.body)
    case_id   = data.get('case_id')
    client_id = data.get('client_id')

    logger.info(f"add_case_client ---> {data}")
    # if not case_id or not client_id:
    #     return JsonResponse({'error': 'case_id and client_id required'}, status=400)

    supa_user  = request.supabase_user
    lawyer_id  = supa_user.get('user_id')
    obj = Handleusermetadata()

    ok1 = obj.update_caseid_and_clientid(lawyer_id, client_id, case_id)
    ok2 = obj.update_caseid_and_lawyerid(client_id, lawyer_id, case_id)

    if ok1 and ok2:
        return JsonResponse({'message': 'Client added to case successfully'})
    else:
        logger.error(f"Failed to add client {client_id} to case {case_id} for lawyer {lawyer_id}")
        return JsonResponse({'error': 'Failed to update mapping'}, status=500)


# @api_view(['GET'])
# def list_feedback(request):
#     """
#     Returns a list of all feedback documents in JSON format.
#     For demonstration or admin usage.
#     """
#     from users.models import feedback_collection
#     feedback_list = list(feedback_collection.find({}))
#     # Convert ObjectId to string
#     for fb in feedback_list:
#         fb['_id'] = str(fb['_id'])

#     return JsonResponse(feedback_list, safe=False)

# ── REST-compatible client views ───────────────────────────────────────────────

@api_view(['GET'])
@supabase_required
def list_clients(request):
    """
    GET /api/users/clients/
    Returns flat list of clients for the logged-in lawyer.
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        obj = Handleusermetadata()
        cases_without_client, clients_without_case, case_client_map = obj.retrieve_clients_and_cases_for_lawyer(user_id)

        clients = {}
        # Add clients linked to cases
        for case_id, client_info in (case_client_map or {}).items():
            cid = client_info.get('client_id') or client_info.get('user_id', '')
            if cid:
                clients[cid] = {
                    "id": cid,
                    "client_id": cid,
                    "fname": client_info.get('fname', '') or client_info.get('Fname', ''),
                    "lname": client_info.get('lname', '') or client_info.get('Lname', ''),
                    "name": f"{client_info.get('fname', '') or client_info.get('Fname', '')} {client_info.get('lname', '') or client_info.get('Lname', '')}".strip(),
                    "email": client_info.get('email', ''),
                    "phone": client_info.get('phone_number', '') or client_info.get('phonenumber', ''),
                    "case_id": case_id,
                    "status": client_info.get('status', ''),
                }
        # Add clients without cases
        for client_info in (clients_without_case or []):
            cid = client_info.get('client_id') or client_info.get('user_id', '')
            if cid and cid not in clients:
                clients[cid] = {
                    "id": cid,
                    "client_id": cid,
                    "fname": client_info.get('fname', '') or client_info.get('Fname', ''),
                    "lname": client_info.get('lname', '') or client_info.get('Lname', ''),
                    "name": f"{client_info.get('fname', '') or client_info.get('Fname', '')} {client_info.get('lname', '') or client_info.get('Lname', '')}".strip(),
                    "email": client_info.get('email', ''),
                    "phone": client_info.get('phone_number', '') or client_info.get('phonenumber', ''),
                    "case_id": None,
                    "status": client_info.get('status', ''),
                }

        result = list(clients.values())
        search = request.GET.get('search', '').strip().lower()
        if search:
            result = [
                c for c in result
                if search in (c.get('name') or '').lower()
                or search in (c.get('email') or '').lower()
                or search in (c.get('phone') or '')
            ]
        return JsonResponse({"results": result, "count": len(result)})
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"results": [], "count": 0, "error": str(e)}, status=500)


@api_view(['PUT'])
@supabase_required
def update_client_detail(request, client_id):
    """
    PUT /api/users/clients/<client_id>/
    Body: {fname, lname, email, phone, ...}
    """
    try:
        from core.init_clients import get_mongo_client, get_mongo_db
        data = json.loads(request.body or b"{}")
        allowed = {k: v for k, v in data.items() if k in ('fname', 'lname', 'email', 'phonenumber', 'phone_number', 'address', 'notes')}
        if not allowed:
            return JsonResponse({"error": "No updatable fields provided"}, status=400)
        db = get_mongo_db()
        res = db['user_details'].update_one({"user_id": client_id}, {"$set": allowed})
        if res.matched_count:
            return JsonResponse({"message": "Updated"})
        return JsonResponse({"error": "Client not found"}, status=404)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['POST'])
@supabase_required
def invite_client_handler(request):
    """
    POST /api/users/invite_client/
    Body: {fname, lname, email, phonenumber, case_id (optional)}
    Wraps the existing onboard_new_client logic.
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get('user_id')
        data = json.loads(request.body or b"{}")

        fname = data.get('fname', '').strip()
        lname = data.get('lname', '').strip()
        email = data.get('email', '').strip()
        phonenumber = data.get('phonenumber', '').strip()
        case_id = data.get('case_id', '')

        if not phonenumber and not email:
            return JsonResponse({"error": "phonenumber or email required"}, status=400)
        if not fname:
            return JsonResponse({"error": "fname required"}, status=400)

        obj = Handleusermetadata()
        existing = obj.check_user_exists("phone", phonenumber) if phonenumber else obj.check_user_exists("email", email)
        if existing:
            client_user_id = existing.get('user_id')
            if case_id:
                obj.update_caseid_and_clientid(user_id, client_user_id, case_id)
                obj.update_caseid_and_lawyerid(client_user_id, user_id, case_id)
            else:
                obj.update_caseid_and_clientid(user_id, client_user_id)
                obj.update_caseid_and_lawyerid(client_user_id, user_id)
            return JsonResponse({"message": "Existing client linked", "client_id": client_user_id})

        signup_link = obj.create_client_by_lawyer(
            creator_id=user_id, fname=fname, lname=lname,
            user_type='Client', phonenumber=phonenumber, email=email, case_id=case_id
        )
        new_client = obj.check_user_exists("phone", phonenumber) if phonenumber else obj.check_user_exists("email", email)
        new_client_id = new_client.get('user_id') if new_client else None
        return JsonResponse({"message": "Invite sent", "signup_link": signup_link, "client_id": new_client_id})
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['PATCH'])
@supabase_required
def update_client_status(request, client_id):
    """
    PATCH /api/users/clients/<client_id>/status/
    Body: {"status": "A" | "I"}
    Allows a lawyer to activate ("A") or deactivate ("I") a client.
    """
    try:
        supa_user = request.supabase_user
        lawyer_id = supa_user.get('user_id')
        data = json.loads(request.body or b'{}')
        new_status = (data.get('status') or '').strip().upper()
        if new_status not in ('A', 'I'):
            return JsonResponse({'error': 'status must be "A" (active) or "I" (inactive)'}, status=400)

        obj = Handleusermetadata()
        db = obj.get_mongo_client_db()

        # Ownership check: lawyer must have this client in their client_ids
        lawyer_doc = db['user_details'].find_one({'user_id': lawyer_id}, {'client_ids': 1})
        if not lawyer_doc or client_id not in (lawyer_doc.get('client_ids') or []):
            return JsonResponse({'error': 'Client not associated with your account'}, status=403)

        res = db['user_details'].update_one({'user_id': client_id}, {'$set': {'user_status': new_status}})
        if not res.matched_count:
            return JsonResponse({'error': 'Client not found'}, status=404)
        return JsonResponse({'message': 'Status updated', 'status': new_status})
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@supabase_required
def resend_client_invite(request, client_id):
    """
    POST /api/users/clients/<client_id>/resend-invite/
    Body: {"email": "..."} (optional — adds/updates email before sending invite)
    Generates a fresh signup token and sends an invite email.
    Only valid for pending clients (user_status = "P" and no supabase_id).
    Returns 400 if the client has already registered.
    """
    try:
        from Legalv1.settings import FRONTEND_URL
        from users.tasks import send_email_celery
        from core.init_clients import get_supabase_client

        supa_user = request.supabase_user
        lawyer_id = supa_user.get('user_id')
        data = json.loads(request.body or b'{}')

        obj = Handleusermetadata()
        db = obj.get_mongo_client_db()

        # Ownership check: lawyer must have this client in their client_ids
        lawyer_doc = db['user_details'].find_one({'user_id': lawyer_id}, {'client_ids': 1})
        if not lawyer_doc or client_id not in (lawyer_doc.get('client_ids') or []):
            return JsonResponse({'error': 'Client not associated with your account'}, status=403)

        client_doc = db['user_details'].find_one({'user_id': client_id})
        if not client_doc:
            return JsonResponse({'error': 'Client not found'}, status=404)

        # Block if the client has already signed up (supabase_id is set)
        if client_doc.get('supabase_id'):
            return JsonResponse({'error': 'Client has already registered'}, status=400)

        # Optionally update email if provided in the request body
        email = (data.get('email') or '').strip()
        if email:
            db['user_details'].update_one({'user_id': client_id}, {'$set': {'email': email}})
            try:
                supabase = get_supabase_client()
                supabase.table('user_metadata').update({'email': email}).eq('user_id', client_id).execute()
            except Exception:
                logger.warning(f'resend_client_invite: could not sync email to Supabase for {client_id}')
        else:
            # Fall back to stored email
            try:
                supabase = get_supabase_client()
                resp = supabase.table('user_metadata').select('email').eq('user_id', client_id).single().execute()
                email = (resp.data or {}).get('email') or client_doc.get('email') or ''
            except Exception:
                email = client_doc.get('email') or ''

        if not email:
            return JsonResponse({'error': 'Email is required to send an invite'}, status=400)

        # Get client first name for the email body
        try:
            supabase = get_supabase_client()
            meta_resp = supabase.table('user_metadata').select('first_name').eq('user_id', client_id).single().execute()
            fname = (meta_resp.data or {}).get('first_name') or client_doc.get('fname') or 'there'
        except Exception:
            fname = client_doc.get('fname') or 'there'

        # Get lawyer name for the email body
        lawyer_data = obj.check_user_exists('user_id', lawyer_id) or {}
        lawyer_fname = lawyer_data.get('fname') or 'your lawyer'
        lawyer_lname = lawyer_data.get('lname') or ''

        # Generate a fresh signup token and build the invite link
        signup_token = obj.generate_signup_token(lawyer_id, client_id)
        signup_link = f"{FRONTEND_URL}/signup?token={signup_token}"

        # Send the invite email asynchronously
        email_subject, email_body = EmailTemplates.client_signup_invitation(fname, lawyer_fname, lawyer_lname, signup_link)
        send_email_celery.delay(email, email_subject, email_body)

        return JsonResponse({'message': 'Invite sent', 'signup_link': signup_link})
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
def save_consent_event(request):
    """
    POST /api/users/consent-events/
    Body: {
      "consent_type": "cookie_preferences" | "terms_of_service" | etc,
      "version": "1.0",
      "preferences": {...},
      "source": "web" | "mobile" | "admin"
    }
    
    Saves consent events to MongoDB for audit purposes.
    Works with or without authentication (for anonymous users).
    If authenticated, links to user_id.
    """
    try:
        data = json.loads(request.body or b'{}')
        consent_type = data.get('consent_type', '').strip()
        preferences = data.get('preferences', {})
        source = data.get('source', 'web').strip()

        if not consent_type:
            return JsonResponse({'error': 'consent_type is required'}, status=400)

        # Use server-authoritative version for legal docs; fall back to client-supplied.
        from core.legal_versions import LEGAL_DOC_VERSIONS, SERVER_AUTHORITATIVE_TYPES
        if consent_type in SERVER_AUTHORITATIVE_TYPES:
            version = LEGAL_DOC_VERSIONS.get(consent_type, '1.0')
        else:
            version = data.get('version', LEGAL_DOC_VERSIONS.get(consent_type, '1.0')).strip()

        # Try to extract user_id from authenticated request
        user_id = None
        if hasattr(request, 'supabase_user'):
            user_id = request.supabase_user.get('user_id')

        # Capture IP and User-Agent
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Get MongoDB client
        from core.init_clients import get_mongo_client, get_mongo_db
        db = get_mongo_db()

        # Build consent document
        consent_doc = {
            'consent_type': consent_type,
            'version': version,
            'preferences': preferences,
            'source': source,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': datetime.datetime.utcnow(),
        }

        if user_id:
            consent_doc['user_id'] = user_id

        # Insert into consent_events collection
        result = db['consent_events'].insert_one(consent_doc)

        # If authenticated, optionally update user_details with latest consent summary
        if user_id:
            db['user_details'].update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        f'consent_{consent_type}_version': version,
                        f'consent_{consent_type}_updated_at': datetime.datetime.utcnow(),
                    }
                }
            )

        logger.info(f"Consent event saved: {consent_type} for user_id={user_id}")
        return JsonResponse({'message': 'Consent recorded', 'event_id': str(result.inserted_id)})
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@supabase_required
def export_user_data(request):
    """
    GDPR/DPDP data export — returns all stored data for the authenticated user.
    GET /api/users/privacy/export-data/
    """
    try:
        from core.init_clients import get_mongo_db
        db = get_mongo_db()
        user_id = request.supabase_user.get('user_id')

        profile = db['user_details'].find_one({'user_id': user_id}, {'_id': 0})

        usage_events = list(db['usage_events'].find(
            {'user_id': user_id},
            {'_id': 0, 'ip_address': 0, 'user_agent': 0},
        ).sort('timestamp', -1).limit(500))
        for e in usage_events:
            if 'timestamp' in e:
                e['timestamp'] = e['timestamp'].isoformat()

        consent_events = list(db['consent_events'].find(
            {'user_id': user_id},
            {'_id': 0, 'ip_address': 0, 'user_agent': 0},
        ).sort('created_at', -1))
        for c in consent_events:
            if 'created_at' in c:
                c['created_at'] = c['created_at'].isoformat()

        subscription = db['subscriptions'].find_one({'user_id': user_id}, {'_id': 0})
        if subscription:
            for k in ('created_at', 'updated_at', 'cancelled_at', 'current_period_start', 'current_period_end'):
                if subscription.get(k):
                    subscription[k] = subscription[k].isoformat()

        from core.audit_log import ACTION_EXPORT_USER_DATA
        audit_from_request(request, ACTION_EXPORT_USER_DATA)
        return JsonResponse({
            'user_id': user_id,
            'profile': profile or {},
            'usage_events': usage_events,
            'consent_events': consent_events,
            'subscription': subscription or {},
            'exported_at': datetime.datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@supabase_required
def delete_user_data(request):
    """
    GDPR/DPDP right to erasure — anonymises stored data for the authenticated user.
    Preserves billing records (legal/financial hold) but removes PII.
    POST /api/users/privacy/delete-data/
    Body: {"confirm": true}
    """
    try:
        import json as _json
        body = _json.loads(request.body or '{}')
        if not body.get('confirm'):
            return JsonResponse({'error': 'Send {"confirm": true} to confirm deletion'}, status=400)

        from core.init_clients import get_mongo_db
        db = get_mongo_db()
        user_id = request.supabase_user.get('user_id')
        now = datetime.datetime.utcnow()

        db['user_details'].update_one(
            {'user_id': user_id},
            {'$set': {
                'email': f'deleted_{user_id}@deleted.invalid',
                'phone': '',
                'full_name': 'Deleted User',
                'bar_registration': '',
                'deleted_at': now,
                'deletion_requested_at': now,
            }},
        )

        db['usage_events'].update_many(
            {'user_id': user_id},
            {'$set': {'ip_address': '', 'user_agent': ''}},
        )

        db['consent_events'].update_many(
            {'user_id': user_id},
            {'$set': {'ip_address': '', 'user_agent': ''}},
        )

        from core.audit_log import ACTION_DELETE_USER_DATA
        audit_from_request(request, ACTION_DELETE_USER_DATA, metadata={'initiated_by': 'self'})

        logger.info('[Privacy] Data deletion completed for user_id=%s', user_id)
        return JsonResponse({
            'status': 'deleted',
            'user_id': user_id,
            'deleted_at': now.isoformat(),
            'note': 'Billing/invoice records are retained as required by financial regulations.',
        })
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
def legal_doc_versions(request):
    """
    GET /api/users/legal-doc-versions/

    Returns the current canonical version of every legal document.
    Frontend uses this before showing T&C / Privacy dialogs so it can
    detect whether the user has accepted the latest version.
    """
    from core.legal_versions import LEGAL_DOC_VERSIONS
    return JsonResponse({'versions': LEGAL_DOC_VERSIONS})
