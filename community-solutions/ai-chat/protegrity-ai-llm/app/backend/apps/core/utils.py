"""
Utility functions for core app.

This module provides helper functions for role-based access control,
user management, error responses, and other common operations.
"""

from django.http import JsonResponse


def error_response(message: str, *, code: str = "error", http_status: int = 400) -> JsonResponse:
    """
    Standardized error response format for consistent API error handling.
    
    Returns a consistent JSON structure:
        {
            "error": {
                "code": "machine_friendly_code",
                "message": "Human readable message"
            }
        }
    
    Args:
        message: Human-readable error message
        code: Machine-friendly error code (e.g., "forbidden_model", "message_required")
        http_status: HTTP status code (default: 400 Bad Request)
    
    Returns:
        JsonResponse with standardized error structure
    
    Examples:
        return error_response("Message is required", code="message_required", http_status=400)
        return error_response("Access denied", code="forbidden_model", http_status=403)
        return error_response("Not found", code="conversation_not_found", http_status=404)
    """
    return JsonResponse(
        {"error": {"code": code, "message": message}},
        status=http_status
    )


def get_user_role(user) -> str:
    """
    Get the role of a user based on Django Groups.
    
    Checks user's group membership to determine access level:
    - "Protegrity Users" group → PROTEGRITY role (full access)
    - No groups or other groups → STANDARD role (limited access)
    - Unauthenticated → ANONYMOUS role (no access)
    
    This uses Django's built-in Groups system for better scalability
    and flexibility. New roles can be added by creating groups without
    code changes.
    
    Args:
        user: Django User instance (may be unauthenticated/AnonymousUser)
    
    Returns:
        str: User's role - one of:
            - "PROTEGRITY": Full access to all active resources
            - "STANDARD": Limited access to resources marked for STANDARD
            - "ANONYMOUS": No access (unauthenticated users)
    
    Usage:
        role = get_user_role(request.user)
        if role == "PROTEGRITY":
            # Grant full access
            pass
    """
    # Handle unauthenticated users
    if not getattr(user, "is_authenticated", False):
        return "ANONYMOUS"
    
    # Prefer explicit UserProfile role when available
    profile = getattr(user, "profile", None)
    if profile and getattr(profile, "role", None) in {"PROTEGRITY", "STANDARD"}:
        return profile.role

    # Fallback: Check if user is in "Protegrity Users" group
    if user.groups.filter(name="Protegrity Users").exists():
        return "PROTEGRITY"
    
    # Default to STANDARD for all authenticated users
    return "STANDARD"


def get_default_llm_for_user(user):
    """
    Return a safe default LLM for the given user, or None if none is available.
    
    This function applies role-based filtering to ensure users only get models
    they're allowed to access, then selects the first active model by display_order.
    
    Rules:
    - STANDARD users: Only models with min_role="STANDARD"
    - PROTEGRITY users: Any active model, ordered by display_order
    - Returns None if no models are available for the user's role
    
    Args:
        user: Django User instance
    
    Returns:
        LLMProvider instance or None
    
    Usage:
        llm = get_default_llm_for_user(request.user)
        if not llm:
            return error_response("No LLM providers available", ...)
    """
    from .models import LLMProvider
    from .permissions import filter_by_role
    from .llm_config import filter_enabled_llm_provider_queryset
    
    # Apply role-based filtering first
    qs = filter_by_role(LLMProvider.objects.all(), user)
    qs = filter_enabled_llm_provider_queryset(qs)
    
    # Then order by display_order and name
    qs = qs.order_by("display_order", "name")
    
    # Return first allowed model
    return qs.first()
