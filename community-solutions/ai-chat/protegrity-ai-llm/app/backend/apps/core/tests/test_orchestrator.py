"""
Tests for Chat Orchestrator and Tool Routing (Task 3)

This test suite covers:
1. ChatOrchestrator.handle_user_message() - message processing flow
2. ChatOrchestrator.poll() - async response handling
3. Tool routing and execution via execute_tool_calls()
4. Integration with DummyProvider tool call simulation
5. End-to-end API tests with /api/chat/ and /api/chat/poll/

Test Organization:
- TestToolRouter: Tool execution and permission validation
- TestChatOrchestrator: Orchestrator flow and message creation
- TestChatAPIWithOrchestrator: API endpoint integration
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from apps.core.models import Conversation, Message, LLMProvider, Agent, Tool

User = get_user_model()
from apps.core.tool_router import execute_tool_calls, _execute_protegrity_tool
from apps.core.orchestrator import ChatOrchestrator
import json


class TestToolRouter(TestCase):
    """Test tool routing and execution logic"""
    
    def setUp(self):
        """Create test fixtures"""
        # Create authenticated user
        self.user = User.objects.create_user(
            username='testuser@example.com',
            password='testpass123'
        )
        self.user.profile.role = 'PROTEGRITY'
        self.user.profile.save()
        
        # Create LLM
        self.llm = LLMProvider.objects.create(
            id="dummy",
            name="Dummy LLM",
            provider_type="dummy",
            is_active=True
        )
        
        # Create tools
        self.redact_tool = Tool.objects.create(
            id="protegrity-redact",
            name="Protegrity Redact",
            tool_type="protegrity",
            description="Redact sensitive data",
            is_active=True
        )
        
        self.classify_tool = Tool.objects.create(
            id="protegrity-classify",
            name="Protegrity Classify",
            tool_type="protegrity",
            description="Classify and discover PII",
            is_active=True
        )
        
        self.disabled_tool = Tool.objects.create(
            id="protegrity-disabled",
            name="Disabled Tool",
            tool_type="protegrity",
            description="This tool is disabled",
            is_active=False
        )
        
        # Create agent with tools
        self.agent = Agent.objects.create(
            id="test-agent",
            name="Test Agent",
            description="Agent for testing",
            default_llm=self.llm,
            is_active=True
        )
        self.agent.tools.add(self.redact_tool, self.classify_tool, self.disabled_tool)
    
    def test_execute_tool_calls_empty_list(self):
        """Empty tool_calls list should return empty results"""
        results = execute_tool_calls(self.agent, [])
        self.assertEqual(results, [])
    
    def test_execute_tool_calls_no_agent(self):
        """Tool calls without agent should return errors"""
        tool_calls = [
            {
                "tool_name": "protegrity-redact",
                "arguments": {"text": "test"},
                "call_id": "call_1"
            }
        ]
        
        results = execute_tool_calls(None, tool_calls)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["call_id"], "call_1")
        self.assertIn("error", results[0])
        self.assertIn("not authorized", results[0]["error"])
    
    def test_execute_tool_calls_unauthorized_tool(self):
        """Agent without tool access should get error"""
        # Create agent without tools
        agent_no_tools = Agent.objects.create(
            id="agent-no-tools",
            name="Agent Without Tools",
            default_llm=self.llm,
            is_active=True
        )
        
        tool_calls = [
            {
                "tool_name": "protegrity-redact",
                "arguments": {"text": "SSN: 123-45-6789"},
                "call_id": "call_1"
            }
        ]
        
        results = execute_tool_calls(agent_no_tools, tool_calls)
        
        self.assertEqual(len(results), 1)
        self.assertIn("error", results[0])
        self.assertIn("not authorized", results[0]["error"])
    
    def test_execute_tool_calls_disabled_tool(self):
        """Disabled tool should return error"""
        tool_calls = [
            {
                "tool_name": "protegrity-disabled",
                "arguments": {"text": "test"},
                "call_id": "call_1"
            }
        ]
        
        results = execute_tool_calls(self.agent, tool_calls)
        
        self.assertEqual(len(results), 1)
        self.assertIn("error", results[0])
        self.assertIn("disabled", results[0]["error"])
    
    def test_execute_tool_calls_redact_success(self):
        """Redact tool should execute successfully"""
        tool_calls = [
            {
                "tool_name": "protegrity-redact",
                "arguments": {"text": "My email is test@example.com"},
                "call_id": "call_1"
            }
        ]
        
        results = execute_tool_calls(self.agent, tool_calls)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["call_id"], "call_1")
        self.assertEqual(results[0]["tool_name"], "protegrity-redact")
        self.assertIn("output", results[0])
        self.assertIn("redacted_text", results[0]["output"])
    
    def test_execute_tool_calls_classify_success(self):
        """Classify tool should execute successfully"""
        tool_calls = [
            {
                "tool_name": "protegrity-classify",
                "arguments": {"text": "John Doe lives in New York"},
                "call_id": "call_1"
            }
        ]
        
        results = execute_tool_calls(self.agent, tool_calls)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tool_name"], "protegrity-classify")
        self.assertIn("output", results[0])
        self.assertIn("entities", results[0]["output"])
    
    def test_execute_multiple_tool_calls(self):
        """Should handle multiple tool calls in sequence"""
        tool_calls = [
            {
                "tool_name": "protegrity-redact",
                "arguments": {"text": "SSN: 123-45-6789"},
                "call_id": "call_1"
            },
            {
                "tool_name": "protegrity-classify",
                "arguments": {"text": "Email: test@example.com"},
                "call_id": "call_2"
            }
        ]
        
        results = execute_tool_calls(self.agent, tool_calls)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["call_id"], "call_1")
        self.assertEqual(results[1]["call_id"], "call_2")
        self.assertIn("output", results[0])
        self.assertIn("output", results[1])


class TestChatOrchestrator(TestCase):
    """Test ChatOrchestrator flow and logic"""
    
    def setUp(self):
        """Create test fixtures"""
        # Create authenticated user
        self.user = User.objects.create_user(
            username='testuser2@example.com',
            password='testpass123'
        )
        self.user.profile.role = 'PROTEGRITY'
        self.user.profile.save()
        
        # Create LLM
        self.llm = LLMProvider.objects.create(
            id="dummy",
            name="Dummy LLM",
            provider_type="dummy",
            is_active=True
        )
        
        # Create tools
        self.redact_tool = Tool.objects.create(
            id="protegrity-redact",
            name="Protegrity Redact",
            tool_type="protegrity",
            is_active=True
        )
        
        # Create agent
        self.agent = Agent.objects.create(
            id="test-agent",
            name="Test Agent",
            default_llm=self.llm,
            is_active=True
        )
        self.agent.tools.add(self.redact_tool)
        
        # Create conversation
        self.conversation = Conversation.objects.create(
            title="Test Conversation",
            primary_agent=self.agent,
            primary_llm=self.llm,
            model_id=self.llm.id
        )
    
    def test_resolve_agent_and_llm(self):
        """Should resolve agent and LLM from conversation"""
        orchestrator = ChatOrchestrator()
        agent, llm = orchestrator._resolve_agent_and_llm(self.conversation)
        
        self.assertEqual(agent, self.agent)
        self.assertEqual(llm, self.llm)
    
    def test_resolve_fallback_to_agent_default_llm(self):
        """Should use agent's default_llm if primary_llm is None"""
        conversation = Conversation.objects.create(
            title="Test",
            primary_agent=self.agent,
            primary_llm=None
        )
        
        orchestrator = ChatOrchestrator()
        agent, llm = orchestrator._resolve_agent_and_llm(conversation)
        
        self.assertEqual(agent, self.agent)
        self.assertEqual(llm, self.agent.default_llm)
        
        # Should update conversation
        conversation.refresh_from_db()
        self.assertEqual(conversation.primary_llm, self.agent.default_llm)
    
    def test_handle_user_message_creates_assistant_message(self):
        """Should create assistant message after processing"""
        # Create user message
        user_msg = Message.objects.create(
            conversation=self.conversation,
            role="user",
            content="Hello world"
        )
        
        orchestrator = ChatOrchestrator()
        result = orchestrator.handle_user_message(self.conversation, user_msg)
        
        self.assertEqual(result["status"], "completed")
        self.assertIsNotNone(result["assistant_message"])
        
        assistant_msg = result["assistant_message"]
        self.assertEqual(assistant_msg.role, "assistant")
        self.assertEqual(assistant_msg.conversation, self.conversation)
        self.assertEqual(assistant_msg.agent, self.agent)
        self.assertEqual(assistant_msg.llm_provider, self.llm)
        self.assertFalse(assistant_msg.pending)
    
    def test_handle_user_message_with_tool_calls(self):
        """Should execute tools when DummyProvider triggers them"""
        # Message with "ssn" triggers tool call in DummyProvider
        user_msg = Message.objects.create(
            conversation=self.conversation,
            role="user",
            content="My SSN is 123-45-6789"
        )
        
        orchestrator = ChatOrchestrator()
        result = orchestrator.handle_user_message(self.conversation, user_msg)
        
        self.assertEqual(result["status"], "completed")
        self.assertGreater(len(result["tool_results"]), 0)
        
        # Check tool was executed
        tool_result = result["tool_results"][0]
        self.assertEqual(tool_result["tool_name"], "protegrity-redact")
        self.assertIn("output", tool_result)
    
    def test_handle_user_message_no_llm_error(self):
        """Should return error message when no LLM available"""
        conversation = Conversation.objects.create(
            title="Test",
            primary_agent=None,
            primary_llm=None
        )
        
        user_msg = Message.objects.create(
            conversation=conversation,
            role="user",
            content="Hello"
        )
        
        orchestrator = ChatOrchestrator()
        result = orchestrator.handle_user_message(conversation, user_msg)
        
        self.assertEqual(result["status"], "error")
        self.assertIsNotNone(result["assistant_message"])
        self.assertIn("No LLM provider", result["assistant_message"].content)


