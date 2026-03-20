"""
LLM provider environment configuration helpers.

This module centralizes how enabled LLM providers are resolved from environment
variables so backend behavior is vendor-neutral and consistent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set

from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class ProviderSpec:
    canonical_name: str
    required_env_vars: tuple[str, ...]


PROVIDER_SPECS: Dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        canonical_name="openai",
        required_env_vars=("OPENAI_API_KEY",),
    ),
    "azure": ProviderSpec(
        canonical_name="azure",
        required_env_vars=("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"),
    ),
    "anthropic": ProviderSpec(
        canonical_name="anthropic",
        required_env_vars=("ANTHROPIC_API_KEY",),
    ),
    "bedrock": ProviderSpec(
        canonical_name="bedrock",
        required_env_vars=("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"),
    ),
}


PROVIDER_ALIASES = {
    "azure_openai": "azure",
    "azure": "azure",
    "openai": "openai",
    "anthropic": "anthropic",
    "bedrock": "bedrock",
}


def _normalize_provider_name(name: str) -> str:
    return PROVIDER_ALIASES.get(name.strip().lower(), name.strip().lower())


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    return (
        lowered.startswith("your-")
        or lowered.startswith("example-")
        or "placeholder" in lowered
        or lowered in {"changeme", "replace-me", "none"}
    )


def _is_real_env_value(var_name: str) -> bool:
    raw = os.getenv(var_name, "")
    return bool(raw and not _is_placeholder(raw))


def _missing_required_vars(provider_name: str) -> List[str]:
    spec = PROVIDER_SPECS[provider_name]
    return [var_name for var_name in spec.required_env_vars if not _is_real_env_value(var_name)]


def _parse_enabled_list(raw_value: str) -> Set[str]:
    parsed: Set[str] = set()
    for item in raw_value.split(","):
        if not item.strip():
            continue
        normalized = _normalize_provider_name(item)
        if normalized in PROVIDER_SPECS:
            parsed.add(normalized)
    return parsed


def get_enabled_llm_providers() -> Set[str]:
    """
    Resolve enabled LLM provider types.

    Resolution order:
    1) If ENABLED_LLM_PROVIDERS is set, use that list (normalized aliases).
    2) Otherwise, auto-detect providers by checking required env vars.

    Returns:
        Set of canonical provider_type names (openai, azure, anthropic, bedrock).
    """
    raw_enabled = os.getenv("ENABLED_LLM_PROVIDERS", "").strip()

    if raw_enabled:
        return _parse_enabled_list(raw_enabled)

    enabled: Set[str] = set()
    for provider_name in PROVIDER_SPECS:
        if not _missing_required_vars(provider_name):
            enabled.add(provider_name)
    return enabled


def validate_llm_provider_configuration() -> Set[str]:
    """
    Strictly validate that at least one provider is configured and usable.

    Raises:
        ImproperlyConfigured when no provider is configured or selected providers
        are missing required environment variables.
    """
    raw_enabled = os.getenv("ENABLED_LLM_PROVIDERS", "").strip()
    enabled = get_enabled_llm_providers()

    if raw_enabled and not enabled:
        raise ImproperlyConfigured(
            "ENABLED_LLM_PROVIDERS is set but no valid providers were recognized. "
            "Use provider names like: openai,azure_openai,anthropic,bedrock. "
            "See backend/.env.example and configure backend/.env."
        )

    if raw_enabled:
        missing_map = {provider: _missing_required_vars(provider) for provider in enabled}
        missing_map = {provider: missing for provider, missing in missing_map.items() if missing}
        if missing_map:
            details = "; ".join(
                f"{provider}: missing {', '.join(missing_vars)}"
                for provider, missing_vars in sorted(missing_map.items())
            )
            raise ImproperlyConfigured(
                "Invalid LLM provider configuration. "
                f"{details}. See backend/.env.example and configure backend/.env."
            )

    if not enabled:
        raise ImproperlyConfigured(
            "No LLM provider is configured. Configure at least one provider in backend/.env "
            "(for example Azure OpenAI, OpenAI, Anthropic, or Bedrock) and re-run. "
            "See backend/.env.example for vendor-neutral templates."
        )

    return enabled


def filter_enabled_llm_provider_queryset(queryset):
    """
    Filter a LLMProvider queryset to env-enabled provider types.

    Backward-compatible behavior:
    - If no provider can be resolved from env, returns original queryset unchanged.
      (Strict validation is enforced via validate_llm_provider_configuration in startup preflight.)
    """
    raw_enabled = os.getenv("ENABLED_LLM_PROVIDERS", "").strip()
    if not raw_enabled:
        return queryset

    enabled = get_enabled_llm_providers()
    if not enabled:
        return queryset
    return queryset.filter(provider_type__in=enabled)
