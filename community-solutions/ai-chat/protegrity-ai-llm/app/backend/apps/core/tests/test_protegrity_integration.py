"""
Tests for Protegrity input/output protection integration in ChatOrchestrator.

Tests cover:
- Input protection before LLM call
- Output protection after LLM response
- Blocked input handling (guardrails rejection)
- Blocked output handling (guardrails rejection)
- Protected text usage in LLM history
- protegrity_data persistence on messages
"""

from django.test import TestCase
from unittest.mock import patch, MagicMock
from apps.core.models import Conversation, Message, Agent, LLMProvider, Tool
from apps.core.orchestrator import ChatOrchestrator


class TestProtegrityInputProtection(TestCase):
    """Test input protection flow in orchestrator."""
    
    def setUp(self):
        """Create test fixtures."""
        self.llm = LLMProvider.objects.create(
            id="test-llm",
            name="Test LLM",
            provider_type="dummy"
        )
        self.agent = Agent.objects.create(
            id="test-agent",
            name="Test Agent",
            system_prompt="You are helpful",
            default_llm=self.llm,
            is_active=True
        )
        self.conversation = Conversation.objects.create(
            model_id=self.llm.id,
            primary_agent=self.agent,
            primary_llm=self.llm
        )
        self.orchestrator = ChatOrchestrator()
    
    @patch('apps.core.orchestrator.get_protegrity_service')
    @patch('apps.core.orchestrator.get_provider')
    def test_input_protection_runs_on_user_message(self, mock_get_provider, mock_get_protegrity):
        """Test that input protection runs and saves to user message."""
        # Setup mocks
        mock_protegrity = MagicMock()
        mock_protegrity.process_full_pipeline.return_value = {
            "original_text": "My SSN is 123-45-6789",
            "processed_text": "My SSN is [SSN]",
            "should_block": False,
            "guardrails": {"outcome": "accepted", "risk_score": 0.1},
            "discovery": {"SSN": [{"entity_text": "123-45-6789", "score": 0.99}]},
            "redaction": {"success": True, "method": "redact"},
            "mode": "redact"
        }
        # Return plain dict (not MagicMock) for process_llm_response to avoid .copy() issues
        mock_protegrity.process_llm_response.return_value = {
            "original_response": "I've noted your SSN.",
            "processed_response": "I've noted your SSN.",
            "should_filter": False,
            "guardrails": {"outcome": "accepted"},
            "discovery": {},
            "redaction": {}
        }
        mock_get_protegrity.return_value = mock_protegrity
        
        mock_provider = MagicMock()
        mock_provider.send_message.return_value = MagicMock(
            status="completed",
            content="I've noted your SSN.",
            tool_calls=[],
            pending_message_id=None
        )
        mock_get_provider.return_value = mock_provider
        
        # Create user message
        user_msg = Message.objects.create(
            conversation=self.conversation,
            role="user",
            content="My SSN is 123-45-6789"
        )
        
        # Execute
        result = self.orchestrator.handle_user_message(self.conversation, user_msg)
        
        # Verify input protection was called
        mock_protegrity.process_full_pipeline.assert_called_once_with(
            "My SSN is 123-45-6789",
            mode="redact"
        )
        
        # Verify user message has protegrity_data saved
        user_msg.refresh_from_db()
        self.assertIsNotNone(user_msg.protegrity_data)
        self.assertIn("input_processing", user_msg.protegrity_data)
        input_data = user_msg.protegrity_data["input_processing"]
        self.assertEqual(input_data["original_text"], "My SSN is 123-45-6789")
        self.assertEqual(input_data["processed_text"], "My SSN is [SSN]")
        self.assertFalse(input_data["should_block"])
    
    @patch('apps.core.orchestrator.get_protegrity_service')
    @patch('apps.core.orchestrator.get_provider')
    def test_protected_text_sent_to_llm(self, mock_get_provider, mock_get_protegrity):
        """Test that protected text (not original) is sent to LLM."""
        # Setup mocks
        mock_protegrity = MagicMock()
        mock_protegrity.process_full_pipeline.return_value = {
            "original_text": "Call me at 555-1234",
            "processed_text": "Call me at [PHONE]",
            "should_block": False,
            "guardrails": {"outcome": "accepted"},
            "discovery": {},
            "redaction": {},
            "mode": "redact"
        }
        # Return plain dict for process_llm_response
        mock_protegrity.process_llm_response.return_value = {
            "original_response": "Noted",
            "processed_response": "Noted",
            "should_filter": False,
            "guardrails": {"outcome": "accepted"},
            "discovery": {},
            "redaction": {}
        }
        mock_get_protegrity.return_value = mock_protegrity
        
        mock_provider = MagicMock()
        mock_provider.send_message.return_value = MagicMock(
            status="completed",
            content="Noted",
            tool_calls=[]
        )
        mock_get_provider.return_value = mock_provider
        
        # Create user message
        user_msg = Message.objects.create(
            conversation=self.conversation,
            role="user",
            content="Call me at 555-1234"
        )
        
        # Execute
        self.orchestrator.handle_user_message(self.conversation, user_msg)
        
        # Verify provider received history with protected text
        call_args = mock_provider.send_message.call_args
        history = call_args[0][1]  # Second positional arg
        
        # Find the user message in history
        user_messages = [msg for msg in history if msg.role == "user"]
        self.assertEqual(len(user_messages), 1)
        self.assertEqual(user_messages[0].content, "Call me at [PHONE]")
    
    @patch('apps.core.orchestrator.get_protegrity_service')
    def test_blocked_input_returns_early(self, mock_get_protegrity):
        """Test that blocked input doesn't call LLM and returns blocked message."""
        # Setup mock to return blocked
        mock_protegrity = MagicMock()
        mock_protegrity.process_full_pipeline.return_value = {
            "original_text": "Malicious prompt",
            "processed_text": None,
            "should_block": True,
            "guardrails": {"outcome": "rejected", "risk_score": 0.95},
            "discovery": {},
            "redaction": {},
            "mode": "redact"
        }
        mock_get_protegrity.return_value = mock_protegrity
        
        # Create user message
        user_msg = Message.objects.create(
            conversation=self.conversation,
            role="user",
            content="Malicious prompt"
        )
        
        # Execute
        result = self.orchestrator.handle_user_message(self.conversation, user_msg)
        
        # Verify blocked status
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["assistant_message"].blocked)
        self.assertIn("blocked", result["assistant_message"].content.lower())
        
        # Verify user message has blocked flag in protegrity_data
        user_msg.refresh_from_db()
        self.assertIn("input_processing", user_msg.protegrity_data)
        self.assertTrue(user_msg.protegrity_data["input_processing"]["should_block"])


