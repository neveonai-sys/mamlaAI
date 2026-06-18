import traceback
from functools import wraps
from django.http import JsonResponse
from core.init_clients import get_supabase_client
import logging

logger = logging.getLogger('django')

def verify_supabase_token(access_token: str):
    """
    Verify a Supabase access token.
    Returns the user metadata if valid, raises an exception otherwise.
    """
    sb = get_supabase_client()
    resp = sb.auth.get_user(access_token)
    if not resp:
        raise Exception("Invalid or expired Supabase token.")
    return resp.user.user_metadata

def supabase_required(view_func):
    """
    Decorator that checks for a valid Supabase access token.
    Can be bypassed if request.bypass_supabase_auth is True.
    """
    @wraps(view_func)
    def decorated_function(request, *args, **kwargs):
        # Check if authentication should be bypassed for this request
        if getattr(request, 'bypass_supabase_auth', False):
            # logger.debug("[supabase_required] Bypassing auth check for test endpoint")
            # Ensure we have an anonymous user
            if not hasattr(request, 'user') or request.user.is_anonymous:
                from django.contrib.auth.models import AnonymousUser
                request.user = AnonymousUser()
            return view_func(request, *args, **kwargs)
            
        # Normal authentication flow
        access_token = request.COOKIES.get('access_token')
        # Also support Authorization header (Bearer or raw)
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header:
                # Support 'Bearer <token>' or just the token
                if auth_header.lower().startswith('bearer '):
                    access_token = auth_header[7:].strip()
                else:
                    access_token = auth_header.strip()
        
        if not access_token:
            logger.warning("[supabase_required] No access token provided")
            return JsonResponse({"error": "Authentication required"}, status=401)
            
        try:
            supabase_user = verify_supabase_token(access_token)
            request.supabase_user = supabase_user
            # Update log context now that we have the real user identity
            uid = supabase_user.get('user_id') or supabase_user.get('email', 'authenticated')
            try:
                from core.log_filters import set_log_context
                set_log_context(getattr(request, 'request_id', '-'), uid)
                request.telemetry_user_id = uid
            except Exception:
                pass
            return view_func(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"[supabase_required] Authentication failed: {str(e)}")
            logger.error(traceback.format_exc())
            return JsonResponse({"error": "Invalid or expired authentication"}, status=401)
            
    return decorated_function
