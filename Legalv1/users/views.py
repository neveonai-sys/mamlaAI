from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
from rest_framework.decorators import api_view
from users.routes.checkusers import Handleuserdata
import uuid
import traceback
from .tasks import send_email_celery
from core.email_templates import EmailTemplates
import logging
import datetime

logger = logging.getLogger('django')


@api_view(['POST'])
def signup_user(request):
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
        password = req_body.get('password')
        user_type = req_body.get('type')
        barcode_id = req_body.get('barcodeid', '')
        case_ids = req_body.get('case_ids', [])
        if isinstance(case_ids, str):
            case_ids = case_ids.split(',')

        state = req_body.get('state', '')
        district = req_body.get('district', '')
        courts = req_body.get('courts', [])
        if isinstance(courts, str):
            courts = [courts]

        whatsapp_opt_in = req_body.get('whatsappOptIn', False)
        agreed_tnc = req_body.get('agreedTnC', False)

        obj = Handleuserdata()

        # If it's token-based (prefilled) signup
        if token:
            user_id = obj.verify_signup_token(token)
            if not user_id:
                return JsonResponse({'status': 'fail', 'message': 'Invalid or expired signup token.'}, status=400)

            existing_user = obj.check_user_exists({"user_id": user_id})
            if not existing_user:
                return JsonResponse({'status': 'fail', 'message': 'User not found.'}, status=404)

            if not password:
                return JsonResponse({'status': 'fail', 'message': 'Password is required.'}, status=400)

            hashed_password = obj.hash_password(password)
            # For token-based finalization, you might skip the email verification flow
            # or possibly re-trigger a new verification link. It's up to you.
            update_data = {
                "phone_number": phone_number or existing_user.get('phone_number'),
                "fname": fname or existing_user.get('fname'),
                "lname": lname or existing_user.get('lname'),
                "email": email or existing_user.get('email'),
                "password": hashed_password,
                "last_updated_on": datetime.datetime.now(datetime.timezone.utc),
                "whatsappOptIn": bool(whatsapp_opt_in),
                "agreedTnC": bool(agreed_tnc),
                # Force them to re-verify? or skip?
                "email_verification": 'Pending',
                "whatsapp_verification": 'Pending',
                "user_status": 'P'  # 'P' for pending?
            }
            obj.update_user_detail(user_id, update_data)

            # Send verification link and WhatsApp message again if needed
            # But let's say we do that:
            new_user = obj.check_user_exists({"user_id": user_id})
            email_verify_token = str(uuid.uuid4())
            expiry_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
            obj.update_user_detail(user_id, {
                "email_verification_token": email_verify_token,
                "email_verification_expiry": expiry_time
            })

            # Send verification email link
            email_chk = obj.send_email_verification_link(email, email_verify_token, fname)

            # If user opted for WhatsApp, send a message
            if whatsapp_opt_in:
                whatsapp_chk = obj.send_whatsapp_message(phone_number, "Welcome to our platform!")

                ##TODO: after whatsapp impelemengtation consider this if condition
                # if whatsapp_chk:
                    # If delivered, update DB
                # else:
                    # delete the user entry ## or the signup process will change we'll first verify OTP for both then will proceed here.
                obj.update_user_detail(user_id, {"whatsapp_verification": "A"})
                # Then if email_verification is also 'A', set user_status='A'
                updated_user = obj.check_user_exists({"user_id": user_id})
                if updated_user.get("email_verification") == 'A':
                    obj.update_user_detail(user_id, {"user_status": "A"})

            ## for now whatsapp verification is not considered
            if email_chk :
                return JsonResponse({'status': 'success', 'message': 'Signup completed. Check your email & WhatsApp.'}, status=201)
    
            if email_chk and whatsapp_chk:
                return JsonResponse({'status': 'success', 'message': 'Signup completed. Check your email & WhatsApp.'}, status=201)
            elif email_chk and not whatsapp_chk:
                return JsonResponse({'status': 'error', 'message': 'Verify WhatsApp, message sending failed'}, status=400)
            elif not email_chk and whatsapp_chk:
                return JsonResponse({'status': 'error', 'message': 'Verify Email, mail sending failed'}, status=400)
            elif not email_chk and not whatsapp_chk:
                return JsonResponse({'status': 'error', 'message': 'Verify Email and WhatsApp, unable to send mail or message'}, status=400)

        else:
            # Standard signup
            if not all([phone_number, fname, email, user_type, password]):
                return JsonResponse({'status': 'fail', 'message': 'All required fields not provided'}, status=400)

            # Additional validations
            if user_type == 'Lawyer' and not barcode_id:
                return JsonResponse({'status': 'fail', 'message': 'Barcode ID is required for Lawyer'}, status=400)
            if user_type == 'Paralegal':
                if not state or not district or not courts:
                    return JsonResponse({'status': 'fail', 'message': 'State, District, Courts required for Paralegal'}, status=400)

            # Create the user in DB
            user_status = 'P'  # 'P' for "Pending final verification"
            user_id, email_verify_token = obj.create_new_user(
                phone_number, fname, lname, email, user_type, password,
                user_status, barcode_id, case_ids, state, district, courts,
                bool(whatsapp_opt_in), bool(agreed_tnc)
            )
            if not user_id:
                raise Exception("User creation failed")

            # Send verification link (within 24 hours)
            email_chk = obj.send_email_verification_link(email, email_verify_token, fname)

            # If user opted for WhatsApp, send welcome message
            if whatsapp_opt_in:
                whatsapp_chk = obj.send_whatsapp_message(phone_number, "Welcome to our platform!")
                # for now commenting as whatsapp check is not verified
                # if whatsapp_chk:
                    # Mark whatsapp_verification='A'
                obj.update_user_detail(user_id, {"whatsapp_verification": "A"})

            if email_chk and whatsapp_chk:
                return JsonResponse({'status': 'success', 'message': 'User registered successfully'}, status=201)
            elif email_chk and not whatsapp_chk:
                return JsonResponse({'status': 'error', 'message': 'Verify WhatsApp, message sending failed'}, status=400)
            elif not email_chk and whatsapp_chk:
                return JsonResponse({'status': 'error', 'message': 'Verify Email, mail sending failed'}, status=400)
            elif not email_chk and not whatsapp_chk:
                return JsonResponse({'status': 'error', 'message': 'Verify Email and WhatsApp, unable to send mail or message'}, status=400)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({'status': 'fail', 'message': "error in signup"}, status=500)

