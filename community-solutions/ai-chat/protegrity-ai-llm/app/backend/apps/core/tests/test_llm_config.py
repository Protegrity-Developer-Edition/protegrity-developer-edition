"""Tests for LLM provider environment configuration helpers."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.core.llm_config import get_enabled_llm_providers, validate_llm_provider_configuration


def test_validate_llm_provider_configuration_none_configured(monkeypatch):
    """Validation should fail when no provider credentials are configured."""
    for env_var in [
        "ENABLED_LLM_PROVIDERS",
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "ANTHROPIC_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
    ]:
        monkeypatch.delenv(env_var, raising=False)

    with pytest.raises(ImproperlyConfigured) as exc_info:
        validate_llm_provider_configuration()

    assert "No LLM provider is configured" in str(exc_info.value)


def test_validate_llm_provider_configuration_one_provider_configured(monkeypatch):
    """Validation should pass when one provider is fully configured."""
    monkeypatch.delenv("ENABLED_LLM_PROVIDERS", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "real-azure-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://demo.openai.azure.com/")

    enabled = validate_llm_provider_configuration()

    assert enabled == {"azure"}


def test_get_enabled_llm_providers_from_enabled_list(monkeypatch):
    """ENABLED_LLM_PROVIDERS list should normalize aliases."""
    monkeypatch.setenv("ENABLED_LLM_PROVIDERS", "azure_openai, openai")

    enabled = get_enabled_llm_providers()

    assert enabled == {"azure", "openai"}
