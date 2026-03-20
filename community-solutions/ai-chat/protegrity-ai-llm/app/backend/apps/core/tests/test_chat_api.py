# backend/apps/core/tests/test_chat_api.py
"""
Tests for the chat API endpoints.

NOTE: This file previously contained provider-specific tests (Fin AI, Bedrock)
that tested low-level provider behavior. Those tests are now obsolete because:
1. The orchestrator now has fallback logic to DummyProvider on errors
2. Protegrity processing wraps all requests
3. Provider-specific behavior is tested in test_provider_abstraction.py
4. Integration testing is covered in test_protegrity_integration.py

This file now focuses on basic API validation (HTTP methods, required fields, etc.)
"""
import json
from unittest.mock import patch, Mock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


class ChatAPITestCase(TestCase):
    """Tests for the chat API endpoint validation"""

    def setUp(self):
        # Create a PROTEGRITY user for testing
        self.user = User.objects.create_user(
            username='testuser@example.com',
            password='testpass123'
        )
        self.user.profile.role = 'PROTEGRITY'
        self.user.profile.save()
        
        # Use APIClient and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_chat_requires_post(self):
        """Chat endpoint should only accept POST requests"""
        response = self.client.get('/api/chat/')
        self.assertEqual(response.status_code, 405)
        data = response.json()
        self.assertIn('not allowed', data['detail'].lower())

    def test_chat_requires_message(self):
        """Chat endpoint should reject empty messages"""
        response = self.client.post(
            '/api/chat/',
            {'message': ''},  # APIClient handles JSON encoding
            format='json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error']['code'], 'message_required')

    def test_chat_requires_valid_json(self):
        """Chat endpoint should reject invalid JSON"""
        response = self.client.post(
            '/api/chat/',
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        # DRF handles JSON parsing and returns appropriate error
