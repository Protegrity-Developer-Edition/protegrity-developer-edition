"""
Comprehensive tests for tool routing and execution system.

Tests cover:
- Tool call validation and permission checks
- Tool execution for all Protegrity tool types
- Error handling for unauthorized/disabled tools
- Multiple tool call execution
- Edge cases and error scenarios
"""

import pytest
from unittest.mock import patch, Mock
from apps.core.tool_router import execute_tool_calls, _execute_protegrity_tool
from apps.core.models import Agent, Tool, LLMProvider
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def llm_provider(db):
    """Create a test LLM provider."""
    return LLMProvider.objects.create(
        id='test-llm',
        name='Test LLM',
        provider_type='dummy',
        is_active=True
    )


@pytest.fixture
def agent_with_tools(db, llm_provider):
    """Create an agent with Protegrity tools assigned."""
    agent = Agent.objects.create(
        id='test-agent',
        name='Test Agent',
        description='Agent for testing',
        default_llm=llm_provider,
        is_active=True
    )
    
    # Create and assign tools
    redact_tool = Tool.objects.create(
        id='protegrity-redact',
        name='Redact PII',
        description='Redact sensitive data',
        tool_type='protegrity',
        is_active=True
    )
    
    classify_tool = Tool.objects.create(
        id='protegrity-classify',
        name='Classify Data',
        description='Discover PII entities',
        tool_type='protegrity',
        is_active=True
    )
    
    guardrails_tool = Tool.objects.create(
        id='protegrity-guardrails',
        name='Check Guardrails',
        description='Validate input safety',
        tool_type='protegrity',
        is_active=True
    )
    
    agent.tools.add(redact_tool, classify_tool, guardrails_tool)
    return agent


@pytest.fixture
def disabled_tool(db):
    """Create a disabled tool."""
    return Tool.objects.create(
        id='disabled-tool',
        name='Disabled Tool',
        description='Inactive tool',
        tool_type='protegrity',
        is_active=False
    )


@pytest.fixture
def mock_protegrity_service():
    """Mock the Protegrity service."""
    with patch('apps.core.tool_router.get_protegrity_service') as mock:
        service = Mock()
        service.redact_data.return_value = ("Redacted text", {"success": True})
        service.discover_entities.return_value = {
            "EMAIL": [{"entity_text": "test@example.com"}]
        }
        service.check_guardrails.return_value = {
            "outcome": "accepted",
            "risk_score": 0.2
        }
        service.protect_data.return_value = ("Protected text", {"success": True})
        service.unprotect_data.return_value = ("Unprotected text", {"success": True})
        mock.return_value = service
        yield service


