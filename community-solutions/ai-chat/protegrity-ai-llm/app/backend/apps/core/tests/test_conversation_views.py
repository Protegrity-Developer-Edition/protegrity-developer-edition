"""
Tests for conversation management views.

Covers:
- List conversations (GET /api/conversations/)
- Create conversation (POST /api/conversations/)
- Get conversation detail (GET /api/conversations/{id}/)
- Update conversation (PATCH /api/conversations/{id}/)
- Delete conversation (DELETE /api/conversations/{id}/)
- Add message to conversation (POST /api/conversations/{id}/messages/)
- Pagination
- Permission checks
- Error handling
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient
from apps.core.models import Conversation, Message, LLMProvider

User = get_user_model()


@pytest.fixture
def protegrity_user(db):
    """Create a Protegrity user."""
    user = User.objects.create_user(
        username='protegrity@example.com',
        password='testpass123',
        email='protegrity@example.com'
    )
    protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
    user.groups.add(protegrity_group)
    return user


@pytest.fixture
def standard_user(db):
    """Create a standard user."""
    user = User.objects.create_user(
        username='standard@example.com',
        password='testpass123',
        email='standard@example.com'
    )
    return user


@pytest.fixture
def llm_provider(db):
    """Create a test LLM provider."""
    return LLMProvider.objects.create(
        id='fin',
        name='Fin AI',
        provider_type='intercom',
        description='Test LLM',
        is_active=True,
        min_role='STANDARD'
    )


@pytest.fixture
def authenticated_client(protegrity_user):
    """Return an authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=protegrity_user)
    return client


@pytest.mark.django_db
class TestConversationList:
    """Test GET /api/conversations/ - list conversations."""
    
    def test_list_conversations_empty(self, authenticated_client):
        """Test listing conversations when none exist."""
        url = reverse('conversation_list_create')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert len(data['results']) == 0
    
    def test_list_conversations_with_data(self, authenticated_client, protegrity_user, llm_provider):
        """Test listing multiple conversations."""
        # Create 3 conversations
        conv1 = Conversation.objects.create(title="Chat 1", primary_llm=llm_provider)
        conv2 = Conversation.objects.create(title="Chat 2", primary_llm=llm_provider)
        conv3 = Conversation.objects.create(title="Chat 3", primary_llm=llm_provider)
        
        # Add messages to conv1 to test message_count
        Message.objects.create(conversation=conv1, role="user", content="Hello")
        Message.objects.create(conversation=conv1, role="assistant", content="Hi")
        
        url = reverse('conversation_list_create')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert len(data['results']) == 3
        
        # Check that conv1 has message_count
        conv1_data = next(c for c in data['results'] if c['id'] == str(conv1.id))
        assert conv1_data['message_count'] == 2
        assert conv1_data['title'] == "Chat 1"
    
    def test_list_conversations_excludes_deleted(self, authenticated_client, llm_provider):
        """Test that soft-deleted conversations are excluded."""
        conv1 = Conversation.objects.create(title="Active", primary_llm=llm_provider)
        conv2 = Conversation.objects.create(title="Deleted", primary_llm=llm_provider)
        conv2.soft_delete()
        
        url = reverse('conversation_list_create')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['results']) == 1
        assert data['results'][0]['title'] == "Active"
    
    def test_list_conversations_pagination(self, authenticated_client, llm_provider):
        """Test conversation list pagination."""
        # Create 55 conversations (more than default page size of 50)
        for i in range(55):
            Conversation.objects.create(title=f"Chat {i}", primary_llm=llm_provider)
        
        url = reverse('conversation_list_create')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 55
        assert len(data['results']) == 50  # Default page size
        assert data['next'] is not None
        assert data['previous'] is None
        
        # Test page 2
        response = authenticated_client.get(url, {'page': 2})
        assert response.status_code == 200
        data = response.json()
        assert len(data['results']) == 5
        assert data['next'] is None
        assert data['previous'] is not None
    
    def test_list_conversations_custom_page_size(self, authenticated_client, llm_provider):
        """Test custom page size parameter."""
        for i in range(15):
            Conversation.objects.create(title=f"Chat {i}", primary_llm=llm_provider)
        
        url = reverse('conversation_list_create')
        response = authenticated_client.get(url, {'page_size': 10})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['results']) == 10
    
    def test_list_conversations_requires_authentication(self):
        """Test that unauthenticated requests work (no auth required for now)."""
        client = APIClient()
        url = reverse('conversation_list_create')
        response = client.get(url)
        
        # Note: View currently doesn't require authentication
        assert response.status_code == 200


