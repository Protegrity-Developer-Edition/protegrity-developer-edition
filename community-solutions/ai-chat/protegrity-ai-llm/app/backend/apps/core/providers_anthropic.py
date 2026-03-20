"""
Anthropic Provider Implementation

Integrates Anthropic Messages API with the app's LLM abstraction.

Environment Variables:
- ANTHROPIC_API_KEY (required)
- ANTHROPIC_MODEL (optional fallback model when DB model_identifier is empty)
"""

import logging
import os

import requests

from .providers import BaseLLMProvider, ProviderResult

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider for Claude models."""

    def __init__(self, llm_provider):
        super().__init__(llm_provider)

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"

        model_from_env = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        self.model_name = llm_provider.model_identifier or model_from_env

        config = llm_provider.configuration or {}
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", llm_provider.max_tokens or 2048)

        logger.info("Initialized Anthropic provider: %s (%s)", llm_provider.name, self.model_name)

    def _build_payload_messages(self, messages):
        payload_messages = []
        for msg in messages:
            if msg.role in ["user", "assistant"]:
                payload_messages.append({"role": msg.role, "content": msg.content})
        return payload_messages

    def _build_tools(self, agent=None):
        if not agent:
            return None

        tools = agent.tools.filter(is_active=True)
        if not tools.exists():
            return None

        tool_defs = []
        for tool in tools:
            schema = tool.function_schema or {}
            input_schema = schema.get("parameters", {"type": "object", "properties": {}})
            tool_defs.append(
                {
                    "name": tool.id,
                    "description": schema.get("description", tool.description or tool.name),
                    "input_schema": input_schema,
                }
            )

        return tool_defs

    def _parse_response(self, data):
        content_blocks = data.get("content", [])
        text_parts = []
        tool_calls = []

        for block in content_blocks:
            block_type = block.get("type")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_calls.append(
                    {
                        "tool_name": block.get("name", ""),
                        "arguments": block.get("input", {}) or {},
                        "call_id": block.get("id", "unknown"),
                    }
                )

        return "\n".join([part for part in text_parts if part]).strip(), tool_calls

    def send_message(self, conversation, messages, agent=None):
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": self._build_payload_messages(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if agent and agent.system_prompt:
            payload["system"] = agent.system_prompt

        tools = self._build_tools(agent)
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            content, tool_calls = self._parse_response(data)
            return ProviderResult(status="completed", content=content, tool_calls=tool_calls)

        except requests.Timeout:
            logger.error("Anthropic request timeout")
            return ProviderResult(status="completed", content="⚠️ Request timed out. Please try again.")
        except requests.HTTPError as exc:
            logger.error("Anthropic API HTTP error: %s", exc)
            return ProviderResult(status="completed", content=f"⚠️ API error: {str(exc)}")
        except Exception as exc:
            logger.exception("Unexpected error in Anthropic provider: %s", exc)
            return ProviderResult(status="completed", content=f"⚠️ Unexpected error: {str(exc)}")

    def poll_response(self, conversation):
        return None
