"""Tests for provider factory routing and DummyProvider fallback behavior."""

from types import SimpleNamespace

import pytest

from apps.core.providers import DummyProvider, get_provider


def _llm(provider_type: str, model_identifier: str = "model-id"):
    return SimpleNamespace(
        id=f"{provider_type}-test",
        name=f"{provider_type} test",
        provider_type=provider_type,
        model_identifier=model_identifier,
        max_tokens=1024,
        configuration={},
    )


@pytest.mark.parametrize(
    "provider_type, env_vars",
    [
        (
            "openai",
            {
                "OPENAI_API_KEY": "sk-test",
                "OPENAI_BASE_URL": "https://api.openai.com/v1",
            },
        ),
        (
            "anthropic",
            {
                "ANTHROPIC_API_KEY": "ant-test",
                "ANTHROPIC_MODEL": "claude-3-5-sonnet-latest",
            },
        ),
        (
            "bedrock",
            {
                "AWS_ACCESS_KEY_ID": "AKIAXXXXXXXX",
                "AWS_SECRET_ACCESS_KEY": "secret",
                "AWS_DEFAULT_REGION": "us-east-1",
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            },
        ),
    ],
)
def test_get_provider_routes_to_concrete_provider(monkeypatch, provider_type, env_vars):
    # ensure empty defaults first
    for key in [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "BEDROCK_MODEL_ID",
    ]:
        monkeypatch.delenv(key, raising=False)

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    provider = get_provider(_llm(provider_type))
    assert not isinstance(provider, DummyProvider)


@pytest.mark.parametrize("provider_type", ["openai", "anthropic", "bedrock", "azure"])
def test_get_provider_falls_back_to_dummy_when_env_missing(monkeypatch, provider_type):
    # Remove all relevant env vars to force provider init failure.
    for key in [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "BEDROCK_MODEL_ID",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
    ]:
        monkeypatch.delenv(key, raising=False)

    provider = get_provider(_llm(provider_type))
    assert isinstance(provider, DummyProvider)


def test_get_provider_unknown_type_still_returns_dummy():
    provider = get_provider(_llm("unknown-provider"))
    assert isinstance(provider, DummyProvider)
