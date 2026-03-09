import re
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger(__name__)

class BypassAuthForTestEndpoints:
    """
    Middleware to bypass authentication for test endpoints.
    This should be placed before AuthenticationMiddleware in MIDDLEWARE settings.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Compile regex patterns for test endpoints
        self.test_endpoints = [
            r'^/api/aidrafts/test/.*$',
            r'^/test-ai-drafting/.*$',
            r'^/draft-preview/.*$',
        ]
        self.patterns = [re.compile(pattern) for pattern in self.test_endpoints]
        
    def is_test_endpoint(self, path):
        """Check if the request path matches any test endpoint pattern"""
        return any(pattern.match(path) for pattern in self.patterns)

    def __call__(self, request):
        # Add debug logging
        logger.debug(f"[MIDDLEWARE] Processing request: {request.method} {request.path}")
        
        # Check if the request path matches any test endpoint pattern
        if self.is_test_endpoint(request.path):
            logger.debug(f"[MIDDLEWARE] Matched test endpoint: {request.path}")
            
            # Set attributes to bypass authentication
            request._dont_enforce_csrf_checks = True
            
            # Explicitly set user to anonymous
            if not hasattr(request, 'user') or request.user.is_anonymous:
                logger.debug("[MIDDLEWARE] Setting anonymous user for test endpoint")
                request.user = AnonymousUser()
            
            # Add a flag to indicate this is a test request
            # This can be checked by other middleware or decorators
            request.is_test_endpoint = True
            
            # Set a flag that supabase_required can check
            request.bypass_supabase_auth = True
            
            logger.debug(f"[MIDDLEWARE] Request flags set - is_test_endpoint: True, bypass_supabase_auth: True")
        
        response = self.get_response(request)
        logger.debug(f"[MIDDLEWARE] Response status: {response.status_code}")
        return response
