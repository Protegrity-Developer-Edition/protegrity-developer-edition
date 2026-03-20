"""
Tests for standardized API error responses.

Ensures all endpoints return consistent error format:
    {"error": {"code": "...", "message": "..."}}
"""

import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.core.models import LLMProvider, Agent
from apps.core.utils import error_response

User = get_user_model()


class ErrorResponseFormatTestCase(TestCase):
    """Test that error_response helper returns correct format"""
    
    def test_error_response_structure(self):
        """Test error_response returns expected JSON structure"""
        response = error_response(
            "Test error message",
            code="test_error",
            http_status=400
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        
        # Verify structure
        self.assertIn("error", data)
        self.assertIn("code", data["error"])
        self.assertIn("message", data["error"])
        
        # Verify values
        self.assertEqual(data["error"]["code"], "test_error")
        self.assertEqual(data["error"]["message"], "Test error message")
    
    def test_error_response_defaults(self):
        """Test error_response default values"""
        response = error_response("Default error")
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data["error"]["code"], "error")
        self.assertEqual(data["error"]["message"], "Default error")


class APIErrorResponsesTestCase(TestCase):
    """Test that API endpoints return standardized error formats"""
    
    def setUp(self):
        # Create authenticated user
        self.user = User.objects.create_user(
            username='testuser@example.com',
            password='testpass123'
        )
        self.user.profile.role = 'PROTEGRITY'
        self.user.profile.save()
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        self.llm = LLMProvider.objects.create(
            id='test-llm',
            name='Test LLM',
            provider_type='dummy',
            min_role='PROTEGRITY'
        )
        self.agent = Agent.objects.create(
            id='test-agent',
            name='Test Agent',
            system_prompt='Test prompt',
            default_llm=self.llm,
            min_role='PROTEGRITY'
        )
    
    def test_chat_missing_message_error_format(self):
        """Test /api/chat/ returns standard error for missing message"""
        response = self.client.post('/api/chat/', {'message': ''}, format='json')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        # Verify standard error structure
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "message_required")
        self.assertIsInstance(data["error"]["message"], str)
    
    def test_chat_invalid_model_error_format(self):
        """Test /api/chat/ returns standard error for invalid model"""
        response = self.client.post(
            '/api/chat/',
            {'message': 'Hello', 'model_id': 'nonexistent'},
            format='json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        # Verify standard error structure
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "invalid_model")
        self.assertIsInstance(data["error"]["message"], str)
    
    def test_chat_forbidden_model_error_format(self):
        """Test /api/chat/ returns standard error for forbidden model"""
        # Create PROTEGRITY-only model
        protected_llm = LLMProvider.objects.create(
            id='protected-llm',
            name='Protected LLM',
            provider_type='dummy',
            min_role='PROTEGRITY'
        )
        
        # Switch to STANDARD user
        self.user.profile.role = 'STANDARD'
        self.user.profile.save()
        
        response = self.client.post(
            '/api/chat/',
            {'message': 'Hello', 'model_id': 'protected-llm'},
            format='json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        
        # Verify standard error structure
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "forbidden_model")
        self.assertIsInstance(data["error"]["message"], str)
    
    def test_conversation_not_found_error_format(self):
        """Test /api/conversations/{id}/ returns standard error for 404"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = self.client.get(f'/api/conversations/{fake_id}/')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        
        # Verify standard error structure
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "conversation_not_found")
        self.assertIsInstance(data["error"]["message"], str)
    
    def test_poll_conversation_not_found_error_format(self):
        """Test /api/chat/poll/{id}/ returns standard error for 404"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = self.client.get(f'/api/chat/poll/{fake_id}/')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        
        # Verify standard error structure
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "conversation_not_found")
        self.assertIsInstance(data["error"]["message"], str)
