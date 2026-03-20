# backend/apps/core/tests/test_polling_api.py
"""
Tests for the polling API endpoint.

NOTE: This file previously contained provider-specific tests (Fin AI polling)
that tested low-level provider behavior with fake conversation IDs. Those tests
are now obsolete because:
1. The orchestrator.poll() method now handles all polling logic
2. Provider-specific polling behavior is tested in test_provider_abstraction.py
3. The poll endpoint requires real Conversation UUIDs from the database

This file now focuses on basic API validation (HTTP methods, conversation not found, etc.)
"""
import uuid
from unittest.mock import patch, Mock
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


class PollingAPITestCase(TestCase):
    """Tests for the polling API endpoint validation"""

    def setUp(self):
        # Create authenticated user
        self.user = User.objects.create_user(
            username='testuser@example.com',
            password='testpass123'
        )
        self.user.profile.role = 'PROTEGRITY'
        self.user.profile.save()
        
        # Use APIClient and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Generate a valid (but non-existent) conversation UUID for testing
        self.fake_uuid = str(uuid.uuid4())

    def test_poll_requires_get(self):
        """Poll endpoint should only accept GET requests"""
        response = self.client.post(f'/api/chat/poll/{self.fake_uuid}/')
        self.assertEqual(response.status_code, 405)
        data = response.json()
        self.assertIn('not allowed', data['detail'].lower())
    
    def test_poll_conversation_not_found(self):
        """Test polling with non-existent conversation returns 404"""
        response = self.client.get(f'/api/chat/poll/{self.fake_uuid}/')
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['error']['code'], 'conversation_not_found')
