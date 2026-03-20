"""
Tests for authentication and role-based permissions system.

Test Coverage:
- UserProfile creation and role assignment
- Role-based queryset filtering (filter_by_role)
- List endpoint filtering (/api/models/, /api/agents/, /api/tools/)
- Chat endpoint permission enforcement (/api/chat/)
- API key authentication and authorization
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from apps.core.models import (
    UserProfile, LLMProvider, Agent, Tool, ApiKey, Conversation, ROLE_CHOICES
)
from apps.core.utils import get_user_role
from apps.core.permissions import filter_by_role, check_resource_access


User = get_user_model()


@pytest.fixture
def protegrity_user(db):
    """Create a user with PROTEGRITY role via Django Groups."""
    user = User.objects.create_user(
        username="protegrity@example.com",
        email="protegrity@example.com",
        password="testpass123"
    )
    # Add to Protegrity Users group
    protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
    user.groups.add(protegrity_group)
    return user


@pytest.fixture
def standard_user(db):
    """Create a user with STANDARD role via Django Groups."""
    user = User.objects.create_user(
        username="standard@example.com",
        email="standard@example.com",
        password="testpass123"
    )
    # User is STANDARD by default (not in any special group)
    assert get_user_role(user) == "STANDARD"
    return user


@pytest.fixture
def fin_model(db):
    """Create Fin AI model with STANDARD min_role."""
    return LLMProvider.objects.create(
        id="fin",
        name="Fin AI",
        provider_type="intercom",
        description="Intercom Fin AI",
        is_active=True,
        min_role="STANDARD"
    )


@pytest.fixture
def claude_model(db):
    """Create Claude model with PROTEGRITY min_role."""
    return LLMProvider.objects.create(
        id="claude",
        name="Claude 3.5 Sonnet",
        provider_type="anthropic",
        description="Anthropic Claude",
        is_active=True,
        min_role="PROTEGRITY"
    )


@pytest.fixture
def test_agent(db, fin_model):
    """Create a test agent with PROTEGRITY min_role."""
    return Agent.objects.create(
        id="test-agent",
        name="Test Agent",
        description="Test agent for testing",
        system_prompt="You are a test agent",
        default_llm=fin_model,
        is_active=True,
        min_role="PROTEGRITY"
    )


@pytest.fixture
def test_tool(db):
    """Create a test tool with PROTEGRITY min_role."""
    return Tool.objects.create(
        id="test-tool",
        name="Test Tool",
        tool_type="custom",
        description="Test tool for testing",
        function_schema={},
        is_active=True,
        min_role="PROTEGRITY"
    )


@pytest.mark.django_db
class TestUserProfileCreation:
    """Test automatic UserProfile creation and Django Groups role assignment."""
    
    def test_profile_auto_created_on_user_creation(self):
        """UserProfile should be auto-created via post_save signal."""
        user = User.objects.create_user(
            username="newuser@example.com",
            password="testpass123"
        )
        
        assert hasattr(user, 'profile')
        assert isinstance(user.profile, UserProfile)
        # User is STANDARD by default (not in any special group)
        assert get_user_role(user) == "STANDARD"
    
    def test_get_user_role_for_authenticated_user(self, protegrity_user):
        """get_user_role should return PROTEGRITY for users in Protegrity Users group."""
        role = get_user_role(protegrity_user)
        assert role == "PROTEGRITY"
    
    def test_get_user_role_for_standard_user(self, standard_user):
        """Standard users should have STANDARD role."""
        role = get_user_role(standard_user)
        assert role == "STANDARD"
    
    def test_get_user_role_for_anonymous_user(self):
        """Anonymous users should get ANONYMOUS role."""
        from django.contrib.auth.models import AnonymousUser
        anon = AnonymousUser()
        role = get_user_role(anon)
        assert role == "ANONYMOUS"


@pytest.mark.django_db
class TestRoleFilteringLogic:
    """Test filter_by_role helper function."""
    
    def test_protegrity_sees_all_active_models(self, protegrity_user, fin_model, claude_model):
        """PROTEGRITY users should see all active models."""
        qs = LLMProvider.objects.all()
        filtered = filter_by_role(qs, protegrity_user)
        
        assert filtered.count() == 2
        assert fin_model in filtered
        assert claude_model in filtered
    
    def test_standard_sees_only_standard_models(self, standard_user, fin_model, claude_model):
        """STANDARD users should only see models with min_role=STANDARD."""
        qs = LLMProvider.objects.all()
        filtered = filter_by_role(qs, standard_user)
        
        assert filtered.count() == 1
        assert fin_model in filtered
        assert claude_model not in filtered
    
    def test_anonymous_sees_nothing(self, fin_model, claude_model):
        """Anonymous users should see no models."""
        from django.contrib.auth.models import AnonymousUser
        anon = AnonymousUser()
        
        qs = LLMProvider.objects.all()
        filtered = filter_by_role(qs, anon)
        
        assert filtered.count() == 0
    
    def test_inactive_models_filtered_out(self, protegrity_user, fin_model):
        """Inactive models should not appear even for PROTEGRITY users."""
        fin_model.is_active = False
        fin_model.save()
        
        qs = LLMProvider.objects.all()
        filtered = filter_by_role(qs, protegrity_user)
        
        assert filtered.count() == 0
    
    def test_filter_agents_protegrity_sees_all(self, protegrity_user, test_agent):
        """PROTEGRITY users should see agents."""
        qs = Agent.objects.all()
        filtered = filter_by_role(qs, protegrity_user)
        
        assert filtered.count() == 1
        assert test_agent in filtered
    
    def test_filter_agents_standard_sees_none(self, standard_user, test_agent):
        """STANDARD users should see no agents (all are PROTEGRITY-only)."""
        qs = Agent.objects.all()
        filtered = filter_by_role(qs, standard_user)
        
        assert filtered.count() == 0
    
    def test_check_resource_access_protegrity_allowed(self, protegrity_user, claude_model):
        """PROTEGRITY users should have access to PROTEGRITY resources."""
        assert check_resource_access(protegrity_user, claude_model) is True
    
    def test_check_resource_access_standard_allowed_for_standard_resource(self, standard_user, fin_model):
        """STANDARD users should have access to STANDARD resources."""
        assert check_resource_access(standard_user, fin_model) is True
    
    def test_check_resource_access_standard_denied_for_protegrity_resource(self, standard_user, claude_model):
        """STANDARD users should not have access to PROTEGRITY resources."""
        assert check_resource_access(standard_user, claude_model) is False


@pytest.mark.django_db
class TestListEndpointFiltering:
    """Test /api/models/, /api/agents/, /api/tools/ endpoints."""
    
    def test_models_endpoint_protegrity_user(self, protegrity_user, fin_model, claude_model):
        """PROTEGRITY users should see all models in /api/models/."""
        client = APIClient()
        client.force_authenticate(user=protegrity_user)
        
        response = client.get('/api/models/')
        assert response.status_code == 200
        
        data = response.json()
        assert len(data['models']) == 2
        model_ids = [m['id'] for m in data['models']]
        assert 'fin' in model_ids
        assert 'claude' in model_ids
    
    def test_models_endpoint_standard_user(self, standard_user, fin_model, claude_model):
        """STANDARD users should only see STANDARD models in /api/models/."""
        client = APIClient()
        client.force_authenticate(user=standard_user)
        
        response = client.get('/api/models/')
        assert response.status_code == 200
        
        data = response.json()
        assert len(data['models']) == 1
        assert data['models'][0]['id'] == 'fin'
    
    def test_agents_endpoint_protegrity_user(self, protegrity_user, test_agent):
        """PROTEGRITY users should see agents in /api/agents/."""
        client = APIClient()
        client.force_authenticate(user=protegrity_user)
        
        response = client.get('/api/agents/')
        assert response.status_code == 200
        
        data = response.json()
        assert len(data['agents']) == 1
        assert data['agents'][0]['id'] == 'test-agent'
    
    def test_agents_endpoint_standard_user(self, standard_user, test_agent):
        """STANDARD users should see empty list in /api/agents/."""
        client = APIClient()
        client.force_authenticate(user=standard_user)
        
        response = client.get('/api/agents/')
        assert response.status_code == 200
        
        data = response.json()
        assert len(data['agents']) == 0
    
    def test_tools_endpoint_protegrity_user(self, protegrity_user, test_tool):
        """PROTEGRITY users should see tools in /api/tools/."""
        client = APIClient()
        client.force_authenticate(user=protegrity_user)
        
        response = client.get('/api/tools/')
        assert response.status_code == 200
        
        data = response.json()
        assert len(data['tools']) == 1
        assert data['tools'][0]['id'] == 'test-tool'
    
    def test_tools_endpoint_standard_user(self, standard_user, test_tool):
        """STANDARD users should see empty list in /api/tools/."""
        client = APIClient()
        client.force_authenticate(user=standard_user)
        
        response = client.get('/api/tools/')
        assert response.status_code == 200
        
        data = response.json()
        assert len(data['tools']) == 0


@pytest.mark.django_db
class TestChatEndpointPermissions:
    """Test /api/chat/ endpoint permission enforcement."""
    
    def test_chat_protegrity_user_with_protegrity_model(self, protegrity_user, claude_model):
        """PROTEGRITY users can use PROTEGRITY models."""
        client = APIClient()
        client.force_authenticate(user=protegrity_user)
        
        response = client.post('/api/chat/', {
            'message': 'Hello',
            'model_id': 'claude'
        }, format='json')
        
        # Should not return 403
        assert response.status_code != 403
    
    def test_chat_standard_user_with_standard_model(self, standard_user, fin_model):
        """STANDARD users can use STANDARD models."""
        client = APIClient()
        client.force_authenticate(user=standard_user)
        
        response = client.post('/api/chat/', {
            'message': 'Hello',
            'model_id': 'fin'
        }, format='json')
        
        # Should not return 403
        assert response.status_code != 403
    
    def test_chat_standard_user_with_protegrity_model_forbidden(self, standard_user, claude_model):
        """STANDARD users cannot use PROTEGRITY models."""
        client = APIClient()
        client.force_authenticate(user=standard_user)
        
        response = client.post('/api/chat/', {
            'message': 'Hello',
            'model_id': 'claude'
        }, format='json')
        
        assert response.status_code == 403
        data = response.json()
        assert data['error']['code'] == 'forbidden_model'
        assert 'not allowed' in data['error']['message'].lower()
    
    def test_chat_standard_user_with_agent_forbidden(self, standard_user, test_agent, fin_model):
        """STANDARD users cannot use agents (all are PROTEGRITY-only)."""
        client = APIClient()
        client.force_authenticate(user=standard_user)
        
        response = client.post('/api/chat/', {
            'message': 'Hello',
            'model_id': 'fin',
            'agent_id': 'test-agent'
        }, format='json')
        
        assert response.status_code == 403
        data = response.json()
        assert data['error']['code'] == 'forbidden_agent'
        assert 'not allowed' in data['error']['message'].lower()
    
    def test_chat_protegrity_user_with_agent_allowed(self, protegrity_user, test_agent, fin_model):
        """PROTEGRITY users can use agents."""
        client = APIClient()
        client.force_authenticate(user=protegrity_user)
        
        response = client.post('/api/chat/', {
            'message': 'Hello',
            'model_id': 'fin',
            'agent_id': 'test-agent'
        }, format='json')
        
        # Should not return 403
        assert response.status_code != 403


@pytest.mark.django_db
class TestApiKeyAuthentication:
    """Test API key generation, authentication, and authorization."""
    
    def test_api_key_creation(self, protegrity_user):
        """Should create API key with hashed storage."""
        api_key, raw_key = ApiKey.create_for_user(
            user=protegrity_user,
            name="Test Key",
            scopes=["chat"]
        )
        
        assert api_key.user == protegrity_user
        assert api_key.name == "Test Key"
        assert api_key.prefix == raw_key[:8]
        assert api_key.hashed_key != raw_key  # Should be hashed
        assert api_key.is_active is True
        assert api_key.scopes == ["chat"]
        assert len(raw_key) == 43  # URL-safe base64 of 32 bytes
    
    def test_api_key_check_valid_key(self, protegrity_user):
        """Should validate correct API key."""
        api_key, raw_key = ApiKey.create_for_user(protegrity_user, "Test")
        
        assert api_key.check_key(raw_key) is True
    
    def test_api_key_check_invalid_key(self, protegrity_user):
        """Should reject incorrect API key."""
        api_key, raw_key = ApiKey.create_for_user(protegrity_user, "Test")
        
        assert api_key.check_key("wrong_key_here") is False
    
    def test_authenticate_with_valid_api_key_authorization_header(self, protegrity_user, fin_model):
        """Should authenticate with valid API key in Authorization header."""
        api_key, raw_key = ApiKey.create_for_user(protegrity_user, "Test")
        
        client = APIClient()
        response = client.get(
            '/api/models/',
            HTTP_AUTHORIZATION=f'Api-Key {raw_key}'
        )
        
        assert response.status_code == 200
    
    def test_authenticate_with_valid_api_key_custom_header(self, protegrity_user, fin_model):
        """Should authenticate with valid API key in X-API-Key header."""
        api_key, raw_key = ApiKey.create_for_user(protegrity_user, "Test")
        
        client = APIClient()
        response = client.get(
            '/api/models/',
            HTTP_X_API_KEY=raw_key
        )
        
        assert response.status_code == 200
    
    def test_authenticate_with_invalid_api_key(self, fin_model):
        """Should reject invalid API key."""
        client = APIClient()
        response = client.get(
            '/api/models/',
            HTTP_AUTHORIZATION='Api-Key invalid_key_here_123456789'
        )
        
        assert response.status_code == 401
    
    def test_authenticate_with_inactive_api_key(self, protegrity_user, fin_model):
        """Should reject inactive API key."""
        api_key, raw_key = ApiKey.create_for_user(protegrity_user, "Test")
        api_key.is_active = False
        api_key.save()
        
        client = APIClient()
        response = client.get(
            '/api/models/',
            HTTP_AUTHORIZATION=f'Api-Key {raw_key}'
        )
        
        assert response.status_code == 401
    
    def test_authenticate_with_expired_api_key(self, protegrity_user, fin_model):
        """Should reject expired API key."""
        api_key, raw_key = ApiKey.create_for_user(protegrity_user, "Test")
        api_key.expires_at = timezone.now() - timedelta(days=1)
        api_key.save()
        
        client = APIClient()
        response = client.get(
            '/api/models/',
            HTTP_AUTHORIZATION=f'Api-Key {raw_key}'
        )
        
        assert response.status_code == 401
        data = response.json()
        assert 'expired' in data['detail'].lower()
    
    def test_api_key_inherits_user_role(self, standard_user, fin_model, claude_model):
        """API key should inherit user's role and permissions."""
        api_key, raw_key = ApiKey.create_for_user(standard_user, "Test")
        
        client = APIClient()
        
        # Should see only STANDARD models
        response = client.get(
            '/api/models/',
            HTTP_AUTHORIZATION=f'Api-Key {raw_key}'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['models']) == 1
        assert data['models'][0]['id'] == 'fin'
    
    def test_api_key_updates_last_used_at(self, protegrity_user, fin_model):
        """Should update last_used_at on successful authentication."""
        api_key, raw_key = ApiKey.create_for_user(protegrity_user, "Test")
        
        assert api_key.last_used_at is None
        
        client = APIClient()
        response = client.get(
            '/api/models/',
            HTTP_AUTHORIZATION=f'Api-Key {raw_key}'
        )
        
        assert response.status_code == 200
        
        # Refresh from database
        api_key.refresh_from_db()
        assert api_key.last_used_at is not None
        assert api_key.last_used_at <= timezone.now()
    
    def test_api_key_chat_with_forbidden_model(self, standard_user, claude_model):
        """API key with STANDARD role should be forbidden from PROTEGRITY models."""
        api_key, raw_key = ApiKey.create_for_user(standard_user, "Test")
        
        client = APIClient()
        response = client.post(
            '/api/chat/',
            {'message': 'Hello', 'model_id': 'claude'},
            format='json',
            HTTP_AUTHORIZATION=f'Api-Key {raw_key}'
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data['error']['code'] == 'forbidden_model'


@pytest.mark.django_db
class TestResourceMinRoleDefaults:
    """Test that resources have correct default min_role values."""
    
    def test_llm_provider_defaults_to_protegrity(self, db):
        """New LLM providers should default to PROTEGRITY min_role."""
        llm = LLMProvider.objects.create(
            id="test-llm",
            name="Test LLM",
            provider_type="custom",
            is_active=True
        )
        
        assert llm.min_role == "PROTEGRITY"
    
    def test_agent_defaults_to_protegrity(self, db, fin_model):
        """New agents should default to PROTEGRITY min_role."""
        agent = Agent.objects.create(
            id="test-agent-2",
            name="Test Agent 2",
            system_prompt="Test",
            default_llm=fin_model,
            is_active=True
        )
        
        assert agent.min_role == "PROTEGRITY"
    
    def test_tool_defaults_to_protegrity(self, db):
        """New tools should default to PROTEGRITY min_role."""
        tool = Tool.objects.create(
            id="test-tool-2",
            name="Test Tool 2",
            tool_type="custom",
            description="Test",
            is_active=True
        )
        
        assert tool.min_role == "PROTEGRITY"
