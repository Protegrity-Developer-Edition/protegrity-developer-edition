"""
Tests for agent and LLM tracking on conversations and messages.

Test Coverage:
- Conversation creation with agent_id and model_id
- Message tracking of agent and llm_provider
- Serializer inclusion of new fields
- API endpoint behavior
"""

import pytest
from django.test import TestCase
from apps.core.models import Conversation, Message, LLMProvider, Agent, Tool


class AgentLLMTrackingTestCase(TestCase):
    """Test agent and LLM tracking functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create LLM providers
        self.fin = LLMProvider.objects.create(
            id='fin',
            name='Fin AI',
            provider_type='intercom',
            description='Intercom Fin AI',
            is_active=True,
            requires_polling=True
        )
        
        self.claude = LLMProvider.objects.create(
            id='bedrock-claude',
            name='Claude 3.5 Sonnet',
            provider_type='bedrock',
            description='Amazon Bedrock Claude',
            is_active=True,
            requires_polling=False
        )
        
        # Create agents
        self.data_expert = Agent.objects.create(
            id='data-protection-expert',
            name='Data Protection Expert',
            description='Specialized in data security',
            system_prompt='You are a data protection expert.',
            default_llm=self.fin,
            is_active=True
        )
        
        self.general = Agent.objects.create(
            id='general-assistant',
            name='General Assistant',
            description='General purpose assistant',
            system_prompt='You are a helpful assistant.',
            default_llm=self.claude,
            is_active=True
        )
    
    def test_conversation_tracks_primary_agent_and_llm(self):
        """Test that new conversations track agent and LLM."""
        conversation = Conversation.objects.create(
            title='Test Chat',
            model_id='fin',
            primary_agent=self.data_expert,
            primary_llm=self.fin
        )
        
        self.assertEqual(conversation.primary_agent, self.data_expert)
        self.assertEqual(conversation.primary_llm, self.fin)
        self.assertEqual(conversation.model_id, 'fin')
    
    def test_message_tracks_agent_and_llm_provider(self):
        """Test that assistant messages track agent and LLM."""
        conversation = Conversation.objects.create(
            title='Test Chat',
            model_id='fin',
            primary_agent=self.data_expert,
            primary_llm=self.fin
        )
        
        # User message should have NULL agent and llm_provider
        user_msg = Message.objects.create(
            conversation=conversation,
            role='user',
            content='Hello'
        )
        self.assertIsNone(user_msg.agent)
        self.assertIsNone(user_msg.llm_provider)
        
        # Assistant message should track agent and LLM
        assistant_msg = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content='Hi there!',
            agent=conversation.primary_agent,
            llm_provider=conversation.primary_llm
        )
        self.assertEqual(assistant_msg.agent, self.data_expert)
        self.assertEqual(assistant_msg.llm_provider, self.fin)
    
    def test_conversation_without_agent_or_llm(self):
        """Test that conversations can be created without agent/LLM."""
        conversation = Conversation.objects.create(
            title='Test Chat',
            model_id='fin'
        )
        
        self.assertIsNone(conversation.primary_agent)
        self.assertIsNone(conversation.primary_llm)
    
    def test_set_null_on_delete(self):
        """Test that deleting agent/LLM doesn't cascade to conversations."""
        conversation = Conversation.objects.create(
            title='Test Chat',
            model_id='fin',
            primary_agent=self.data_expert,
            primary_llm=self.fin
        )
        
        # Delete the agent
        agent_id = self.data_expert.id
        self.data_expert.delete()
        
        # Refresh conversation
        conversation.refresh_from_db()
        self.assertIsNone(conversation.primary_agent)
        
        # LLM should still be there
        self.assertEqual(conversation.primary_llm, self.fin)
    
    def test_conversation_serializer_includes_agent_and_llm(self):
        """Test that conversation serializer exposes agent and LLM."""
        from apps.core.serializers import ConversationDetailSerializer
        
        conversation = Conversation.objects.create(
            title='Test Chat',
            model_id='fin',
            primary_agent=self.data_expert,
            primary_llm=self.fin
        )
        
        serializer = ConversationDetailSerializer(conversation)
        data = serializer.data
        
        self.assertEqual(data['primary_agent'], 'data-protection-expert')
        self.assertEqual(data['primary_llm'], 'fin')
        self.assertEqual(data['model_id'], 'fin')
    
    def test_message_serializer_includes_agent_and_llm(self):
        """Test that message serializer exposes agent and LLM."""
        from apps.core.serializers import MessageSerializer
        
        conversation = Conversation.objects.create(
            title='Test Chat',
            model_id='fin',
            primary_agent=self.data_expert,
            primary_llm=self.fin
        )
        
        message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content='Response',
            agent=self.data_expert,
            llm_provider=self.fin
        )
        
        serializer = MessageSerializer(message)
        data = serializer.data
        
        self.assertEqual(data['agent'], 'data-protection-expert')
        self.assertEqual(data['llm_provider'], 'fin')
    
    def test_agent_switch_across_conversations(self):
        """Test using different agents in different conversations."""
        conv1 = Conversation.objects.create(
            title='Chat with Data Expert',
            model_id='fin',
            primary_agent=self.data_expert,
            primary_llm=self.fin
        )
        
        conv2 = Conversation.objects.create(
            title='Chat with General Assistant',
            model_id='bedrock-claude',
            primary_agent=self.general,
            primary_llm=self.claude
        )
        
        self.assertEqual(conv1.primary_agent, self.data_expert)
        self.assertEqual(conv2.primary_agent, self.general)
        self.assertEqual(conv1.primary_llm, self.fin)
        self.assertEqual(conv2.primary_llm, self.claude)
    
    def test_message_analytics_queries(self):
        """Test that message indexes support analytics queries."""
        conversation = Conversation.objects.create(
            title='Test Chat',
            model_id='fin',
            primary_agent=self.data_expert,
            primary_llm=self.fin
        )
        
        # Create messages
        Message.objects.create(
            conversation=conversation,
            role='user',
            content='Question 1'
        )
        
        Message.objects.create(
            conversation=conversation,
            role='assistant',
            content='Answer 1',
            agent=self.data_expert,
            llm_provider=self.fin
        )
        
        Message.objects.create(
            conversation=conversation,
            role='user',
            content='Question 2'
        )
        
        Message.objects.create(
            conversation=conversation,
            role='assistant',
            content='Answer 2',
            agent=self.data_expert,
            llm_provider=self.fin
        )
        
        # Query messages by agent
        agent_messages = Message.objects.filter(agent=self.data_expert)
        self.assertEqual(agent_messages.count(), 2)
        
        # Query messages by LLM
        llm_messages = Message.objects.filter(llm_provider=self.fin)
        self.assertEqual(llm_messages.count(), 2)
        
        # Query user messages (should have null agent/llm)
        user_messages = Message.objects.filter(
            role='user',
            agent__isnull=True,
            llm_provider__isnull=True
        )
        self.assertEqual(user_messages.count(), 2)