class TestToolCallExecution:
    """Test the main execute_tool_calls function."""
    
    def test_execute_empty_tool_calls(self, agent_with_tools):
        """Test that empty tool calls list returns empty results."""
        results = execute_tool_calls(agent_with_tools, [])
        
        assert results == []
    
    def test_execute_authorized_tool(self, agent_with_tools, mock_protegrity_service):
        """Test executing a tool that agent is authorized to use."""
        tool_calls = [
            {
                "tool_name": "protegrity-redact",
                "call_id": "call_1",
                "arguments": {"text": "Email: john@example.com"}
            }
        ]
        
        results = execute_tool_calls(agent_with_tools, tool_calls)
        
        assert len(results) == 1
        assert results[0]["call_id"] == "call_1"
        assert results[0]["tool_name"] == "protegrity-redact"
        assert "output" in results[0]
        assert "error" not in results[0]
        assert results[0]["output"]["redacted_text"] == "Redacted text"
    
    def test_execute_unauthorized_tool(self, agent_with_tools):
        """Test executing a tool that agent doesn't have access to."""
        tool_calls = [
            {
                "tool_name": "unauthorized-tool",
                "call_id": "call_1",
                "arguments": {}
            }
        ]
        
        results = execute_tool_calls(agent_with_tools, tool_calls)
        
        assert len(results) == 1
        assert results[0]["call_id"] == "call_1"
        assert "error" in results[0]
        assert "not found or not authorized" in results[0]["error"]
        assert "output" not in results[0]
    
    def test_execute_disabled_tool(self, agent_with_tools, disabled_tool):
        """Test executing a disabled tool."""
        # Add disabled tool to agent
        agent_with_tools.tools.add(disabled_tool)
        
        tool_calls = [
            {
                "tool_name": "disabled-tool",
                "call_id": "call_1",
                "arguments": {}
            }
        ]
        
        results = execute_tool_calls(agent_with_tools, tool_calls)
        
        assert len(results) == 1
        assert "error" in results[0]
        assert "currently disabled" in results[0]["error"]
    
    def test_execute_multiple_tool_calls(self, agent_with_tools, mock_protegrity_service):
        """Test executing multiple tool calls in one batch."""
        tool_calls = [
            {
                "tool_name": "protegrity-classify",
                "call_id": "call_1",
                "arguments": {"text": "Test text"}
            },
            {
                "tool_name": "protegrity-redact",
                "call_id": "call_2",
                "arguments": {"text": "Another test"}
            }
        ]
        
        results = execute_tool_calls(agent_with_tools, tool_calls)
        
        assert len(results) == 2
        assert results[0]["call_id"] == "call_1"
        assert results[1]["call_id"] == "call_2"
        assert "output" in results[0]
        assert "output" in results[1]
    
    def test_execute_with_no_agent(self):
        """Test executing tools with no agent (should fail)."""
        tool_calls = [
            {
                "tool_name": "protegrity-redact",
                "call_id": "call_1",
                "arguments": {"text": "Test"}
            }
        ]
        
        results = execute_tool_calls(None, tool_calls)
        
        assert len(results) == 1
        assert "error" in results[0]
        assert "not authorized" in results[0]["error"]
    
    def test_execute_tool_with_exception(self, agent_with_tools, mock_protegrity_service):
        """Test handling of exceptions during tool execution."""
        mock_protegrity_service.redact_data.side_effect = Exception("Tool execution failed")
        
        tool_calls = [
            {
                "tool_name": "protegrity-redact",
                "call_id": "call_1",
                "arguments": {"text": "Test"}
            }
        ]
        
        results = execute_tool_calls(agent_with_tools, tool_calls)
        
        assert len(results) == 1
        assert "error" in results[0]
        assert "Tool execution failed" in results[0]["error"]


