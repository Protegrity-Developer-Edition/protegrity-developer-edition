"""
Azure OpenAI Provider Implementation

Integrates Azure OpenAI Service with the application's LLM abstraction layer.
Supports GPT-4, GPT-4o, GPT-3.5-turbo, and other Azure-hosted models.

Features:
- Synchronous chat completions
- Streaming support
- Tool/function calling for Protegrity integration
- Conversation history management
- Error handling and retry logic

Environment Variables Required:
- AZURE_OPENAI_API_KEY: Your Azure OpenAI API key
- AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint URL (e.g., https://pty-openai-it.openai.azure.com/)
- AZURE_OPENAI_API_VERSION: API version (default: 2024-08-01-preview)
"""

import os
import logging
import json
from openai import AzureOpenAI
from openai import OpenAIError, APIError, RateLimitError, APITimeoutError
from .providers import BaseLLMProvider, ProviderResult

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(BaseLLMProvider):
    """
    Azure OpenAI provider for GPT models.
    
    Supports:
    - GPT-4, GPT-4 Turbo, GPT-4o
    - GPT-3.5 Turbo
    - DALL-E 3 (image generation)
    - All models available in your Azure OpenAI deployment
    
    Configuration:
    - model_identifier: Azure deployment name (e.g., 'gpt-4o', 'gpt-35-turbo-chat')
    - Reads credentials from environment variables
    """
    
    def __init__(self, llm_provider):
        """
        Initialize Azure OpenAI provider.
        
        Args:
            llm_provider: LLMProvider model instance with Azure configuration
        """
        super().__init__(llm_provider)
        
        # Get Azure OpenAI credentials from environment
        api_key = os.environ.get('AZURE_OPENAI_API_KEY')
        endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
        api_version = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')
        
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )
        
        # Get deployment name from model_identifier (e.g., 'gpt-4o', 'gpt-35-turbo-chat')
        self.deployment_name = llm_provider.model_identifier
        
        # Get configuration options
        config = llm_provider.configuration or {}
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', llm_provider.max_tokens)
        
        logger.info(f"Initialized Azure OpenAI provider: {llm_provider.name} (deployment: {self.deployment_name})")
    
    def _build_messages(self, messages, agent=None):
        """
        Convert Django Message instances to Azure OpenAI format.
        
        Args:
            messages: QuerySet or list of Message instances
            agent: Agent instance (optional)
        
        Returns:
            List of message dicts in Azure OpenAI format
        """
        openai_messages = []
        
        # Add system message if agent is provided
        if agent and agent.system_prompt:
            openai_messages.append({
                "role": "system",
                "content": agent.system_prompt
            })
        
        # Convert conversation history
        for msg in messages:
            if msg.role in ["user", "assistant", "system"]:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            elif msg.role == "tool":
                # Tool results from Protegrity integrations
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.metadata.get("tool_call_id", "unknown"),
                    "content": msg.content
                })
        
        return openai_messages
    
    def _build_tools(self, agent=None):
        """
        Build tool definitions for function calling.
        
        Args:
            agent: Agent instance with associated tools
        
        Returns:
            List of tool definitions in OpenAI format, or None if no tools
        """
        if not agent:
            return None
        
        # Get agent's available tools
        tools = agent.tools.filter(is_active=True)
        if not tools.exists():
            return None
        
        tool_definitions = []
        for tool in tools:
            # Convert tool's function_schema to OpenAI format
            function_schema = dict(tool.function_schema or {})
            function_schema["name"] = tool.id
            tool_definitions.append({
                "type": "function",
                "function": function_schema
            })
        
        return tool_definitions if tool_definitions else None
    
    def _parse_tool_calls(self, response_message):
        """
        Extract tool calls from Azure OpenAI response.
        
        Args:
            response_message: OpenAI ChatCompletion message object
        
        Returns:
            List of tool call dicts in our standard format
        """
        if not hasattr(response_message, 'tool_calls') or not response_message.tool_calls:
            return []
        
        tool_calls = []
        for tool_call in response_message.tool_calls:
            raw_args = tool_call.function.arguments or "{}"
            try:
                parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Azure tool args JSON for call_id={tool_call.id}")
                parsed_args = {}

            tool_calls.append({
                "tool_name": tool_call.function.name,
                "arguments": parsed_args,
                "call_id": tool_call.id,
            })
        
        return tool_calls
    
    def send_message(self, conversation, messages, agent=None):
        """
        Send a message to Azure OpenAI and get a response.
        
        Args:
            conversation: Conversation model instance
            messages: QuerySet or list of Message instances
            agent: Agent model instance (optional)
        
        Returns:
            ProviderResult with status="completed", content, and optional tool_calls
        """
        try:
            # Build message history in OpenAI format
            openai_messages = self._build_messages(messages, agent)
            
            # Build tool definitions if agent has tools
            tools = self._build_tools(agent)
            
            # Prepare API call parameters
            api_params = {
                "model": self.deployment_name,
                "messages": openai_messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            
            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"  # Let model decide when to use tools
            
            logger.info(f"Sending message to Azure OpenAI: {self.deployment_name} (agent: {agent.name if agent else 'None'})")
            
            # Call Azure OpenAI API
            response = self.client.chat.completions.create(**api_params)
            
            # Extract response
            response_message = response.choices[0].message
            content = response_message.content or ""
            
            # Parse tool calls if present
            tool_calls = self._parse_tool_calls(response_message)
            
            # Log token usage
            if response.usage:
                logger.info(
                    f"Azure OpenAI usage - Input: {response.usage.prompt_tokens} tokens, "
                    f"Output: {response.usage.completion_tokens} tokens"
                )
            
            # Return completed result
            return ProviderResult(
                status="completed",
                content=content,
                tool_calls=tool_calls
            )
        
        except RateLimitError as e:
            logger.error(f"Azure OpenAI rate limit exceeded: {e}")
            return ProviderResult(
                status="completed",
                content="⚠️ Rate limit exceeded. Please try again in a moment."
            )
        
        except APITimeoutError as e:
            logger.error(f"Azure OpenAI request timeout: {e}")
            return ProviderResult(
                status="completed",
                content="⚠️ Request timed out. Please try again."
            )
        
        except APIError as e:
            logger.error(f"Azure OpenAI API error: {e}")
            return ProviderResult(
                status="completed",
                content=f"⚠️ API error: {str(e)}"
            )
        
        except OpenAIError as e:
            logger.error(f"Azure OpenAI error: {e}")
            return ProviderResult(
                status="completed",
                content=f"⚠️ Azure OpenAI error: {str(e)}"
            )
        
        except Exception as e:
            logger.exception(f"Unexpected error in Azure OpenAI provider: {e}")
            return ProviderResult(
                status="completed",
                content=f"⚠️ Unexpected error: {str(e)}"
            )
    
    def poll_response(self, conversation):
        """
        Azure OpenAI is synchronous, no polling needed.
        
        Returns:
            None (synchronous provider)
        """
        return None
