"""
Base test class with authenticated user setup.

All test classes that need authenticated API access should inherit from AuthenticatedTestCase.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

User = get_user_model()


class AuthenticatedTestCase(TestCase):
    """
    Base test case that creates an authenticated PROTEGRITY user.
    
    Provides:
    - self.user: Authenticated user with PROTEGRITY role (via Django Groups)
    - self.client: APIClient with force_authenticate applied
    
    Usage:
        class MyTestCase(AuthenticatedTestCase):
            def test_something(self):
                response = self.client.get('/api/models/')
                # User is automatically authenticated as PROTEGRITY
    """
    
    def setUp(self):
        """Create authenticated user and client."""
        super().setUp()
        
        # Create a PROTEGRITY user via Django Groups
        self.user = User.objects.create_user(
            username='testuser@example.com',
            password='testpass123'
        )
        # Add to Protegrity Users group
        protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
        self.user.groups.add(protegrity_group)
        
        # Use APIClient with authentication
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
