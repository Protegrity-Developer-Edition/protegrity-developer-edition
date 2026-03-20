"""
LLM Provider Abstraction Layer

This module provides a unified interface for interacting with different LLM providers.
Each provider implements the BaseLLMProvider interface and returns standardized results.

Architecture:
- BaseLLMProvider: Abstract base class defining the provider interface
- ProviderResult: Standard result object for all provider calls
- DummyProvider: Local development provider (no API keys needed)
- get_provider(): Factory function to instantiate the correct provider

Future providers (when credentials available):
- FinAIProvider: Intercom Fin AI (async, requires polling)
- BedrockClaudeProvider: AWS Bedrock Claude (sync)
- OpenAIProvider: OpenAI GPT models (sync/streaming)
"""

from abc import ABC, abstractmethod
from types import SimpleNamespace
import logging

logger = logging.getLogger(__name__)


class ProviderResult:
    """
    Standard result object for provider calls.
    
    Attributes:
        status: "completed" | "pending"
        content: Assistant response text (when completed)
        pending_message_id: Message ID for async providers (optional)
        tool_calls: List of tool call requests from the LLM (optional)
                   Each tool call is a dict with:
                   {
                       "tool_name": "protegrity-redact",  # matches Tool.id
                       "arguments": {...},                # JSON-serializable args
                       "call_id": "tool_call_1",          # unique per call
                   }
    """
    
    def __init__(self, status, content=None, pending_message_id=None, tool_calls=None):
        self.status = status
        self.content = content
        self.pending_message_id = pending_message_id
        self.tool_calls = tool_calls or []
    
    def __repr__(self):
        tools_info = f", {len(self.tool_calls)} tool_calls" if self.tool_calls else ""
        return f"ProviderResult(status={self.status}, content={self.content[:50] if self.content else None}...{tools_info})"


class BaseLLMProvider(ABC):
    """
    Base interface for all LLM providers.
    
    All providers must implement send_message() and poll_response().
    Synchronous providers return completed results immediately.
    Asynchronous providers return pending status and require polling.
    """
    
    def __init__(self, llm_provider):
        """
        Initialize provider with LLMProvider model instance.
        
        Args:
            llm_provider: LLMProvider instance or namespace with id, name, provider_type
        """
        self.llm_provider = llm_provider
    
    @abstractmethod
    def send_message(self, conversation, messages, agent=None):
        """
        Send a message to the LLM provider (synchronous or asynchronous).
        
        Args:
            conversation: Conversation model instance
            messages: QuerySet or list of Message instances (full history)
            agent: Agent model instance for this turn (may be None)
        
        Returns:
            ProviderResult with status "completed" (sync) or "pending" (async)
        """
        raise NotImplementedError
    
    @abstractmethod
    def poll_response(self, conversation):
        """
        Poll for async LLM response (for providers that require polling).
        
        Synchronous providers should return None.
        
        Args:
            conversation: Conversation model instance
        
        Returns:
            ProviderResult with status="completed" when ready,
            ProviderResult with status="pending" if still processing,
            or None for synchronous providers
        """
        raise NotImplementedError