class TestChatAPIWithOrchestrator(TestCase):
    """Test API endpoints with ChatOrchestrator integration"""
    
    def setUp(self):
        """Create test fixtures"""
        # Create authenticated user via Django Groups
        self.user = User.objects.create_user(
            username='testuser3@example.com',
            password='testpass123'
        )
        from django.contrib.auth.models import Group
        protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
        self.user.groups.add(protegrity_group)
        
        # Use APIClient and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create LLM
        self.llm = LLMProvider.objects.create(
            id="dummy",
            name="Dummy LLM",
            provider_type="dummy",
            is_active=True
        )
        
        # Create tools
        self.redact_tool = Tool.objects.create(
            id="protegrity-redact",
            name="Protegrity Redact",
            tool_type="protegrity",
            is_active=True
        )
        
        self.classify_tool = Tool.objects.create(
            id="protegrity-classify",
            name="Protegrity Classify",
            tool_type="protegrity",
            is_active=True
        )
        
        # Create agent with tools
        self.agent = Agent.objects.create(
            id="test-agent",
            name="Test Agent",
            default_llm=self.llm,
            is_active=True
        )
        self.agent.tools.add(self.redact_tool, self.classify_tool)
    
    def test_chat_endpoint_creates_conversation_and_messages(self):
        """POST /api/chat/ should create conversation and messages"""
        response = self.client.post(
            '/api/chat/',
            data=json.dumps({
                "message": "Hello from test",
                "agent_id": "test-agent",
                "model_id": "dummy"
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("conversation_id", data)
        self.assertEqual(data["status"], "completed")
        self.assertIn("messages", data)
        self.assertEqual(len(data["messages"]), 2)  # user + assistant
    
    def test_chat_endpoint_with_tool_trigger(self):
        """Should execute tools when message triggers them"""
        response = self.client.post(
            '/api/chat/',
            data=json.dumps({
                "message": "My SSN is 123-45-6789",  # Triggers redact tool
                "agent_id": "test-agent",
                "model_id": "dummy"
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["status"], "completed")
        self.assertIn("tool_results", data)
        self.assertGreater(len(data["tool_results"]), 0)
        
        # Verify tool was executed
        tool_result = data["tool_results"][0]
        self.assertEqual(tool_result["tool_name"], "protegrity-redact")
    
    def test_chat_endpoint_with_classify_trigger(self):
        """Should execute classify tool when triggered"""
        response = self.client.post(
            '/api/chat/',
            data=json.dumps({
                "message": "Please classify this text for PII",
                "agent_id": "test-agent",
                "model_id": "dummy"
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("tool_results", data)
        # Should have classify tool call
        tool_names = [tr["tool_name"] for tr in data["tool_results"]]
        self.assertIn("protegrity-classify", tool_names)
    
    def test_chat_endpoint_tracks_agent_and_llm(self):
        """Should track agent and LLM in messages"""
        response = self.client.post(
            '/api/chat/',
            data=json.dumps({
                "message": "Test message",
                "agent_id": "test-agent",
                "model_id": "dummy"
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check conversation was created with tracking
        conversation = Conversation.objects.get(id=data["conversation_id"])
        self.assertEqual(conversation.primary_agent.id, "test-agent")
        self.assertEqual(conversation.primary_llm.id, "dummy")
        
        # Check assistant message has tracking
        assistant_msg = Message.objects.filter(
            conversation=conversation,
            role="assistant"
        ).first()
        
        self.assertIsNotNone(assistant_msg)
        self.assertEqual(assistant_msg.agent.id, "test-agent")
        self.assertEqual(assistant_msg.llm_provider.id, "dummy")
    
    def test_chat_endpoint_existing_conversation(self):
        """Should use existing conversation when conversation_id provided"""
        # Create initial conversation
        conversation = Conversation.objects.create(
            title="Existing",
            primary_agent=self.agent,
            primary_llm=self.llm,
            model_id=self.llm.id
        )
        
        response = self.client.post(
            '/api/chat/',
            data=json.dumps({
                "conversation_id": str(conversation.id),
                "message": "Follow-up message"
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["conversation_id"], str(conversation.id))
        
        # Should have 2 messages total
        msg_count = Message.objects.filter(conversation=conversation).count()
        self.assertEqual(msg_count, 2)


# Run with: python -m pytest apps/core/tests/test_orchestrator.py -v