class TestProtegrityOutputProtection(TestCase):
    """Test output protection flow in orchestrator."""
    
    def setUp(self):
        """Create test fixtures."""
        self.llm = LLMProvider.objects.create(
            id="test-llm",
            name="Test LLM",
            provider_type="dummy"
        )
        self.agent = Agent.objects.create(
            id="test-agent",
            name="Test Agent",
            system_prompt="You are helpful",
            default_llm=self.llm,
            is_active=True
        )
        self.conversation = Conversation.objects.create(
            model_id=self.llm.id,
            primary_agent=self.agent,
            primary_llm=self.llm
        )
        self.orchestrator = ChatOrchestrator()
    
    @patch('apps.core.orchestrator.get_protegrity_service')
    @patch('apps.core.orchestrator.get_provider')
    def test_output_protection_runs_on_llm_response(self, mock_get_provider, mock_get_protegrity):
        """Test that output protection runs on LLM response."""
        # Setup mocks
        mock_protegrity = MagicMock()
        # Input protection (accepts)
        mock_protegrity.process_full_pipeline.return_value = {
            "original_text": "Hello",
            "processed_text": "Hello",
            "should_block": False,
            "guardrails": {"outcome": "accepted"},
            "discovery": {},
            "redaction": {},
            "mode": "redact"
        }
        # Output protection
        mock_protegrity.process_llm_response.return_value = {
            "original_response": "Your account number is 9876543210",
            "processed_response": "Your account number is [ACCOUNT]",
            "should_filter": False,
            "guardrails": {"outcome": "accepted", "risk_score": 0.2},
            "discovery": {"ACCOUNT": [{"entity_text": "9876543210"}]},
            "redaction": {"success": True}
        }
        mock_get_protegrity.return_value = mock_protegrity
        
        mock_provider = MagicMock()
        mock_provider.send_message.return_value = MagicMock(
            status="completed",
            content="Your account number is 9876543210",
            tool_calls=[]
        )
        mock_get_provider.return_value = mock_provider
        
        # Create user message
        user_msg = Message.objects.create(
            conversation=self.conversation,
            role="user",
            content="Hello"
        )
        
        # Execute
        result = self.orchestrator.handle_user_message(self.conversation, user_msg)
        
        # Verify output protection was called
        mock_protegrity.process_llm_response.assert_called_once_with(
            "Your account number is 9876543210"
        )
        
        # Verify assistant message has safe content
        assistant_msg = result["assistant_message"]
        self.assertEqual(assistant_msg.content, "Your account number is [ACCOUNT]")
        
        # Verify protegrity_data saved
        self.assertIsNotNone(assistant_msg.protegrity_data)
        self.assertIn("output_processing", assistant_msg.protegrity_data)
        output_data = assistant_msg.protegrity_data["output_processing"]
        self.assertEqual(
            output_data["original_response"],
            "Your account number is 9876543210"
        )
        self.assertEqual(
            output_data["processed_response"],
            "Your account number is [ACCOUNT]"
        )
    
    @patch('apps.core.orchestrator.get_protegrity_service')
    @patch('apps.core.orchestrator.get_provider')
    def test_blocked_output_sets_blocked_flag(self, mock_get_provider, mock_get_protegrity):
        """Test that blocked output sets blocked=True and replaces content."""
        # Setup mocks
        mock_protegrity = MagicMock()
        # Input protection (accepts)
        mock_protegrity.process_full_pipeline.return_value = {
            "original_text": "Tell me a secret",
            "processed_text": "Tell me a secret",
            "should_block": False,
            "guardrails": {"outcome": "accepted"},
            "discovery": {},
            "redaction": {},
            "mode": "redact"
        }
        # Output protection (blocks)
        mock_protegrity.process_llm_response.return_value = {
            "original_response": "Here's confidential data...",
            "processed_response": "Here's confidential data...",
            "should_filter": True,  # BLOCKED
            "guardrails": {"outcome": "rejected", "risk_score": 0.99},
            "discovery": {},
            "redaction": {}
        }
        mock_get_protegrity.return_value = mock_protegrity
        
        mock_provider = MagicMock()
        mock_provider.send_message.return_value = MagicMock(
            status="completed",
            content="Here's confidential data...",
            tool_calls=[]
        )
        mock_get_provider.return_value = mock_provider
        
        # Create user message
        user_msg = Message.objects.create(
            conversation=self.conversation,
            role="user",
            content="Tell me a secret"
        )
        
        # Execute
        result = self.orchestrator.handle_user_message(self.conversation, user_msg)
        
        # Verify assistant message is blocked
        assistant_msg = result["assistant_message"]
        self.assertTrue(assistant_msg.blocked)
        self.assertEqual(assistant_msg.content, "This response was blocked due to policy violations.")
        
        # Verify protegrity_data shows should_filter=True
        self.assertIn("output_processing", assistant_msg.protegrity_data)
        self.assertTrue(assistant_msg.protegrity_data["output_processing"]["should_filter"])