class DummyProvider(BaseLLMProvider):
    """
    Local fake provider for development and testing.
    
    Features:
    - No external API calls
    - No credentials required
    - Deterministic responses
    - Synchronous (immediate response)
    - Useful for frontend development and testing
    
    The dummy provider echoes back information about the agent, model,
    and a snippet of the user's message.
    """
    
    def send_message(self, conversation, messages, agent=None):
        """
        Generate a fake response based on the last user message.
        
        Simulates tool calling when sensitive data patterns are detected:
        - "ssn" or "social security" -> triggers protegrity-redact
        - "classify" or "find pii" -> triggers protegrity-classify
        - "guardrail" or "check policy" -> triggers protegrity-guardrails
        
        Args:
            conversation: Conversation instance
            messages: Message history
            agent: Agent instance (optional)
        
        Returns:
            ProviderResult with status="completed", dummy content, and optional tool_calls
        """
        # Find the last user message
        message_list = list(messages)
        last_user = next((m for m in reversed(message_list) if m.role == "user"), None)
        user_text = last_user.content if last_user else ""
        user_text_lower = user_text.lower()
        
        # Get agent and LLM names
        agent_name = agent.name if agent else "Default Agent"
        llm_name = getattr(self.llm_provider, "name", "Dummy LLM")
        
        # Detect if tool calls should be simulated
        tool_calls = []
        
        # Check for sensitive data keywords
        if "ssn" in user_text_lower or "social security" in user_text_lower:
            tool_calls.append({
                "tool_name": "protegrity-redact",
                "arguments": {
                    "text": user_text,
                },
                "call_id": "tool_call_1",
            })
        
        # Check for classification keywords
        if "classify" in user_text_lower or "find pii" in user_text_lower or "discover" in user_text_lower:
            tool_calls.append({
                "tool_name": "protegrity-classify",
                "arguments": {
                    "text": user_text,
                },
                "call_id": f"tool_call_{len(tool_calls) + 1}",
            })
        
        # Check for guardrail keywords
        if "guardrail" in user_text_lower or "check policy" in user_text_lower or "validate" in user_text_lower:
            tool_calls.append({
                "tool_name": "protegrity-guardrails",
                "arguments": {
                    "text": user_text,
                },
                "call_id": f"tool_call_{len(tool_calls) + 1}",
            })
        
        # Generate reply based on whether tools were triggered
        if tool_calls:
            reply_text = (
                f"🤖 **Dummy Response** from **{agent_name}** using **{llm_name}**\n\n"
                f"I detected sensitive data or a request that requires Protegrity tools. "
                f"I will use {len(tool_calls)} tool(s) to process this safely.\n\n"
                f"Tools requested: {', '.join([tc['tool_name'] for tc in tool_calls])}"
            )
        else:
            reply_text = (
                f"🤖 **Dummy Response** from **{agent_name}** using **{llm_name}**\n\n"
                f"You said: \"{user_text[:200]}{'...' if len(user_text) > 200 else ''}\"\n\n"
                f"This is a simulated response. Configure real LLM credentials to get actual AI responses.\n\n"
                f"Conversation ID: {conversation.id}\n"
                f"Message count: {len(message_list)}"
            )
        
        # Return completed result (synchronous)
        return ProviderResult(
            status="completed",
            content=reply_text,
            tool_calls=tool_calls,
        )
    
    def poll_response(self, conversation):
        """
        Dummy provider is synchronous, nothing to poll.
        
        Returns:
            None (synchronous provider)
        """
        return None


def get_provider(llm_provider):
    """
    Factory function to instantiate the correct provider.
    
    Given an LLMProvider instance (or None), returns a concrete provider object.
    Currently defaults to DummyProvider for all providers until real implementations
    are added.
    
    Args:
        llm_provider: LLMProvider model instance or None
    
    Returns:
        BaseLLMProvider subclass instance
    
    Example:
        >>> provider = get_provider(conversation.primary_llm)
        >>> result = provider.send_message(conversation, messages, agent)
    
    Future providers:
        - provider_type == "intercom" → FinAIProvider (async)
        - provider_type == "bedrock" → BedrockClaudeProvider (sync)
        - provider_type == "openai" → OpenAIProvider (sync/streaming)
        - provider_type == "anthropic" → AnthropicProvider (sync/streaming)
    """
    # Handle None case: create a dummy LLM namespace
    if llm_provider is None:
        dummy = SimpleNamespace(
            id="dummy",
            name="Dummy LLM",
            provider_type="custom",
        )
        return DummyProvider(dummy)
    
    # Get provider type from LLMProvider model
    provider_type = llm_provider.provider_type
    
    # Azure OpenAI provider (active)
    if provider_type == "azure":
        try:
            from .providers_azure import AzureOpenAIProvider
            return AzureOpenAIProvider(llm_provider)
        except Exception as exc:
            logger.warning("Falling back to DummyProvider for azure due to initialization error: %s", exc)
            return DummyProvider(llm_provider)
    
    # Extend provider mappings here when adding additional providers.
    # 
    # if provider_type == "intercom":
    #     from .providers_fin import FinAIProvider
    #     return FinAIProvider(llm_provider)
    # 
    if provider_type == "bedrock":
        try:
            from .providers_bedrock import BedrockClaudeProvider
            return BedrockClaudeProvider(llm_provider)
        except Exception as exc:
            logger.warning("Falling back to DummyProvider for bedrock due to initialization error: %s", exc)
            return DummyProvider(llm_provider)
    # 
    if provider_type == "openai":
        try:
            from .providers_openai import OpenAIProvider
            return OpenAIProvider(llm_provider)
        except Exception as exc:
            logger.warning("Falling back to DummyProvider for openai due to initialization error: %s", exc)
            return DummyProvider(llm_provider)

    if provider_type == "anthropic":
        try:
            from .providers_anthropic import AnthropicProvider
            return AnthropicProvider(llm_provider)
        except Exception as exc:
            logger.warning("Falling back to DummyProvider for anthropic due to initialization error: %s", exc)
            return DummyProvider(llm_provider)
    
    # Default to DummyProvider for all providers (development mode)
    return DummyProvider(llm_provider)
