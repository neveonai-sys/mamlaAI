from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser
from unittest.mock import patch, MagicMock
from bson import ObjectId
import json
import datetime

# Import the views we want to test
from .views import initiate_drafting_session, save_draft, get_draft_for_draftsession_id
from .routes.creatupdateAIdrafts import CreateupdatefetchAIdrafts

class AIDraftClientValidationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client_user = {
            'user_id': 'client123',
            'user_type': 'Client',
            'email': 'client@example.com'
        }
        self.lawyer_user = {
            'user_id': 'lawyer123',
            'user_type': 'Lawyer',
            'email': 'lawyer@example.com'
        }
        self.paralegal_user = {
            'user_id': 'paralegal123',
            'user_type': 'Paralegal',
            'email': 'paralegal@example.com'
        }
        
        # Mock MongoDB collection
        self.mock_collection = MagicMock()
        self.mock_db = {'aidrafts_complete_data': self.mock_collection}
        
        # Patch the get_mongo_client_db method to return our mock collection
        self.get_mongo_patcher = patch.object(
            CreateupdatefetchAIdrafts, 
            'get_mongo_client_db', 
            return_value=self.mock_collection
        )
        self.mock_get_mongo = self.get_mongo_patcher.start()
        
    def tearDown(self):
        self.get_mongo_patcher.stop()
    
    def test_client_user_cannot_set_draft_for(self):
        """Test that client users cannot set draft_for to another client"""
        # Mock request data with draft_for set (should be ignored for client users)
        data = {
            'user_query': 'Test draft',
            'draft_for': {'client_id': 'another_client'},
            'language': 'English'
        }
        
        # Create a request with client user
        request = self.factory.post(
            '/api/aidrafts/start_session', 
            data=json.dumps(data), 
            content_type='application/json'
        )
        request.supabase_user = self.client_user
        
        # Mock the MongoDB insert response
        mock_session_id = ObjectId()
        self.mock_collection.insert_one.return_value.inserted_id = mock_session_id
        
        # Call the view
        response = initiate_drafting_session(request)
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('session_id', response_data)
        
        # Check that draft_for was set to empty dict for client user
        call_args = self.mock_collection.insert_one.call_args[0][0]
        self.assertEqual(call_args.get('draft_for'), {})
    
    def test_lawyer_can_set_draft_for(self):
        """Test that lawyer users can set draft_for"""
        # Mock request data with draft_for set
        draft_for = {'client_id': 'client456', 'client_name': 'Test Client'}
        data = {
            'user_query': 'Test draft',
            'draft_for': draft_for,
            'language': 'English'
        }
        
        # Create a request with lawyer user
        request = self.factory.post(
            '/api/aidrafts/start_session', 
            data=json.dumps(data), 
            content_type='application/json'
        )
        request.supabase_user = self.lawyer_user
        
        # Mock the MongoDB insert response
        mock_session_id = ObjectId()
        self.mock_collection.insert_one.return_value.inserted_id = mock_session_id
        
        # Call the view
        response = initiate_drafting_session(request)
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('session_id', response_data)
        
        # Check that draft_for was preserved for lawyer user
        call_args = self.mock_collection.insert_one.call_args[0][0]
        self.assertEqual(call_args.get('draft_for'), draft_for)
    
    def test_client_cannot_save_draft_with_draft_for(self):
        """Test that client users cannot save a draft with draft_for set"""
        # First, create a session with a client user
        session_id = str(ObjectId())
        
        # Mock the session in the database with draft_for set (shouldn't happen, but testing protection)
        self.mock_collection.find_one.return_value = {
            '_id': ObjectId(session_id),
            'user_id': self.client_user['user_id'],
            'draft_for': {'client_id': 'another_client'},  # This should be caught
            'saved_drafts': []
        }
        
        # Create a save draft request
        data = {
            'session_id': session_id,
            'draft_name': 'Test Draft',
            'draft_sections': [{'section': 'test'}]
        }
        
        request = self.factory.post(
            '/api/aidrafts/save_draft',
            data=json.dumps(data),
            content_type='application/json'
        )
        request.supabase_user = self.client_user
        
        # Call the view
        response = save_draft(request)
        
        # Should return 403 Forbidden
        self.assertEqual(response.status_code, 403)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertIn('Unauthorized', response_data['error'])
    
    def test_paralegal_can_save_draft_with_draft_for(self):
        """Test that paralegal users can save drafts with draft_for set"""
        session_id = str(ObjectId())
        draft_for = {'client_id': 'client789', 'client_name': 'Test Client'}
        
        # Mock the session in the database
        self.mock_collection.find_one.return_value = {
            '_id': ObjectId(session_id),
            'user_id': self.paralegal_user['user_id'],
            'draft_for': draft_for,
            'saved_drafts': []
        }
        
        # Mock the update operation
        self.mock_collection.update_one.return_value.matched_count = 1
        
        # Create a save draft request
        data = {
            'session_id': session_id,
            'draft_name': 'Test Draft',
            'draft_sections': [{'section': 'test'}]
        }
        
        request = self.factory.post(
            '/api/aidrafts/save_draft',
            data=json.dumps(data),
            content_type='application/json'
        )
        request.supabase_user = self.paralegal_user
        
        # Call the view
        response = save_draft(request)
        
        # Should be successful
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('message', response_data)
        self.assertEqual(response_data['message'], 'Successfully Saved')
    
    def test_get_draft_for_client_user(self):
        """Test that get_draft_for_draftsession_id works for client users"""
        session_id = str(ObjectId())
        
        # Mock the session in the database
        self.mock_collection.find_one.return_value = {
            '_id': ObjectId(session_id),
            'user_id': self.client_user['user_id'],
            'draft_for': {}  # Should be empty for client users
        }
        
        # Create a GET request
        request = self.factory.get(f'/api/aidrafts/get_draft_for?session_id={session_id}')
        request.supabase_user = self.client_user
        
        # Call the view
        response = get_draft_for_draftsession_id(request)
        
        # Should be successful
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('draft_for', response_data)
        self.assertEqual(response_data['draft_for'], {})