class TestProtegrityInPollFlow(TestCase):
    """Test output protection in async poll flow."""
    
    def setUp(self):
        """Create test fixtures."""
        self.llm = LLMProvider.objects.create(
            id="test-llm",
            name="Test LLM",
            provider_type="dummy"
        )
        self.agent = Agent.objects.create(
            id="test-agent",
            name="Test Agent",
            system_prompt="You are helpful",
            default_llm=self.llm,
            is_active=True
        )
        self.conversation = Conversation.objects.create(
            model_id=self.llm.id,
            primary_agent=self.agent,
            primary_llm=self.llm
        )
        self.orchestrator = ChatOrchestrator()
    
    @patch('apps.core.orchestrator.get_protegrity_service')
    @patch('apps.core.orchestrator.get_provider')
    def test_poll_applies_output_protection(self, mock_get_provider, mock_get_protegrity):
        """Test that poll() applies output protection to async LLM responses."""
        # Setup mocks
        mock_protegrity = MagicMock()
        mock_protegrity.process_llm_response.return_value = {
            "original_response": "Raw LLM output with PII",
            "processed_response": "Raw LLM output with [PII]",
            "should_filter": False,
            "guardrails": {"outcome": "accepted"},
            "discovery": {"EMAIL": []},
            "redaction": {"success": True}
        }
        mock_get_protegrity.return_value = mock_protegrity
        
        mock_provider = MagicMock()
        mock_provider.poll_response.return_value = MagicMock(
            status="completed",
            content="Raw LLM output with PII",
            tool_calls=[]
        )
        mock_get_provider.return_value = mock_provider
        
        # Execute poll
        result = self.orchestrator.poll(self.conversation)
        
        # Verify output protection was called
        mock_protegrity.process_llm_response.assert_called_once_with(
            "Raw LLM output with PII"
        )
        
        # Verify safe content used
        self.assertEqual(result["status"], "completed")
        assistant_msg = result["assistant_message"]
        self.assertEqual(assistant_msg.content, "Raw LLM output with [PII]")
        self.assertIsNotNone(assistant_msg.protegrity_data)
    
    @patch('apps.core.orchestrator.get_protegrity_service')
    @patch('apps.core.orchestrator.get_provider')
    def test_poll_handles_blocked_output(self, mock_get_provider, mock_get_protegrity):
        """Test that poll() handles blocked output correctly."""
        # Setup mocks
        mock_protegrity = MagicMock()
        mock_protegrity.process_llm_response.return_value = {
            "original_response": "Harmful content",
            "processed_response": "Harmful content",
            "should_filter": True,  # BLOCKED
            "guardrails": {"outcome": "rejected"},
            "discovery": {},
            "redaction": {}
        }
        mock_get_protegrity.return_value = mock_protegrity
        
        mock_provider = MagicMock()
        mock_provider.poll_response.return_value = MagicMock(
            status="completed",
            content="Harmful content",
            tool_calls=[]
        )
        mock_get_provider.return_value = mock_provider
        
        # Execute poll
        result = self.orchestrator.poll(self.conversation)
        
        # Verify blocked
        assistant_msg = result["assistant_message"]
        self.assertTrue(assistant_msg.blocked)
        self.assertEqual(assistant_msg.content, "This response was blocked due to policy violations.")