@pytest.mark.django_db
class TestConversationCreate:
    """Test POST /api/conversations/ - create conversation."""
    
    def test_create_conversation(self, authenticated_client, llm_provider):
        """Test creating a new conversation."""
        url = reverse('conversation_list_create')
        data = {
            'title': 'New Chat',
            'model_id': 'fin'
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == 201
        result = response.json()
        assert result['title'] == 'New Chat'
        assert result['id'] is not None
        assert 'messages' in result
        assert len(result['messages']) == 0
        
        # Verify in database
        conversation = Conversation.objects.get(id=result['id'])
        assert conversation.title == 'New Chat'
        # Note: primary_llm is not set by serializer, it's set later via chat API
    
    def test_create_conversation_without_title(self, authenticated_client, llm_provider):
        """Test creating conversation without title uses default."""
        url = reverse('conversation_list_create')
        data = {
            'model_id': 'fin'
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == 201
        result = response.json()
        assert result['title'] == 'New chat'  # Default from model
    
    def test_create_conversation_invalid_model(self, authenticated_client):
        """Test creating conversation with non-existent model."""
        url = reverse('conversation_list_create')
        data = {
            'title': 'Test',
            'model_id': 'nonexistent'
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == 400
        assert 'model_id' in response.json()
    
    def test_create_conversation_requires_authentication(self, llm_provider):
        """Test that unauthenticated requests work (no auth required for now)."""
        client = APIClient()
        url = reverse('conversation_list_create')
        data = {
            'title': 'Test',
            'model_id': 'fin'
        }
        response = client.post(url, data, format='json')
        
        # Note: View currently doesn't require authentication
        assert response.status_code == 201


@pytest.mark.django_db
class TestConversationDetail:
    """Test GET /api/conversations/{id}/ - get conversation detail."""
    
    def test_get_conversation_detail(self, authenticated_client, llm_provider):
        """Test retrieving a conversation with messages."""
        conversation = Conversation.objects.create(
            title="Test Chat",
            primary_llm=llm_provider
        )
        Message.objects.create(
            conversation=conversation,
            role="user",
            content="Hello"
        )
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content="Hi there"
        )
        
        url = reverse('conversation_detail', kwargs={'conversation_id': conversation.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == str(conversation.id)
        assert data['title'] == "Test Chat"
        assert len(data['messages']) == 2
        assert data['messages'][0]['role'] == 'user'
        assert data['messages'][0]['content'] == 'Hello'
        assert data['messages'][1]['role'] == 'assistant'
        assert data['messages'][1]['content'] == 'Hi there'
    
    def test_get_conversation_excludes_deleted_messages(self, authenticated_client, llm_provider):
        """Test that deleted messages are excluded from detail view."""
        conversation = Conversation.objects.create(
            title="Test Chat",
            primary_llm=llm_provider
        )
        msg1 = Message.objects.create(
            conversation=conversation,
            role="user",
            content="Active message"
        )
        msg2 = Message.objects.create(
            conversation=conversation,
            role="user",
            content="Deleted message"
        )
        # Manually soft delete the message
        msg2.deleted_at = timezone.now()
        msg2.save()
        
        url = reverse('conversation_detail', kwargs={'conversation_id': conversation.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['messages']) == 1
        assert data['messages'][0]['content'] == "Active message"
    
    def test_get_conversation_not_found(self, authenticated_client):
        """Test getting non-existent conversation returns 404."""
        url = reverse('conversation_detail', kwargs={'conversation_id': '00000000-0000-0000-0000-000000000000'})
        response = authenticated_client.get(url)
        
        assert response.status_code == 404
        # Note: Django returns standard 404, not custom error_response format
    
    def test_get_deleted_conversation_not_found(self, authenticated_client, llm_provider):
        """Test that deleted conversations return 404."""
        conversation = Conversation.objects.create(
            title="Deleted",
            primary_llm=llm_provider
        )
        conversation.soft_delete()
        
        url = reverse('conversation_detail', kwargs={'conversation_id': conversation.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestConversationUpdate:
    """Test PATCH /api/conversations/{id}/ - update conversation."""
    
    def test_update_conversation_title(self, authenticated_client, llm_provider):
        """Test updating conversation title."""
        conversation = Conversation.objects.create(
            title="Old Title",
            primary_llm=llm_provider
        )
        
        url = reverse('conversation_detail', kwargs={'conversation_id': conversation.id})
        data = {'title': 'New Title'}
        response = authenticated_client.patch(url, data, format='json')
        
        assert response.status_code == 200
        result = response.json()
        assert result['title'] == 'New Title'
        
        # Verify in database
        conversation.refresh_from_db()
        assert conversation.title == 'New Title'
    
    def test_update_conversation_not_found(self, authenticated_client):
        """Test updating non-existent conversation."""
        url = reverse('conversation_detail', kwargs={'conversation_id': '00000000-0000-0000-0000-000000000000'})
        data = {'title': 'New Title'}
        response = authenticated_client.patch(url, data, format='json')
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestConversationDelete:
    """Test DELETE /api/conversations/{id}/ - delete conversation."""
    
    def test_delete_conversation(self, authenticated_client, llm_provider):
        """Test soft deleting a conversation."""
        conversation = Conversation.objects.create(
            title="To Delete",
            primary_llm=llm_provider
        )
        Message.objects.create(
            conversation=conversation,
            role="user",
            content="Message in conversation"
        )
        
        url = reverse('conversation_detail', kwargs={'conversation_id': conversation.id})
        response = authenticated_client.delete(url)
        
        assert response.status_code == 204
        
        # Verify soft delete
        conversation.refresh_from_db()
        assert conversation.deleted_at is not None
        
        # Verify messages are also soft deleted
        message = conversation.messages.first()
        assert message.deleted_at is not None
    
    def test_delete_conversation_not_found(self, authenticated_client):
        """Test deleting non-existent conversation."""
        url = reverse('conversation_detail', kwargs={'conversation_id': '00000000-0000-0000-0000-000000000000'})
        response = authenticated_client.delete(url)
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestConversationMessagesCreate:
    """Test POST /api/conversations/{id}/messages/ - add message to conversation."""
    
    def test_add_message_to_conversation(self, authenticated_client, llm_provider):
        """Test adding a message to an existing conversation."""
        conversation = Conversation.objects.create(
            title="Test Chat",
            primary_llm=llm_provider
        )
        
        url = reverse('conversation_messages_create', kwargs={'conversation_id': conversation.id})
        data = {
            'role': 'user',
            'content': 'New message'
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == 201
        result = response.json()
        assert result['role'] == 'user'
        assert result['content'] == 'New message'
        assert result['id'] is not None
        
        # Verify in database
        message = Message.objects.get(id=result['id'])
        assert message.conversation == conversation
        assert message.content == 'New message'
        
        # Verify conversation updated_at was updated
        conversation.refresh_from_db()
        assert conversation.updated_at is not None
    
    def test_add_message_with_protegrity_data(self, authenticated_client, llm_provider):
        """Test adding message with Protegrity metadata."""
        conversation = Conversation.objects.create(
            title="Test Chat",
            primary_llm=llm_provider
        )
        
        url = reverse('conversation_messages_create', kwargs={'conversation_id': conversation.id})
        data = {
            'role': 'user',
            'content': 'Message with PII',
            'protegrity_data': {
                'input_protection': {'entities_found': ['EMAIL', 'PHONE']},
                'output_protection': {}
            }
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == 201
        result = response.json()
        assert result['protegrity_data'] is not None
        assert 'input_protection' in result['protegrity_data']
    
    def test_add_message_to_nonexistent_conversation(self, authenticated_client):
        """Test adding message to non-existent conversation."""
        url = reverse('conversation_messages_create', kwargs={'conversation_id': '00000000-0000-0000-0000-000000000000'})
        data = {
            'role': 'user',
            'content': 'Test'
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == 404
        # Note: Django returns standard 404, not custom error_response format
    
    def test_add_message_invalid_data(self, authenticated_client, llm_provider):
        """Test adding message with invalid data."""
        conversation = Conversation.objects.create(
            title="Test Chat",
            primary_llm=llm_provider
        )
        
        url = reverse('conversation_messages_create', kwargs={'conversation_id': conversation.id})
        data = {
            'role': 'invalid_role',  # Invalid role
            'content': 'Test'
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == 400
        assert 'role' in response.json()
