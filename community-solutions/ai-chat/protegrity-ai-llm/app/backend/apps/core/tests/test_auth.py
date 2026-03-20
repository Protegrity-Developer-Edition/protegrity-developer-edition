"""
Tests for JWT authentication endpoints.

Verifies that users can obtain and refresh JWT tokens.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_login_with_valid_credentials():
    """Test that valid credentials return access and refresh tokens."""
    # Create user
    user = User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com'
    )
    
    # Login
    client = APIClient()
    url = reverse('token_obtain_pair')
    response = client.post(url, {
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert 'access' in data
    assert 'refresh' in data
    assert isinstance(data['access'], str)
    assert isinstance(data['refresh'], str)
    assert len(data['access']) > 50  # JWT tokens are long


@pytest.mark.django_db
def test_login_with_invalid_credentials():
    """Test that invalid credentials return 401."""
    # Create user
    user = User.objects.create_user(
        username='testuser',
        password='testpass123'
    )
    
    # Attempt login with wrong password
    client = APIClient()
    url = reverse('token_obtain_pair')
    response = client.post(url, {
        'username': 'testuser',
        'password': 'wrongpassword'
    })
    
    # Verify response
    assert response.status_code == 401


@pytest.mark.django_db
def test_login_with_nonexistent_user():
    """Test that login with nonexistent user returns 401."""
    client = APIClient()
    url = reverse('token_obtain_pair')
    response = client.post(url, {
        'username': 'nonexistent',
        'password': 'testpass123'
    })
    
    # Verify response
    assert response.status_code == 401


@pytest.mark.django_db
def test_token_refresh():
    """Test that refresh token can be used to get new access token."""
    # Create user and get tokens
    user = User.objects.create_user(
        username='testuser',
        password='testpass123'
    )
    
    client = APIClient()
    
    # Get initial tokens
    token_url = reverse('token_obtain_pair')
    response = client.post(token_url, {
        'username': 'testuser',
        'password': 'testpass123'
    })
    tokens = response.json()
    refresh_token = tokens['refresh']
    
    # Use refresh token to get new access token
    refresh_url = reverse('token_refresh')
    response = client.post(refresh_url, {
        'refresh': refresh_token
    })
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert 'access' in data
    assert isinstance(data['access'], str)
    assert len(data['access']) > 50


@pytest.mark.django_db
def test_authenticated_endpoint_with_valid_token():
    """Test that /api/me/ works with valid JWT token."""
    # Create user and get token
    user = User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com'
    )
    user.profile.role = 'STANDARD'
    user.profile.save()
    
    client = APIClient()
    
    # Get token
    token_url = reverse('token_obtain_pair')
    response = client.post(token_url, {
        'username': 'testuser',
        'password': 'testpass123'
    })
    access_token = response.json()['access']
    
    # Access protected endpoint
    me_url = reverse('current_user')
    response = client.get(
        me_url,
        HTTP_AUTHORIZATION=f'Bearer {access_token}'
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert data['username'] == 'testuser'
    assert data['email'] == 'test@example.com'
    assert data['role'] == 'STANDARD'


@pytest.mark.django_db
def test_authenticated_endpoint_without_token():
    """Test that /api/me/ returns 401 without token."""
    client = APIClient()
    url = reverse('current_user')
    response = client.get(url)
    
    assert response.status_code == 401