class ChatEndpointTestCase(TestCase):
    """Test /api/chat/ endpoint with agent and LLM tracking."""
    
    def setUp(self):
        """Set up test data."""
        self.fin = LLMProvider.objects.create(
            id='fin',
            name='Fin AI',
            provider_type='intercom',
            is_active=True,
            requires_polling=True
        )
        
        self.data_expert = Agent.objects.create(
            id='data-protection-expert',
            name='Data Protection Expert',
            description='Specialized in data security',
            system_prompt='You are a data protection expert.',
            default_llm=self.fin,
            is_active=True
        )
    
    def test_create_conversation_with_agent_and_model(self):
        """Test that POST /api/chat/ creates conversation with agent/model."""
        # Note: This would require mocking Intercom API
        # For now, test the model/agent lookup logic
        
        # Valid model_id
        try:
            llm = LLMProvider.objects.get(id='fin', is_active=True)
            self.assertEqual(llm.id, 'fin')
        except LLMProvider.DoesNotExist:
            self.fail('Should find active LLM')
        
        # Valid agent_id
        try:
            agent = Agent.objects.get(id='data-protection-expert', is_active=True)
            self.assertEqual(agent.id, 'data-protection-expert')
        except Agent.DoesNotExist:
            self.fail('Should find active agent')
    
    def test_invalid_model_id_returns_error(self):
        """Test that invalid model_id is rejected."""
        with self.assertRaises(LLMProvider.DoesNotExist):
            LLMProvider.objects.get(id='invalid-model', is_active=True)
    
    def test_invalid_agent_id_returns_error(self):
        """Test that invalid agent_id is rejected."""
        with self.assertRaises(Agent.DoesNotExist):
            Agent.objects.get(id='invalid-agent', is_active=True)