@api_view(['GET'])
def verify_email(request):
    """
    GET endpoint: /users/verify-email?token=...
    Mark email_verification='A' if valid and not expired.
    If whatsapp_verification=='A' as well, set user_status='A'.
    If expired or invalid, either return error or delete user from DB.
    """
    from users.models import user_collection
    try:
        logger.info(f"verify_email ===========>>>> {request.GET}")
        token = request.GET.get('token')
        if not token:
            return JsonResponse({'status': 'fail', 'message': 'No token provided'}, status=400)
        # obj = Handleuserdata()
        user = user_collection.find_one({"email_verification_token": token})
        if not user:
            return JsonResponse({'status': 'fail', 'message': 'Invalid token'}, status=400)
        # logger.info(f"verify_email =========== user  >>>> {user}")
        # Check if 24 hours have passed
        now = datetime.datetime.now(datetime.timezone.utc)
        expiry_datetime = user.get("email_verification_expiry").replace(tzinfo=datetime.timezone.utc)
        # expiry_datetime = datetime.datetime.utcfromtimestamp(expiry_datetime["$date"]["$numberLong"] / 1000)
        if now > expiry_datetime:
            # Delete user or mark them invalid
            user_collection.delete_one({"user_id": user["user_id"]})
            return JsonResponse({'status': 'fail', 'message': 'Token expired. User removed.'}, status=400)

        # If token is valid within the time
        user_collection.update_one({"user_id": user["user_id"]}, {
            "$set": {
                "email_verification": "A",
                "email_verification_token": None,  # or remove token
                "email_verification_expiry": None
            }
        })

        # If the user's WhatsApp is also verified, set user_status='A'
        updated_user = user_collection.find_one({"user_id": user["user_id"]})
        # for now commenting as whatsapp check is not verified
        # if updated_user.get("whatsapp_verification") == 'A':
        user_collection.update_one({"user_id": user["user_id"]}, {"$set": {"user_status": "A"}})

        # Send professional welcome email
        email_subject, email_body = EmailTemplates.welcome_email(
            updated_user.get('fname'),
            updated_user.get('user_id')
        )
        send_email_celery.delay(updated_user.get('email'), email_subject, email_body)

        # Prepare a redirect URL
        # redirect_url = "https://mamla.ai/login"
        # return JsonResponse({
        #     'status': 'success',
        #     'message': 'Email verified successfully. Redirecting...',
        #     'redirect_url': redirect_url
        # }, status=200)
        return redirect(f"{settings.FRONTEND_URL}/login")
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({'status': 'fail', 'message': str(e)}, status=500)

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
        obj = Handleuserdata()
        user_id = obj.verify_signup_token(token)
        if not user_id:
            return JsonResponse({'message': 'Invalid or expired token.'}, status=400)
        
        user = obj.check_user_exists({"user_id": user_id})
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
def verify_barcode(request):
    obj = Handleuserdata()
    barcode_id = request.data.get('barcode_id', '')
    if not barcode_id:
        return JsonResponse({'status': 'fail', 'message': 'No barcode_id provided'}, status=400)
    # Check if barcode_id is valid
    if obj.verify_barcode_id(barcode_id):  # Implement this check
        return JsonResponse({'status': 'success', 'message': 'Barcode is valid'})
    else:
        return JsonResponse({'status': 'fail', 'message': 'Invalid barcode'}, status=400)


@api_view(['GET'])
def get_states(request):
    # Fetch states from DB or any source
    obj = Handleuserdata()
    res = obj.get_state_district_court_list()
    return JsonResponse(res, status=200)

@api_view(['GET'])
def get_districts(request):
    state = request.GET.get('state', '').strip()
    if not state:
        return JsonResponse({'error': 'state query parameter is required.'}, status=400)
    obj = Handleuserdata()
    res = obj.get_state_district_court_list(state=state)
    return JsonResponse(res, status=200)

@api_view(['GET'])
def get_courts(request):
    state = request.GET.get('state', '').strip()
    district = request.GET.get('district', '').strip()
    if not district:
        return JsonResponse({'error': 'district query parameter is required.'}, status=400)
    obj = Handleuserdata()
    res = obj.get_state_district_court_list(state=state,district=district)
    return JsonResponse(res, status=200)


