"""Input validation utilities."""

from __future__ import annotations

import re

MAX_PROMPT_LENGTH = 10_000  # 10KB default
MIN_PROMPT_LENGTH = 1
ALLOWED_CHARS_PATTERN = re.compile(r'^[\w\s\-.,!?@#$%&*()\[\]{}:;"\'<>/\\+=\n\r\t]+$')


class ValidationError(ValueError):
    """Input validation error."""

    pass


def validate_prompt(text: str, max_length: int = MAX_PROMPT_LENGTH) -> str:
    """Validate user prompt.

    Note: HTML escaping is intentionally NOT performed here. Escaping is
    applied at render-time by callers that interpolate text into HTML
    (see ``html.escape`` usages in ``app.py``). Escaping at validation
    time would corrupt the prompt content sent to backend services and
    shown in plain-text widgets like ``st.code``.

    Args:
        text: User input prompt
        max_length: Maximum allowed length in characters

    Returns:
        Stripped prompt text

    Raises:
        ValidationError: If validation fails
    """
    if not text:
        raise ValidationError("Prompt cannot be empty")

    text = text.strip()

    if len(text) < MIN_PROMPT_LENGTH:
        raise ValidationError("Prompt is too short")

    if len(text) > max_length:
        raise ValidationError(
            f"Prompt exceeds maximum length of {max_length} characters "
            f"(got {len(text)})"
        )

    return text


def validate_domain(domain: str) -> str:
    """Validate semantic guardrail domain.

    Args:
        domain: Domain identifier

    Returns:
        Validated domain

    Raises:
        ValidationError: If domain is invalid
    """
    valid_domains = ["customer-support", "financial", "healthcare"]

    if domain not in valid_domains:
        raise ValidationError(
            f"Invalid domain '{domain}'. Must be one of: {', '.join(valid_domains)}"
        )

    return domain


def validate_method(method: str) -> str:
    """Validate sanitization method.

    Args:
        method: Sanitization method (protect or redact)

    Returns:
        Validated method

    Raises:
        ValidationError: If method is invalid
    """
    valid_methods = ["protect", "redact"]
    method = method.lower()

    if method not in valid_methods:
        raise ValidationError(
            f"Invalid method '{method}'. Must be one of: {', '.join(valid_methods)}"
        )

    return method
