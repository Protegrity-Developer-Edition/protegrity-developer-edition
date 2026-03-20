"""
Tests for default LLM selection logic.

This module tests the get_default_llm_for_user helper function and the
/api/chat/ endpoint's behavior when no model_id is specified.
"""

import pytest
from django.contrib.auth.models import User, Group
from apps.core.models import LLMProvider, UserProfile
from apps.core.utils import get_default_llm_for_user


@pytest.mark.django_db
class TestDefaultLLMSelection:
    """Test default LLM selection for different user roles."""
    
    def test_standard_user_gets_fin_ai(self):
        """Standard users should get Fin AI as default (only STANDARD model)."""
        # Create a STANDARD user
        user = User.objects.create_user(username="standard_user", password="test123")
        standard_group, _ = Group.objects.get_or_create(name="Standard Users")
        user.groups.add(standard_group)
        
        # Create Fin AI model (STANDARD role)
        fin = LLMProvider.objects.create(
            id="fin",
            name="Fin AI",
            provider_type="fin",
            is_active=True,
            min_role="STANDARD",
            display_order=1
        )
        
        # Create Bedrock model (PROTEGRITY role)
        LLMProvider.objects.create(
            id="bedrock",
            name="Claude Sonnet",
            provider_type="bedrock",
            is_active=True,
            min_role="PROTEGRITY",
            display_order=2
        )
        
        # Standard user should only get Fin AI
        default_llm = get_default_llm_for_user(user)
        assert default_llm is not None
        assert default_llm.id == "fin"
        assert default_llm.name == "Fin AI"
    
    def test_protegrity_user_gets_first_by_display_order(self):
        """Protegrity users should get first active model by display_order."""
        # Create a PROTEGRITY user
        user = User.objects.create_user(username="protegrity_user", password="test123")
        protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
        user.groups.add(protegrity_group)
        
        # Clear any existing LLM providers to avoid interference
        LLMProvider.objects.all().delete()
        
        # Create multiple models with different display orders
        bedrock = LLMProvider.objects.create(
            id="bedrock",
            name="Claude Sonnet",
            provider_type="bedrock",
            is_active=True,
            min_role="PROTEGRITY",
            display_order=1
        )
        
        LLMProvider.objects.create(
            id="fin",
            name="Fin AI",
            provider_type="fin",
            is_active=True,
            min_role="STANDARD",
            display_order=2
        )
        
        # Protegrity user should get first by display_order
        default_llm = get_default_llm_for_user(user)
        assert default_llm is not None
        assert default_llm.id == "bedrock"
        assert default_llm.name == "Claude Sonnet"
    
    def test_user_with_no_available_models(self):
        """Users with no available models should get None."""
        # Create a STANDARD user
        user = User.objects.create_user(username="no_models_user", password="test123")
        standard_group, _ = Group.objects.get_or_create(name="Standard Users")
        user.groups.add(standard_group)
        
        # Create only PROTEGRITY models (not accessible to STANDARD)
        LLMProvider.objects.create(
            id="bedrock",
            name="Claude Sonnet",
            provider_type="bedrock",
            is_active=True,
            min_role="PROTEGRITY",
            display_order=1
        )
        
        # Should return None - no accessible models
        default_llm = get_default_llm_for_user(user)
        assert default_llm is None
    
    def test_inactive_models_are_excluded(self):
        """Inactive models should not be returned as defaults."""
        # Create a STANDARD user
        user = User.objects.create_user(username="inactive_test_user", password="test123")
        standard_group, _ = Group.objects.get_or_create(name="Standard Users")
        user.groups.add(standard_group)
        
        # Create an inactive Fin AI model
        LLMProvider.objects.create(
            id="fin",
            name="Fin AI",
            provider_type="fin",
            is_active=False,  # Inactive!
            min_role="STANDARD",
            display_order=1
        )
        
        # Should return None - only model is inactive
        default_llm = get_default_llm_for_user(user)
        assert default_llm is None


@pytest.mark.django_db
class TestChatAPIDefaultLLM:
    """Test /api/chat/ endpoint uses default LLM when none specified."""
    
    def test_new_conversation_without_model_uses_default(self, client):
        """POST /api/chat/ without model_id should use default LLM for user."""
        # Create and authenticate a STANDARD user
        user = User.objects.create_user(username="chatuser", password="test123")
        standard_group, _ = Group.objects.get_or_create(name="Standard Users")
        user.groups.add(standard_group)
        client.force_login(user)
        
        # Create Fin AI model
        LLMProvider.objects.create(
            id="fin",
            name="Fin AI",
            provider_type="fin",
            is_active=True,
            min_role="STANDARD",
            display_order=1
        )
        
        # Send chat message without model_id
        response = client.post(
            "/api/chat/",
            data={"message": "Hello, test message"},
            content_type="application/json"
        )
        
        # Should succeed (not 400)
        assert response.status_code in [200, 202]
        
        # Conversation should be created with Fin AI
        data = response.json()
        assert "db_conversation_id" in data or "conversation_id" in data
    
    def test_new_conversation_no_available_models_returns_error(self, client):
        """POST /api/chat/ with no available models should return 400."""
        # Create and authenticate a STANDARD user
        user = User.objects.create_user(username="nomodels", password="test123")
        standard_group, _ = Group.objects.get_or_create(name="Standard Users")
        user.groups.add(standard_group)
        client.force_login(user)
        
        # Create only PROTEGRITY models (not accessible)
        LLMProvider.objects.create(
            id="bedrock",
            name="Claude Sonnet",
            provider_type="bedrock",
            is_active=True,
            min_role="PROTEGRITY",
            display_order=1
        )
        
        # Send chat message without model_id
        response = client.post(
            "/api/chat/",
            data={"message": "Hello, test message"},
            content_type="application/json"
        )
        
        # Should return 400 with clear error
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "no_available_llm"
        assert "administrator" in data["error"]["message"].lower()