class TestProtegrityWithToolCalls(TestCase):
    """Test that Protegrity works alongside tool execution."""
    
    def setUp(self):
        """Create test fixtures."""
        self.llm = LLMProvider.objects.create(
            id="test-llm",
            name="Test LLM",
            provider_type="dummy"
        )
        self.tool = Tool.objects.create(
            id="protegrity-redact",
            name="Protegrity Redact",
            description="Redacts PII"
        )
        self.agent = Agent.objects.create(
            id="test-agent",
            name="Test Agent",
            system_prompt="You are helpful",
            default_llm=self.llm,
            is_active=True
        )
        self.agent.tools.add(self.tool)
        
        self.conversation = Conversation.objects.create(
            model_id=self.llm.id,
            primary_agent=self.agent,
            primary_llm=self.llm
        )
        self.orchestrator = ChatOrchestrator()
    
    @patch('apps.core.orchestrator.execute_tool_calls')
    @patch('apps.core.orchestrator.get_protegrity_service')
    @patch('apps.core.orchestrator.get_provider')
    def test_protegrity_data_includes_tool_results(self, mock_get_provider, mock_get_protegrity, mock_execute_tools):
        """Test that protegrity_data includes both protection data and tool results."""
        # Setup mocks
        mock_protegrity = MagicMock()
        mock_protegrity.process_full_pipeline.return_value = {
            "original_text": "Test",
            "processed_text": "Test",
            "should_block": False,
            "guardrails": {"outcome": "accepted"},
            "discovery": {},
            "redaction": {},
            "mode": "redact"
        }
        mock_protegrity.process_llm_response.return_value = {
            "original_response": "Done",
            "processed_response": "Done",
            "should_filter": False,
            "guardrails": {"outcome": "accepted"},
            "discovery": {},
            "redaction": {}
        }
        mock_get_protegrity.return_value = mock_protegrity
        
        mock_execute_tools.return_value = [
            {"tool_name": "protegrity-redact", "result": "Success"}
        ]
        
        mock_provider = MagicMock()
        mock_provider.send_message.return_value = MagicMock(
            status="completed",
            content="Done",
            tool_calls=[{"tool_name": "protegrity-redact", "arguments": {}}]
        )
        mock_get_provider.return_value = mock_provider
        
        # Create user message
        user_msg = Message.objects.create(
            conversation=self.conversation,
            role="user",
            content="Test"
        )
        
        # Execute
        result = self.orchestrator.handle_user_message(self.conversation, user_msg)
        
        # Verify protegrity_data has both protection and tool results
        assistant_msg = result["assistant_message"]
        self.assertIn("tool_results", assistant_msg.protegrity_data)
        self.assertIn("output_processing", assistant_msg.protegrity_data)
        self.assertIn("original_response", assistant_msg.protegrity_data["output_processing"])
        self.assertEqual(len(assistant_msg.protegrity_data["tool_results"]), 1)
