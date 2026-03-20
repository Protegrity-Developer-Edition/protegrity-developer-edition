"""
Tests for LLM provider abstraction layer.

Test Coverage:
- BaseLLMProvider interface
- DummyProvider functionality
- Provider factory (get_provider)
- /api/chat/ with DummyProvider
- /api/chat/poll/ with DummyProvider
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.core.models import Conversation, Message, LLMProvider, Agent
from apps.core.providers import (
    ProviderResult,
    BaseLLMProvider,
    DummyProvider,
    get_provider
)

User = get_user_model()


class ProviderResultTestCase(TestCase):
    """Test ProviderResult wrapper class."""
    
    def test_completed_result(self):
        """Test creating a completed result."""
        result = ProviderResult(
            status="completed",
            content="Test response"
        )
        
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.content, "Test response")
        self.assertIsNone(result.pending_message_id)
    
    def test_pending_result(self):
        """Test creating a pending result."""
        result = ProviderResult(
            status="pending",
            pending_message_id="msg_123"
        )
        
        self.assertEqual(result.status, "pending")
        self.assertIsNone(result.content)
        self.assertEqual(result.pending_message_id, "msg_123")


class DummyProviderTestCase(TestCase):
    """Test DummyProvider implementation."""
    
    def setUp(self):
        """Set up test data."""
        self.dummy_llm = LLMProvider.objects.create(
            id='dummy',
            name='Dummy LLM',
            provider_type='custom',
            is_active=True,
            requires_polling=False
        )
        
        self.agent = Agent.objects.create(
            id='test-agent',
            name='Test Agent',
            description='Test agent',
            system_prompt='You are a test agent',
            default_llm=self.dummy_llm,
            is_active=True
        )
        
        self.conversation = Conversation.objects.create(
            title='Test Chat',
            model_id='dummy',
            primary_agent=self.agent,
            primary_llm=self.dummy_llm
        )
    
    def test_dummy_provider_send_message(self):
        """Test DummyProvider returns completed result immediately."""
        # Create user message
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='Hello, test!'
        )
        
        # Get provider and send message
        provider = DummyProvider(self.dummy_llm)
        messages = self.conversation.messages.all()
        result = provider.send_message(self.conversation, messages, agent=self.agent)
        
        # Verify result
        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(result.content)
        self.assertIn("Dummy Response", result.content)
        self.assertIn("Test Agent", result.content)
        self.assertIn("Dummy LLM", result.content)
        self.assertIn("Hello, test!", result.content)
    
    def test_dummy_provider_poll_response(self):
        """Test DummyProvider poll returns None (synchronous)."""
        provider = DummyProvider(self.dummy_llm)
        result = provider.poll_response(self.conversation)
        
        self.assertIsNone(result)
    
    def test_dummy_provider_echoes_user_message(self):
        """Test DummyProvider includes user message in response."""
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='What is 2+2?'
        )
        
        provider = DummyProvider(self.dummy_llm)
        messages = self.conversation.messages.all()
        result = provider.send_message(self.conversation, messages, agent=self.agent)
        
        self.assertIn("What is 2+2?", result.content)
    
    def test_dummy_provider_handles_long_message(self):
        """Test DummyProvider truncates long messages."""
        long_message = "x" * 300
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            content=long_message
        )
        
        provider = DummyProvider(self.dummy_llm)
        messages = self.conversation.messages.all()
        result = provider.send_message(self.conversation, messages, agent=self.agent)
        
        # Should truncate at 200 chars
        self.assertIn("...", result.content)


class ProviderFactoryTestCase(TestCase):
    """Test get_provider factory function."""
    
    def setUp(self):
        """Set up test data."""
        self.dummy_llm = LLMProvider.objects.create(
            id='dummy',
            name='Dummy LLM',
            provider_type='custom',
            is_active=True
        )
    
    def test_get_provider_with_none_returns_dummy(self):
        """Test that None returns DummyProvider."""
        provider = get_provider(None)
        
        self.assertIsInstance(provider, DummyProvider)
        self.assertEqual(provider.llm_provider.id, "dummy")
    
    def test_get_provider_with_dummy_llm(self):
        """Test getting provider for dummy LLM."""
        provider = get_provider(self.dummy_llm)
        
        self.assertIsInstance(provider, DummyProvider)
        self.assertEqual(provider.llm_provider, self.dummy_llm)
    
    def test_get_provider_is_base_llm_provider(self):
        """Test that returned provider implements BaseLLMProvider."""
        provider = get_provider(self.dummy_llm)
        
        self.assertIsInstance(provider, BaseLLMProvider)
        self.assertTrue(hasattr(provider, 'send_message'))
        self.assertTrue(hasattr(provider, 'poll_response'))


class ChatEndpointWithDummyProviderTestCase(TestCase):
    
    def setUp(self):
        # Create authenticated user via Django Groups
        self.user = User.objects.create_user(
            username='testuser@example.com',
            password='testpass123'
        )
        from django.contrib.auth.models import Group
        protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
        self.user.groups.add(protegrity_group)
        
        # Use APIClient and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.dummy_llm = LLMProvider.objects.create(
            id='dummy',
            name='Dummy LLM',
            provider_type='custom',
            is_active=True,
            requires_polling=False
        )
        
        self.agent = Agent.objects.create(
            id='test-agent',
            name='Test Agent',
            description='Test agent',
            system_prompt='You are helpful',
            default_llm=self.dummy_llm,
            is_active=True
        )
    
    def test_chat_with_dummy_provider(self):
        """Test POST /api/chat/ with DummyProvider."""
        response = self.client.post(
            '/api/chat/',
            data={
                'message': 'Hello, world!',
                'model_id': 'dummy',
                'agent_id': 'test-agent',
                'protegrity_mode': 'none'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['status'], 'completed')
        self.assertIn('conversation_id', data)
        self.assertIn('messages', data)
        self.assertEqual(len(data['messages']), 2)
        
        # Check assistant message
        assistant_msg = data['messages'][1]
        self.assertEqual(assistant_msg['role'], 'assistant')
        self.assertIn('Dummy Response', assistant_msg['content'])
        self.assertIn('Hello, world!', assistant_msg['content'])
    
    def test_chat_creates_message_with_llm_provider(self):
        """Test that assistant message has llm_provider set."""
        response = self.client.post(
            '/api/chat/',
            data={
                'message': 'Test message',
                'model_id': 'dummy',
                'agent_id': 'test-agent',
                'protegrity_mode': 'none'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check database
        conversation = Conversation.objects.get(id=data['conversation_id'])
        assistant_msg = conversation.messages.filter(role='assistant').first()
        
        self.assertIsNotNone(assistant_msg)
        self.assertEqual(assistant_msg.llm_provider, self.dummy_llm)
        self.assertEqual(assistant_msg.agent, self.agent)
        self.assertFalse(assistant_msg.pending)
    
    def test_chat_fallback_to_agent_default_llm(self):
        """Test that conversation uses agent's default_llm if not specified."""
        response = self.client.post(
            '/api/chat/',
            data={
                'message': 'Test',
                'agent_id': 'test-agent',
                # No model_id provided
                'protegrity_mode': 'none'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        conversation = Conversation.objects.get(id=data['conversation_id'])
        self.assertEqual(conversation.primary_llm, self.dummy_llm)


class PollEndpointWithDummyProviderTestCase(TestCase):
    """Test /api/chat/poll/ endpoint with DummyProvider."""
    
    def setUp(self):
        """Set up test data."""
        # Create authenticated user
        self.user = User.objects.create_user(
            username='testuser2@example.com',
            password='testpass123'
        )
        self.user.profile.role = 'PROTEGRITY'
        self.user.profile.save()
        
        # Use APIClient and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.dummy_llm = LLMProvider.objects.create(
            id='dummy',
            name='Dummy LLM',
            provider_type='custom',
            is_active=True,
            requires_polling=False
        )
        
        self.conversation = Conversation.objects.create(
            title='Test Chat',
            model_id='dummy',
            primary_llm=self.dummy_llm
        )
    
    def test_poll_with_no_pending_message(self):
        """Test polling when no pending message exists (conversation not found)."""
        # Use a valid UUID format for conversation ID
        import uuid
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(f'/api/chat/poll/{fake_uuid}/')
        
        self.assertEqual(response.status_code, 404)
    
    def test_poll_dummy_provider_returns_pending(self):
        """Test that polling DummyProvider returns pending (sync provider)."""
        # Note: After Task 3 refactor, poll endpoint expects conversation UUID
        # DummyProvider.poll_response() returns None for sync providers
        
        # Create a pending message (no longer needs fin_conversation_id)
        Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            content='',
            pending=True,
            llm_provider=self.dummy_llm
        )
        
        # Poll using the conversation UUID (not Fin conversation ID)
        response = self.client.get(f'/api/chat/poll/{self.conversation.id}/')
        
        # DummyProvider.poll_response() returns None, so status should be "pending"
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'pending')
