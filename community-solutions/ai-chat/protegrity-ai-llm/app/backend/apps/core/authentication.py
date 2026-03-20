"""
Custom authentication backends for API access.

This module implements API key-based authentication for programmatic access
to the chat API. API keys inherit the user's role and permissions.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.utils import timezone
from .models import ApiKey


class ApiKeyAuthentication(BaseAuthentication):
    """
    Authenticate using an API key.
    
    Supports two header formats:
    1. Authorization: Api-Key <key>
    2. X-API-Key: <key>
    
    Security Design:
    - Keys are hashed in database (never stored plaintext)
    - Fast lookup via prefix index (first 8 chars)
    - Full key validation via password hasher (constant-time comparison)
    - Expired keys rejected
    - Inactive keys rejected
    - last_used_at tracked for audit
    
    Role Inheritance:
    - API key inherits user's role from UserProfile
    - Same permissions as if user logged in via JWT
    - No separate permission system for API keys
    
    Usage (client-side):
    
        # Option 1: Authorization header
        curl -H "Authorization: Api-Key YOUR_KEY_HERE" \\
             https://api.example.com/api/chat/
        
        # Option 2: Custom header
        curl -H "X-API-Key: YOUR_KEY_HERE" \\
             https://api.example.com/api/chat/
    
    Error Responses:
    - 401: Invalid, expired, or inactive key
    - Descriptive error message in response
    """
    
    keyword = "Api-Key"
    
    def authenticate(self, request):
        """
        Authenticate the request using API key.
        
        Args:
            request: DRF Request object
        
        Returns:
            Tuple of (user, None) if authenticated
            None if no API key present (let other authenticators try)
        
        Raises:
            AuthenticationFailed: If key is invalid, expired, or inactive
        """
        # Try Authorization header first
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        api_key = None
        
        if auth.startswith(self.keyword):
            # Extract key after "Api-Key "
            api_key = auth[len(self.keyword):].strip()
        
        # Fall back to X-API-Key header
        if not api_key:
            api_key = request.META.get("HTTP_X_API_KEY")
        
        # No API key present - let other authenticators run
        if not api_key:
            return None
        
        # Validate key length (should be at least 8 chars for prefix)
        if len(api_key) < 8:
            raise exceptions.AuthenticationFailed("Invalid API key format.")
        
        # Look up key by prefix (fast indexed lookup)
        prefix = api_key[:8]
        key_obj = ApiKey.objects.filter(
            prefix=prefix,
            is_active=True
        ).select_related('user').first()
        
        if not key_obj:
            raise exceptions.AuthenticationFailed("Invalid API key.")
        
        # Verify full key against hash (constant-time comparison)
        if not key_obj.check_key(api_key):
            raise exceptions.AuthenticationFailed("Invalid API key.")
        
        # Check expiration
        if key_obj.expires_at and key_obj.expires_at < timezone.now():
            raise exceptions.AuthenticationFailed("API key expired.")
        
        # Update last used timestamp (async in production)
        key_obj.last_used_at = timezone.now()
        key_obj.save(update_fields=["last_used_at"])
        
        # Return user (inherits their role and permissions)
        return (key_obj.user, None)
    
    def authenticate_header(self, request):
        """
        Return authentication challenge for 401 responses.
        
        Returns:
            String to use in WWW-Authenticate header
        """
        return self.keyword
