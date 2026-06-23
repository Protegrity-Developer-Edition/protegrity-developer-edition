"""
LLM provider factory.

Returns a unified callable: llm(messages) -> str
Also provides LangChain-compatible ChatModel objects.
"""

from __future__ import annotations
from typing import List, Dict

from config.orchestration_config import (
    LLM_PROVIDER, get_model_name,
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY,
)

# ── Lazy module-level imports (patchable by tests) ───────────────────
try:
    import openai
except ImportError:
    openai = None  # type: ignore

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore

try:
    from groq import Groq
except ImportError:
    Groq = None  # type: ignore


def get_llm():
    """
    Return a callable: fn(messages: List[Dict]) -> str

    messages format: [{"role": "system"|"user"|"assistant", "content": "..."}]
    """
    provider = LLM_PROVIDER
    model = get_model_name()

    if provider == "openai":
        return _openai_llm(model)
    elif provider == "anthropic":
        return _anthropic_llm(model)
    elif provider == "groq":
        return _groq_llm(model)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_llm_for_langchain():
    """Return a LangChain ChatModel instance for the configured provider."""
    provider = LLM_PROVIDER
    model = get_model_name()

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=OPENAI_API_KEY, temperature=0)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=ANTHROPIC_API_KEY, temperature=0)

    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=model, api_key=GROQ_API_KEY, temperature=0)

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# ── Provider implementations ────────────────────────────────────────

def _openai_llm(model: str):
    if openai is None:
        raise ImportError("pip install openai")
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    def call(messages: List[Dict]) -> str:
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0)
        if not resp.choices or not resp.choices[0].message.content:
            raise ValueError(f"OpenAI returned empty response for model {model}")
        return resp.choices[0].message.content.strip()
    return call


def _anthropic_llm(model: str):
    if anthropic is None:
        raise ImportError("pip install anthropic")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def call(messages: List[Dict]) -> str:
        # Anthropic expects system prompt separately
        system = ""
        chat_msgs = []
        for m in messages:
            if m["role"] == "system":
                system += m["content"] + "\n"
            else:
                chat_msgs.append(m)

        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system.strip() or "You are a helpful assistant.",
            messages=chat_msgs,
            temperature=0,
        )
        if not resp.content or not resp.content[0].text:
            raise ValueError(f"Anthropic returned empty response for model {model}")
        return resp.content[0].text.strip()
    return call


def _groq_llm(model: str):
    if Groq is None:
        raise ImportError("pip install groq")
    client = Groq(api_key=GROQ_API_KEY)

    def call(messages: List[Dict]) -> str:
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0)
        if not resp.choices or not resp.choices[0].message.content:
            raise ValueError(f"Groq returned empty response for model {model}")
        return resp.choices[0].message.content.strip()
    return call

# ── Aliases for backward compatibility ──────────────────────────────
get_llm_provider = get_llm