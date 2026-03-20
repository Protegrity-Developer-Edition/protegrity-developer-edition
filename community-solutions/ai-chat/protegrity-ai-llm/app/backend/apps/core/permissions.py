"""
Role-based permissions and filtering for resources.

This module implements simple role-based access control (RBAC) for LLMProvider,
Agent, and Tool models. Access is controlled by:
- User's role (from UserProfile)
- Resource's min_role field
- Resource's is_active status

Design principles:
- Least privilege by default (resources default to PROTEGRITY-only)
- Explicit > implicit (clear rules, no hidden access)
- Fail closed (unknown roles get no access)
"""

from .utils import get_user_role


def filter_by_role(queryset, user):
    """
    Filter a queryset of LLMProvider / Agent / Tool based on user's role.
    
    Access Rules:
    - PROTEGRITY role: Full access to all active resources
    - STANDARD role: Only active resources where min_role == "STANDARD"
    - ANONYMOUS/unknown: No access (empty queryset)
    
    Args:
        queryset: Django QuerySet of LLMProvider, Agent, or Tool
        user: Django User instance (may be AnonymousUser)
    
    Returns:
        Filtered QuerySet based on user's role
    
    Usage:
        # In a view:
        models_qs = LLMProvider.objects.all()
        allowed_models = filter_by_role(models_qs, request.user)
        
        # Protegrity user sees all active models
        # Standard user sees only models with min_role="STANDARD"
        # Anonymous user sees nothing
    
    Implementation Notes:
    - Checks if model has is_active field (all our resources do)
    - Always filters to active resources first
    - Then applies role-based min_role filter
    - Returns empty queryset for invalid roles (fail closed)
    """
    role = get_user_role(user)
    
    # PROTEGRITY: Full access to active resources
    if role == "PROTEGRITY":
        if hasattr(queryset.model, "is_active"):
            return queryset.filter(is_active=True)
        return queryset
    
    # STANDARD: Only active resources with min_role == "STANDARD"
    if role == "STANDARD":
        qs = queryset
        
        # Filter to active resources
        if hasattr(queryset.model, "is_active"):
            qs = qs.filter(is_active=True)
        
        # Filter by min_role
        return qs.filter(min_role="STANDARD")
    
    # ANONYMOUS or unknown role: No access
    return queryset.none()


def check_resource_access(user, resource) -> bool:
    """
    Check if a user can access a specific resource instance.
    
    Args:
        user: Django User instance
        resource: LLMProvider, Agent, or Tool instance
    
    Returns:
        bool: True if user can access resource, False otherwise
    
    Usage:
        llm = LLMProvider.objects.get(id="azure-gpt-4o")
        if check_resource_access(request.user, llm):
            # User can use this model
            pass
    """
    role = get_user_role(user)
    
    # Check if resource is active
    if hasattr(resource, "is_active") and not resource.is_active:
        return False
    
    # PROTEGRITY can access any active resource
    if role == "PROTEGRITY":
        return True
    
    # STANDARD can only access resources with min_role == "STANDARD"
    if role == "STANDARD":
        return getattr(resource, "min_role", "PROTEGRITY") == "STANDARD"
    
    # ANONYMOUS or unknown: No access
    return False
