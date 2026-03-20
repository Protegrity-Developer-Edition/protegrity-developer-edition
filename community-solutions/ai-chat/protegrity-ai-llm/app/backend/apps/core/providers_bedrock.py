"""
AWS Bedrock Provider Implementation

Integrates Bedrock Runtime with the app's LLM abstraction layer.

Environment Variables:
- AWS_ACCESS_KEY_ID (required)
- AWS_SECRET_ACCESS_KEY (required)
- AWS_DEFAULT_REGION (required)
- BEDROCK_MODEL_ID (optional fallback when DB model_identifier is empty)
"""

import json
import logging
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .providers import BaseLLMProvider, ProviderResult

logger = logging.getLogger(__name__)


class BedrockClaudeProvider(BaseLLMProvider):
    """Bedrock Runtime provider (Claude-first payload strategy)."""

    def __init__(self, llm_provider):
        super().__init__(llm_provider)

        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        region = os.environ.get("AWS_DEFAULT_REGION")

        if not access_key:
            raise ValueError("AWS_ACCESS_KEY_ID environment variable is required")
        if not secret_key:
            raise ValueError("AWS_SECRET_ACCESS_KEY environment variable is required")
        if not region:
            raise ValueError("AWS_DEFAULT_REGION environment variable is required")

        self.client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

        model_from_env = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        self.model_id = llm_provider.model_identifier or model_from_env

        config = llm_provider.configuration or {}
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", llm_provider.max_tokens or 2048)

        logger.info("Initialized Bedrock provider: %s (%s)", llm_provider.name, self.model_id)

    def _build_messages(self, messages):
        bedrock_messages = []
        for msg in messages:
            if msg.role in ["user", "assistant"]:
                bedrock_messages.append(
                    {
                        "role": msg.role,
                        "content": [{"type": "text", "text": msg.content}],
                    }
                )
        return bedrock_messages

    def _parse_response_text(self, payload):
        content = payload.get("content", [])
        if isinstance(content, list):
            texts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
            if texts:
                return "\n".join([value for value in texts if value]).strip()

        if isinstance(payload.get("outputText"), str):
            return payload.get("outputText", "")

        if isinstance(payload.get("completion"), str):
            return payload.get("completion", "")

        return ""

    def send_message(self, conversation, messages, agent=None):
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": self._build_messages(messages),
        }

        if agent and agent.system_prompt:
            request_body["system"] = agent.system_prompt

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            )

            raw_body = response.get("body")
            if hasattr(raw_body, "read"):
                payload = json.loads(raw_body.read())
            elif isinstance(raw_body, (bytes, bytearray)):
                payload = json.loads(raw_body.decode("utf-8"))
            elif isinstance(raw_body, str):
                payload = json.loads(raw_body)
            else:
                payload = {}

            content = self._parse_response_text(payload)
            return ProviderResult(status="completed", content=content, tool_calls=[])

        except ClientError as exc:
            logger.error("Bedrock client error: %s", exc)
            return ProviderResult(status="completed", content=f"⚠️ Bedrock API error: {str(exc)}")
        except BotoCoreError as exc:
            logger.error("Bedrock boto core error: %s", exc)
            return ProviderResult(status="completed", content=f"⚠️ Bedrock runtime error: {str(exc)}")
        except Exception as exc:
            logger.exception("Unexpected error in Bedrock provider: %s", exc)
            return ProviderResult(status="completed", content=f"⚠️ Unexpected error: {str(exc)}")

    def poll_response(self, conversation):
        return None
