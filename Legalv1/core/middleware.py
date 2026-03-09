"""
Middleware for dev-only auth bypass when testing API locally (e.g. Swagger).
Only active when DEBUG=True. Use header X-Dev-Bypass-Auth: 1 or query ?dev_auth=1.
"""
import logging
from django.conf import settings

logger = logging.getLogger("django")

DEV_BYPASS_USER = {
    "user_id": "dev-swagger",
    "email": "dev@local",
    "sub": "dev-swagger",
}


class DevAuthBypassMiddleware:
    """
    When DEBUG is True and the request has header X-Dev-Bypass-Auth: 1 or query dev_auth=1,
    set bypass_supabase_auth and a fake supabase_user so @supabase_required endpoints
    can be tested without a real Supabase token.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            header = request.headers.get("X-Dev-Bypass-Auth", "").strip()
            query = request.GET.get("dev_auth", "").strip()
            if header == "1" or query == "1":
                request.bypass_supabase_auth = True
                request.supabase_user = DEV_BYPASS_USER.copy()
                logger.debug("[DevAuthBypass] Bypassing auth for %s %s", request.method, request.path)
        response = self.get_response(request)
        return response
