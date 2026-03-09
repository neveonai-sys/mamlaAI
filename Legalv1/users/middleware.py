from django.utils.deprecation import MiddlewareMixin
from users.routes.session_manager import SessionManager
import logging

logger = logging.getLogger(__name__)

class UpdateLastActivityMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if hasattr(request, 'user_id') and request.user_id:
            token = request.COOKIES.get('access_token')
            if token:
                logger.debug(f"updating session last update ---- UpdateLastActivityMiddleware ---")
                session_manager = SessionManager()
                session_manager.update_last_activity(token)
        return None
