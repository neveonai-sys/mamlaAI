"""
Telemetry middleware for request tracking.

Generates a unique request_id for every request and attaches user/session context.
This enables tracing of usage events back to the originating request.
"""
import base64
import json
import uuid
import logging
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from core.log_filters import set_log_context, clear_log_context

logger = logging.getLogger(__name__)


class TelemetryMiddleware(MiddlewareMixin):
    """
    Generates request_id and attaches to request context.
    Makes available for logging, usage event recording, and tracing.
    """

    def process_request(self, request):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.request_id = request_id

        # Try to extract user info from Supabase token or session
        request.telemetry_user_id = None
        request.telemetry_session_id = None

        # Decode JWT payload (no signature verification — for logging only).
        # @supabase_required handles actual auth; we just want user_id in log lines.
        # Checks Authorization header first, then access_token cookie (both accepted by supabase_required).
        def _decode_jwt_user(token: str):
            try:
                payload_b64 = token.split(".")[1]
                padding = (4 - len(payload_b64) % 4) % 4
                payload = json.loads(base64.b64decode(payload_b64 + "=" * padding))
                # user_metadata carries the app-level user_id; sub is the Supabase UUID fallback
                meta = payload.get("user_metadata") or {}
                return meta.get("user_id") or payload.get("sub")
            except Exception:
                return None

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            request.telemetry_user_id = _decode_jwt_user(auth_header[7:].strip())

        # Cookie-based auth: supabase_required also accepts access_token cookie
        if not request.telemetry_user_id:
            cookie_token = request.COOKIES.get("access_token")
            if cookie_token:
                request.telemetry_user_id = _decode_jwt_user(cookie_token)

        # Extract session ID if available (browser-based auth)
        if hasattr(request, "session") and request.session:
            request.telemetry_session_id = request.session.get("session_id") or request.session.session_key

        # Extract client IP (handles proxies like nginx)
        client_ip = self._get_client_ip(request)
        request.telemetry_client_ip = client_ip

        # Extract user agent
        request.telemetry_user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Populate thread-local so RequestContextFilter injects these into all log lines
        set_log_context(request_id, request.telemetry_user_id or "anonymous")

        logger.debug(
            "[TelemetryMiddleware] request_id=%s user_id=%s path=%s method=%s",
            request_id,
            request.telemetry_user_id or "anonymous",
            request.path,
            request.method,
        )

        return None

    def process_response(self, request, response):
        clear_log_context()
        return response

    def _get_client_ip(self, request):
        """
        Extract client IP address, handling proxies.
        Checks X-Forwarded-For, X-Real-IP, and then REMOTE_ADDR.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
            return ip

        x_real_ip = request.META.get("HTTP_X_REAL_IP")
        if x_real_ip:
            return x_real_ip.strip()

        return request.META.get("REMOTE_ADDR", "")
