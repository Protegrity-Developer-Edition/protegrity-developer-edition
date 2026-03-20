"""
Tests for /api/me/ endpoint - current user information.

Verifies that authenticated users can retrieve their profile information
including role and permissions data.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from apps.core.utils import get_user_role

User = get_user_model()


@pytest.mark.django_db
def test_me_requires_authentication():
    """Test that /api/me/ returns 401 for unauthenticated requests."""
    client = APIClient()
    url = reverse('current_user')
    
    response = client.get(url)
    
    assert response.status_code == 401


@pytest.mark.django_db
def test_me_returns_protegrity_user_data():
    """Test that /api/me/ returns correct data for PROTEGRITY user."""
    # Create PROTEGRITY user via Django Groups
    user = User.objects.create_user(
        username='protegrity_user',
        password='testpass123',
        email='protegrity@example.com',
        first_name='John',
        last_name='Doe'
    )
    protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
    user.groups.add(protegrity_group)
    
    # Authenticate
    client = APIClient()
    client.force_authenticate(user=user)
    
    # Request /api/me/
    url = reverse('current_user')
    response = client.get(url)
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert data['username'] == 'protegrity_user'
    assert data['email'] == 'protegrity@example.com'
    assert data['first_name'] == 'John'
    assert data['last_name'] == 'Doe'
    assert data['role'] == 'PROTEGRITY'
    assert data['is_protegrity'] is True


@pytest.mark.django_db
def test_me_returns_standard_user_data():
    """Test that /api/me/ returns correct data for STANDARD user."""
    # Create STANDARD user (no group = STANDARD role)
    user = User.objects.create_user(
        username='standard_user',
        password='testpass123',
        email='standard@example.com'
    )
    # Verify role is STANDARD (no group membership)
    assert get_user_role(user) == 'STANDARD'
    
    # Authenticate
    client = APIClient()
    client.force_authenticate(user=user)
    
    # Request /api/me/
    url = reverse('current_user')
    response = client.get(url)
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert data['username'] == 'standard_user'
    assert data['email'] == 'standard@example.com'
    assert data['role'] == 'STANDARD'
    assert data['is_protegrity'] is False


@pytest.mark.django_db
def test_me_includes_all_expected_fields():
    """Test that /api/me/ includes all required fields."""
    user = User.objects.create_user(
        username='testuser',
        password='testpass123'
    )
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    url = reverse('current_user')
    response = client.get(url)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify all expected fields are present
    expected_fields = {'id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_protegrity'}
    assert set(data.keys()) == expected_fields
