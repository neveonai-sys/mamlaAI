import json
import logging
from django.http import JsonResponse
from rest_framework.decorators import api_view, throttle_classes, authentication_classes, permission_classes
from rest_framework.throttling import AnonRateThrottle
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.core.cache import cache
from datetime import datetime, timedelta
import uuid
from bson import ObjectId
from functools import wraps

# Import the correct class from routes
from .routes.creatupdateAIdrafts import CreateupdatefetchAIdrafts

logger = logging.getLogger(__name__)

# Rate limiting configuration
class TestDraftThrottle(AnonRateThrottle):
    rate = '5/hour'
    scope = 'test_draft'

class TestDraftUpdateThrottle(AnonRateThrottle):
    rate = '30/hour'
    scope = 'test_draft_update'

# Session expiration in minutes (2 hours)
TEST_SESSION_EXPIRY = 120

# Maximum number of edits allowed per test draft
MAX_EDITS_PER_DRAFT = 3

def get_test_session(session_id):
    """Helper to get test session data from cache"""
    return cache.get(f'test_session_{session_id}')

def update_test_session(session_id, session_data):
    """Helper to update test session data in cache"""
    cache.set(f'test_session_{session_id}', session_data, timeout=TEST_SESSION_EXPIRY * 60)

def bypass_auth(view_func):
    """Decorator to explicitly bypass authentication for test endpoints"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Ensure request has user attribute set to anonymous
        if not hasattr(request, 'user'):
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@api_view(['GET'])
@throttle_classes([TestDraftThrottle])
@authentication_classes([])
@permission_classes([AllowAny])
@bypass_auth
def test_hello(request):
    """Simple test endpoint to verify the API is working"""
    logger.info("Test hello endpoint accessed")
    return JsonResponse({'message': 'Test endpoint is working!'})

@api_view(['POST'])
@throttle_classes([TestDraftThrottle])
@authentication_classes([])
@permission_classes([AllowAny])
@bypass_auth
def create_test_draft(request):
    """
    Public endpoint for creating a test draft.
    No authentication required but strictly rate limited.
    """
    logger.info(f"[TEST] Create test draft request: {request.data}")
    try:
        data = request.data
        # Use a test user ID for test endpoints
        obj = CreateupdatefetchAIdrafts("test_user")
        
        # Validate required fields
        if not data.get('user_query'):
            logger.warning("Missing required field: user_query")
            return JsonResponse({'error': 'Description is required'}, status=400)
            
        # Create a test session
        session_id = obj.start_new_session(
            user_query=data.get('user_query'),
            draft_for=None,  # No draft_for for test users
            location={
                'state': data.get('state', ''),
                'district': '',
                'court': ''
            },
            language=data.get('language', 'English')
        )
        
        if not session_id:
            logger.error("Failed to create test session - start_new_session returned None")
            return JsonResponse({'error': 'Failed to create test session'}, status=500)
            
        logger.info(f"[TEST] Session created with ID: {session_id}")
        
        # Get draft sections directly from the database
        try:
            db = obj.get_mongo_client_db()
            session = db.find_one({'_id': ObjectId(session_id)})
            if not session:
                logger.error(f"[TEST] Session {session_id} not found in database")
                return JsonResponse({'error': 'Failed to create test session'}, status=500)
                
            draft_sections = session.get('draft_sections', [])
        except Exception as e:
            logger.error(f"[TEST] Error accessing database: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Failed to create test session'}, status=500)
        
        # Create a test session record in cache
        test_session = {
            'session_id': str(session_id),
            'created_at': datetime.utcnow().isoformat(),
            'sections': draft_sections,
            'edits_remaining': MAX_EDITS_PER_DRAFT,
            'ip_address': request.META.get('REMOTE_ADDR', 'unknown')
        }
        
        # Store in cache with expiration
        update_test_session(str(session_id), test_session)
        logger.info(f"[TEST] Test session created and cached: {str(session_id)}")
        
        return JsonResponse({
            'session_id': str(session_id),
            'draft_sections': draft_sections,
            'edits_remaining': MAX_EDITS_PER_DRAFT,
            'message': 'Test draft created successfully'
        })
        
    except Exception as e:
        logger.error(f"[TEST] Error in create_test_draft: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)

@api_view(['POST'])
@throttle_classes([TestDraftUpdateThrottle])
@authentication_classes([])
@permission_classes([AllowAny])
@bypass_auth
def update_test_section(request):
    """
    Update a section in a test draft.
    """
    logger.info(f"[TEST] Update test section request: {request.data}")
    try:
        data = request.data
        session_id = data.get('session_id')
        section_id = data.get('section_id')
        content = data.get('content')
        
        if not all([session_id, section_id, content is not None]):
            logger.warning("Missing required fields")
            return JsonResponse({'error': 'Missing required fields'}, status=400)
            
        # Get test session from cache
        test_session = get_test_session(session_id)
        if not test_session:
            logger.error(f"[TEST] Session {session_id} not found in cache")
            return JsonResponse({'error': 'Invalid or expired session'}, status=400)
            
        # Verify IP matches
        if test_session.get('ip_address') != request.META.get('REMOTE_ADDR'):
            logger.error(f"[TEST] IP mismatch for session {session_id}")
            return JsonResponse({'error': 'Unauthorized access to session'}, status=403)
            
        # Check edit limit
        if test_session['edits_remaining'] <= 0:
            logger.error(f"[TEST] Edit limit reached for session {session_id}")
            return JsonResponse({'error': 'Edit limit reached for this test draft'}, status=400)
        
        # Update the section in the test session
        obj = CreateupdatefetchAIdrafts("test_user")
        db = obj.get_mongo_client_db()
        
        # Update the section content
        result = db.update_one(
            {
                '_id': ObjectId(session_id),
                'draft_sections.section_id': section_id
            },
            {
                '$set': {
                    'draft_sections.$.content': content,
                    'last_updated_on': datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            logger.error(f"[TEST] Section {section_id} not found in session {session_id}")
            return JsonResponse({'error': 'Section not found'}, status=404)
            
        # Update session in cache
        test_session['edits_remaining'] -= 1
        update_test_session(session_id, test_session)
        
        # Get updated sections
        session = db.find_one({'_id': ObjectId(session_id)})
        draft_sections = session.get('draft_sections', [])
        
        return JsonResponse({
            'success': True,
            'edits_remaining': test_session['edits_remaining'],
            'section_id': section_id,
            'updated_content': content,
            'draft_sections': draft_sections
        })
        
    except Exception as e:
        logger.error(f"[TEST] Error in update_test_section: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)

@api_view(['GET'])
@throttle_classes([TestDraftUpdateThrottle])
@authentication_classes([])
@permission_classes([AllowAny])
@bypass_auth
def download_test_draft(request):
    """
    Download a test draft as a document.
    """
    logger.info(f"[TEST] Download test draft request: {request.GET}")
    try:
        session_id = request.GET.get('session_id')
        format_type = request.GET.get('format', 'docx')  # docx or pdf
        
        if not session_id:
            logger.warning("Missing required field: session_id")
            return JsonResponse({'error': 'Session ID is required'}, status=400)
            
        # Verify session exists in cache
        test_session = get_test_session(session_id)
        if not test_session:
            logger.error(f"[TEST] Session {session_id} not found in cache")
            return JsonResponse({'error': 'Invalid or expired session'}, status=400)
            
        # Verify IP matches
        if test_session.get('ip_address') != request.META.get('REMOTE_ADDR'):
            logger.error(f"[TEST] IP mismatch for session {session_id}")
            return JsonResponse({'error': 'Unauthorized access to session'}, status=403)
        
        # For test purposes, we'll just return a success response with a mock download URL
        # In a real implementation, you would generate the document here
        return JsonResponse({
            'download_url': f'/api/ai-draft/test/mock-download/{session_id}.{format_type}',
            'expires_in_minutes': 30,
            'format': format_type,
            'message': 'This is a test download. Sign up to access the full document generation feature.'
        })
        
    except Exception as e:
        logger.error(f"[TEST] Error in download_test_draft: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)

@api_view(['GET'])
@throttle_classes([TestDraftThrottle])
@authentication_classes([])
@permission_classes([AllowAny])
@bypass_auth
def test_draft_status(request, session_id):
    """
    Check the status of a test draft session.
    """
    logger.info(f"[TEST] Test draft status request for session: {session_id}")
    try:
        # Get test session from cache
        test_session = get_test_session(session_id)
        if not test_session:
            logger.error(f"[TEST] Session {session_id} not found in cache")
            return JsonResponse({'error': 'Invalid or expired session'}, status=404)
        
        # Calculate time remaining
        created_at = datetime.fromisoformat(test_session['created_at'])
        expires_at = created_at + timedelta(minutes=TEST_SESSION_EXPIRY)
        time_remaining = (expires_at - datetime.utcnow()).total_seconds() / 60
        
        # Get section count from the test session
        section_count = len(test_session.get('sections', []))
        
        return JsonResponse({
            'session_id': session_id,
            'edits_remaining': test_session['edits_remaining'],
            'time_remaining_minutes': max(0, int(time_remaining)),
            'section_count': section_count,
            'is_expired': time_remaining <= 0
        })
        
    except Exception as e:
        logger.error(f"[TEST] Error in test_draft_status: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)

@api_view(['GET'])
@throttle_classes([TestDraftThrottle])
@authentication_classes([])
@permission_classes([AllowAny])
@bypass_auth
def get_test_draft_sections(request, session_id):
    """
    Get the sections for a test draft.
    Accepts both UUID and MongoDB ObjectId formats for session_id.
    No authentication required but strictly rate limited.
    """
    logger.info(f"[TEST] Get test draft sections request for session: {session_id}")
    try:
        # Get test session from cache - try both the original ID and as string
        test_session = get_test_session(session_id)
        
        # If not found, try with ObjectId if it's a valid MongoDB ID
        if not test_session and len(session_id) == 24:
            try:
                # Try to convert to ObjectId to validate format
                from bson import ObjectId
                obj_id = ObjectId(session_id)
                # Try with the string representation
                test_session = get_test_session(str(obj_id))
            except:
                pass
        
        if not test_session:
            logger.error(f"[TEST] Session {session_id} not found in cache")
            return JsonResponse({'error': 'Invalid or expired session'}, status=404)
        
        # Check if session is expired
        created_at = datetime.fromisoformat(test_session['created_at'])
        expires_at = created_at + timedelta(minutes=TEST_SESSION_EXPIRY)
        if datetime.utcnow() > expires_at:
            logger.error(f"[TEST] Session {session_id} has expired")
            return JsonResponse({'error': 'Session has expired'}, status=410)
        
        # Return the sections data
        return JsonResponse({
            'session_id': session_id,
            'sections': test_session.get('sections', []),
            'edits_remaining': test_session.get('edits_remaining', 0),
            'created_at': test_session['created_at'],
            'expires_at': expires_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"[TEST] Error in get_test_draft_sections: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)
