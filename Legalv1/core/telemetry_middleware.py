"""
Telemetry middleware for request tracking.

Generates a unique request_id for every request and attaches user/session context.
This enables tracing of usage events back to the originating request.
"""
import uuid
import logging
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("django")


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

        # If authenticated via @supabase_required, supabase_user will be set
        if hasattr(request, "supabase_user") and request.supabase_user:
            try:
                request.telemetry_user_id = request.supabase_user.get("user_id") or request.supabase_user.get("sub")
            except (AttributeError, KeyError):
                pass

        # Extract session ID if available (browser-based auth)
        if hasattr(request, "session") and request.session:
            request.telemetry_session_id = request.session.get("session_id") or request.session.session_key

        # Extract client IP (handles proxies like nginx)
        client_ip = self._get_client_ip(request)
        request.telemetry_client_ip = client_ip

        # Extract user agent
        request.telemetry_user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Log request with telemetry data for debugging
        logger.debug(
            "[TelemetryMiddleware] request_id=%s user_id=%s path=%s method=%s",
            request_id,
            request.telemetry_user_id or "anonymous",
            request.path,
            request.method,
        )

        return None

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