class TestProtegrityToolExecution:
    """Test the _execute_protegrity_tool function for each tool type."""
    
    def test_execute_redact_tool(self, db, mock_protegrity_service):
        """Test protegrity-redact tool execution."""
        tool = Tool.objects.create(
            id='protegrity-redact',
            name='Redact',
            tool_type='protegrity',
            is_active=True
        )
        
        args = {"text": "Email: john@example.com"}
        result = _execute_protegrity_tool(tool, args)
        
        assert result["redacted_text"] == "Redacted text"
        assert result["original_length"] > 0
        assert result["metadata"]["success"] is True
        mock_protegrity_service.redact_data.assert_called_once_with("Email: john@example.com")
    
    def test_execute_classify_tool(self, db, mock_protegrity_service):
        """Test protegrity-classify tool execution."""
        tool = Tool.objects.create(
            id='protegrity-classify',
            name='Classify',
            tool_type='protegrity',
            is_active=True
        )
        
        args = {"text": "Email: test@example.com"}
        result = _execute_protegrity_tool(tool, args)
        
        assert "entities" in result
        assert "EMAIL" in result["entities"]
        assert result["total_entities"] == 1
        assert result["entity_types"] == ["EMAIL"]
        mock_protegrity_service.discover_entities.assert_called_once()
    
    def test_execute_guardrails_tool(self, db, mock_protegrity_service):
        """Test protegrity-guardrails tool execution."""
        tool = Tool.objects.create(
            id='protegrity-guardrails',
            name='Guardrails',
            tool_type='protegrity',
            is_active=True
        )
        
        args = {"text": "Safe prompt"}
        result = _execute_protegrity_tool(tool, args)
        
        assert result["outcome"] == "accepted"
        assert result["risk_score"] == 0.2
        mock_protegrity_service.check_guardrails.assert_called_once()
    
    def test_execute_protect_tool(self, db, mock_protegrity_service):
        """Test protegrity-protect tool execution."""
        tool = Tool.objects.create(
            id='protegrity-protect',
            name='Protect',
            tool_type='protegrity',
            is_active=True
        )
        
        args = {"text": "SSN: 123-45-6789"}
        result = _execute_protegrity_tool(tool, args)
        
        assert result["protected_text"] == "Protected text"
        assert result["success"] is True
        mock_protegrity_service.protect_data.assert_called_once()
    
    def test_execute_unprotect_tool(self, db, mock_protegrity_service):
        """Test protegrity-unprotect tool execution."""
        tool = Tool.objects.create(
            id='protegrity-unprotect',
            name='Unprotect',
            tool_type='protegrity',
            is_active=True
        )
        
        args = {"text": "Protected data"}
        result = _execute_protegrity_tool(tool, args)
        
        assert result["unprotected_text"] == "Unprotected text"
        assert result["success"] is True
        mock_protegrity_service.unprotect_data.assert_called_once()
    
    def test_execute_unknown_protegrity_tool(self, db):
        """Test that unknown Protegrity tool raises NotImplementedError."""
        tool = Tool.objects.create(
            id='protegrity-unknown',
            name='Unknown Tool',
            tool_type='protegrity',
            is_active=True
        )
        
        args = {"text": "Test"}
        
        with pytest.raises(NotImplementedError) as exc_info:
            _execute_protegrity_tool(tool, args)
        
        assert "No handler defined" in str(exc_info.value)
        assert "protegrity-unknown" in str(exc_info.value)
    
    def test_execute_tool_with_empty_text(self, db, mock_protegrity_service):
        """Test tool execution with empty text argument."""
        tool = Tool.objects.create(
            id='protegrity-redact',
            name='Redact',
            tool_type='protegrity',
            is_active=True
        )
        
        args = {}  # No text provided
        result = _execute_protegrity_tool(tool, args)
        
        # Should still execute with empty string
        assert "redacted_text" in result
        mock_protegrity_service.redact_data.assert_called_once_with("")
    
    def test_execute_tool_with_null_arguments(self, agent_with_tools, mock_protegrity_service):
        """Test tool execution when arguments is None."""
        tool_calls = [
            {
                "tool_name": "protegrity-redact",
                "call_id": "call_1",
                "arguments": None  # None instead of dict
            }
        ]
        
        results = execute_tool_calls(agent_with_tools, tool_calls)
        
        # Should handle gracefully by treating as empty dict
        assert len(results) == 1
        assert "output" in results[0]


class TestToolCallEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_execute_tool_missing_call_id(self, agent_with_tools, mock_protegrity_service):
        """Test tool call without call_id uses default."""
        tool_calls = [
            {
                "tool_name": "protegrity-redact",
                # No call_id provided
                "arguments": {"text": "Test"}
            }
        ]
        
        results = execute_tool_calls(agent_with_tools, tool_calls)
        
        assert len(results) == 1
        assert results[0]["call_id"] == "unknown"
    
    def test_execute_mixed_success_and_failure(self, agent_with_tools, mock_protegrity_service):
        """Test batch with both successful and failed tool calls."""
        tool_calls = [
            {
                "tool_name": "protegrity-redact",
                "call_id": "success",
                "arguments": {"text": "Test"}
            },
            {
                "tool_name": "unauthorized-tool",
                "call_id": "failure",
                "arguments": {}
            },
            {
                "tool_name": "protegrity-classify",
                "call_id": "success2",
                "arguments": {"text": "Another test"}
            }
        ]
        
        results = execute_tool_calls(agent_with_tools, tool_calls)
        
        assert len(results) == 3
        assert "output" in results[0]
        assert "error" in results[1]
        assert "output" in results[2]
