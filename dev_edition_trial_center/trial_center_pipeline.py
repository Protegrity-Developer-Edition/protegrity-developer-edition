"""Pipeline utilities for the Dev Edition Trial Center.

This module orchestrates Semantic Guardrail checks, Data Discovery insights,
and protection/redaction workflows provided by the Protegrity Developer Edition
SDK. It can be consumed from CLI tools or interactive apps to sanitize prompts
before they reach downstream GenAI providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import re
from typing import Any, Callable, Dict, Optional

import json
import logging

import protegrity_developer_python as protegrity
import requests


LOGGER = logging.getLogger(__name__)


def _preview_text(text: str, limit: int = 160) -> str:
    """Return a single-line preview for logging."""
    single_line = " ".join(text.split())
    if len(single_line) <= limit:
        return single_line
    return f"{single_line[: limit - 3]}..."


def _summarize_discovery(payload: Any) -> str:
    if isinstance(payload, dict):
        summaries = []
        for key in ("entities", "detections", "classifications"):
            value = payload.get(key)
            if isinstance(value, list):
                summaries.append(f"{key}={len(value)}")
        if summaries:
            return ", ".join(summaries)
    return f"payload_type={type(payload).__name__}"


PROTECTED_TAG_PATTERN = re.compile(r"\[(?P<label>[A-Z_]+)](?P<payload>.*?)\[/\1]")


def _build_display_prompt(
    sanitized_prompt: str,
    method_used: str,
    original_prompt: str,
    discovery_result: Dict[str, Any],
    named_entity_map: Dict[str, str],
) -> str:
    """Return a human-friendly preview for protected payloads."""

    if method_used.lower() != "protect":
        return sanitized_prompt

    return sanitized_prompt


DEFAULT_ENTITY_MAP: Dict[str, str] = {
    "EMAIL_ADDRESS": "EMAIL",
    "EMAIL": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "MOBILE_NUMBER": "PHONE",
    "PERSON": "PERSON",
    "DATE_OF_BIRTH": "DOB",
    "DATE_TIME": "DATE",
    "ACCOUNT_NUMBER": "ACCOUNT_NUMBER",
    "BANK_ACCOUNT_NUMBER": "ACCOUNT_NUMBER",
    "CREDIT_CARD_NUMBER": "PAYMENT_CARD",
    "SOCIAL_SECURITY_NUMBER": "SSN",
    "NATIONAL_ID_NUMBER": "NATIONAL_ID",
    "PASSPORT": "PASSPORT",
    "INSURANCE_POLICY_ID": "INSURANCE_POLICY_ID",
    "PAN": "TAX_ID",
    "TAX_ID": "TAX_ID",
    "STATE": "STATE",
    "CITY": "CITY",
    "STREET": "STREET",
    "LOCATION": "LOCATION",
    "BUILDING": "LOCATION",
    "USERNAME": "USERNAME",
}


@dataclass
class GuardrailConfig:
    """Configuration for Semantic Guardrail scoring."""

    url: str = (
        "http://localhost:8581/pty/semantic-guardrail/v1.0/conversations/messages/scan"
    )
    rejection_threshold: float = 0.6
    timeout_seconds: float = 30.0


@dataclass
class SanitizationConfig:
    """Configuration for Data Discovery + protection/redaction."""

    method: str = "protect"  # "protect" or "redact"
    fallback_method: str = "redact"
    classification_score_threshold: float = 0.6
    masking_char: str = "#"
    named_entity_map: Optional[Dict[str, str]] = None
    endpoint_url: Optional[str] = None
    enable_logging: bool = False
    log_level: str = "info"

    def normalized_method(self) -> str:
        return self.method.lower()


@dataclass
class GuardrailResult:
    """Container for Semantic Guardrail responses."""

    outcome: str
    score: float
    explanation: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_rejected(self) -> bool:
        return self.outcome.lower() == "rejected"


@dataclass
class SanitizationResult:
    """Holds the output from a single sanitization attempt."""

    sanitized_prompt: str
    method_used: str  # "protect" or "redact"
    discovery_entities: Dict[str, Any]
    original_prompt: str
    raw_sanitized_prompt: Optional[str]  # non-display version (tokens)
    unprotected_prompt: Optional[str]
    unprotect_error: Optional[str]
    display_prompt: Optional[str]
    sanitize_error: Optional[str] = None


@dataclass
class TrialCenterReport:
    """Aggregate report returned by TrialCenterPipeline."""

    guardrail: GuardrailResult
    sanitization: SanitizationResult

    def to_json(self) -> str:
        """Serialize the report for persistence."""
        payload = {
            "guardrail": asdict(self.guardrail),
            "sanitization": asdict(self.sanitization),
        }
        return json.dumps(payload, indent=2)


class SemanticGuardrailClient:
    """Lightweight client for the Semantic Guardrail REST endpoint."""

    def __init__(self, config: GuardrailConfig) -> None:
        self._config = config

    def score_prompt(self, prompt: str, metadata: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        """Submit a single-turn conversation for scoring."""
        payload = {
            "messages": [
                {
                    "from": "user",
                    "to": "ai",
                    "content": prompt,
                    "processors": ["semantic"],
                }
            ]
        }
        if metadata:
            payload["metadata"] = metadata  # type: ignore[assignment]

        LOGGER.info(
            "Submitting prompt to semantic guardrail (len=%d): %s",
            len(prompt),
            _preview_text(prompt),
        )
        LOGGER.debug("Semantic guardrail payload: %s", json.dumps(payload, indent=2))
        try:
            response = requests.post(
                self._config.url,
                json=payload,
                timeout=self._config.timeout_seconds,
            )
            response.raise_for_status()
        except requests.HTTPError as error:  # type: ignore[attr-defined]
            raise RuntimeError(
                f"Semantic guardrail request failed ({error.response.status_code}): {error.response.text}"
            ) from error
        data = response.json()
        LOGGER.debug("Semantic guardrail response: %s", json.dumps(data, indent=2))

        message_result = data.get("messages", [{}])[0]
        outcome = message_result.get("outcome", "accepted")
        score = float(message_result.get("score", 0.0))
        processors = message_result.get("processors", [])
        explanation = None
        if processors:
            explanation = ", ".join(
                f"{proc.get('name')}: {proc.get('explanation') or proc.get('score')}"
                for proc in processors
            )

        # Guardrail default: if score exceeds threshold, treat as rejected.
        LOGGER.info(
            "Semantic guardrail result outcome=%s score=%.2f",
            outcome,
            score,
        )

        return GuardrailResult(outcome=outcome, score=score, explanation=explanation, raw_response=data)


def _split_line(segment: str) -> tuple[str, str]:
    """Split a text segment into its content and trailing newline (if present)."""

    if segment.endswith("\r\n"):
        return segment[:-2], "\r\n"
    if segment.endswith("\n") or segment.endswith("\r"):
        return segment[:-1], segment[-1]
    return segment, ""


def _apply_linewise(prompt: str, operation: Callable[[str], str]) -> str:
    """Apply an SDK operation to each non-empty line while preserving formatting."""

    if not prompt:
        return operation(prompt)

    segments = prompt.splitlines(keepends=True)
    if not segments:
        segments = [prompt]

    output_parts: list[str] = []
    for segment in segments:
        line_text, line_break = _split_line(segment)
        if line_text.strip():
            sanitized_line = operation(line_text)
            output_parts.append(sanitized_line + line_break)
        else:
            output_parts.append(segment)
    return "".join(output_parts)


class PromptSanitizer:
    """Handles discovery + protect/redact operations via the SDK."""

    def __init__(self, config: SanitizationConfig) -> None:
        self._config = config
        named_map = dict(DEFAULT_ENTITY_MAP)
        if config.named_entity_map:
            named_map.update(config.named_entity_map)

        self._base_kwargs: Dict[str, Any] = {
            "endpoint_url": config.endpoint_url,
            "named_entity_map": named_map,
            "classification_score_threshold": config.classification_score_threshold,
            "masking_char": config.masking_char,
            "enable_logging": config.enable_logging,
            "log_level": config.log_level,
        }
        self._named_entity_map = named_map
        self._primary_method = config.normalized_method()
        self._apply_configuration(self._primary_method)

    def sanitize(self, prompt: str) -> SanitizationResult:
        """Discover entities and apply protection/redaction."""
        LOGGER.info(
            "Running discovery with method='%s'",
            self._primary_method,
        )
        discovery_result = protegrity.discover(prompt)
        LOGGER.info("Discovery summary: %s", _summarize_discovery(discovery_result))
        LOGGER.debug("Discovery payload: %s", json.dumps(discovery_result, indent=2))
        normalized_discovery = self._normalize_discovery_entities(discovery_result)
        method_used = self._primary_method

        sanitize_fn = self._select_method(method_used)
        sanitized_prompt: Optional[str] = None
        sanitize_error: Optional[str] = None
        
        try:
            sanitized_prompt = _apply_linewise(prompt, sanitize_fn)
            LOGGER.info("Method '%s' succeeded.", method_used)
            
            # For protection method, check if data was actually modified
            if method_used == "protect" and sanitized_prompt.strip() == prompt.strip():
                sanitize_error = "Protection did not modify the text. This indicates protection failed for all entities (likely due to missing credentials or authentication failure)."
                LOGGER.warning(sanitize_error)
                sanitized_prompt = None
                
        except Exception as error:  # noqa: BLE001
            sanitize_error = str(error)
            LOGGER.error(
                "Method '%s' failed: %s",
                method_used,
                error,
            )

        display_prompt = None
        if sanitized_prompt:
            LOGGER.debug(
                "Sanitized prompt via %s (len=%d): %s",
                method_used,
                len(sanitized_prompt),
                _preview_text(sanitized_prompt),
            )
            display_prompt = _build_display_prompt(
                sanitized_prompt,
                method_used,
                prompt,
                discovery_result,
                self._named_entity_map,
            )
        
        unprotected_prompt: Optional[str] = None
        unprotect_error: Optional[str] = None
        if method_used == "protect" and sanitized_prompt:
            unprotected_prompt, unprotect_error = self._attempt_unprotect(
                sanitized_prompt,
                prompt,
            )
        
        return SanitizationResult(
            sanitized_prompt=sanitized_prompt or prompt,
            method_used=method_used,
            discovery_entities=normalized_discovery,
            original_prompt=prompt,
            raw_sanitized_prompt=sanitized_prompt if method_used == "protect" else None,
            unprotected_prompt=unprotected_prompt,
            unprotect_error=unprotect_error,
            display_prompt=display_prompt,
            sanitize_error=sanitize_error,
        )

    def _select_method(self, method: str):
        method = method.lower()
        if method == "protect":
            return protegrity.find_and_protect
        if method == "redact":
            return protegrity.find_and_redact
        raise ValueError(f"Unsupported sanitization method: {method}")

    def _normalize_discovery_entities(self, discovery_result: Any) -> Dict[str, Any]:
        if not isinstance(discovery_result, dict):
            return {}

        normalized: Dict[str, list[Any]] = {}
        for raw_label, entries in discovery_result.items():
            if not isinstance(entries, list):
                continue

            normalized_label = self._resolve_label(raw_label)
            target_list = normalized.setdefault(normalized_label, [])
            target_list.extend(entries)

        return normalized

    def _resolve_label(self, raw_label: str) -> str:
        if raw_label in self._named_entity_map:
            return self._named_entity_map[raw_label]

        if "|" not in raw_label:
            return self._named_entity_map.get(raw_label, raw_label)

        candidate_labels = [part.strip() for part in raw_label.split("|") if part.strip()]
        for candidate in candidate_labels:
            if candidate in self._named_entity_map:
                mapped = self._named_entity_map[candidate]
                self._named_entity_map[raw_label] = mapped
                return mapped
            if candidate in DEFAULT_ENTITY_MAP:
                mapped = DEFAULT_ENTITY_MAP[candidate]
                self._named_entity_map[raw_label] = mapped
                return mapped

        if candidate_labels:
            fallback = candidate_labels[0]
            self._named_entity_map[raw_label] = fallback
            return fallback

        return self._named_entity_map.get(raw_label, raw_label)

    def _apply_configuration(self, method: str) -> None:
        kwargs = dict(self._base_kwargs)
        normalized = method.lower()
        if normalized in {"redact", "mask"}:
            kwargs["method"] = normalized
        protegrity.configure(**kwargs)

    def _attempt_unprotect(self, text: str, original_prompt: str) -> tuple[Optional[str], Optional[str]]:
        # First check if the "protected" text is identical to original (meaning protection failed)
        if text.strip() == original_prompt.strip():
            message = "Protection did not modify the text. This indicates protection failed for all entities (likely due to missing credentials or authentication failure)."
            LOGGER.warning(message)
            return None, message
        
        try:
            restored = protegrity.find_and_unprotect(text)
        except Exception as error:  # noqa: BLE001
            message = f"Unprotect error: {error}"
            LOGGER.warning(message)
            return None, message

        # Normalize whitespace for comparison
        normalized_original = " ".join(original_prompt.split())
        normalized_restored = " ".join(restored.split())
        
        if normalized_restored != normalized_original:
            LOGGER.warning(
                "Unprotect mismatch detected (expected len=%d, got len=%d).",
                len(normalized_original),
                len(normalized_restored),
            )
            LOGGER.debug("Expected: %s", _preview_text(normalized_original, limit=200))
            LOGGER.debug("Got: %s", _preview_text(normalized_restored, limit=200))
            return None, "find_and_unprotect returned content that did not match the original prompt."

        LOGGER.info("find_and_unprotect succeeded (len=%d).", len(restored))
        return restored, None



class TrialCenterPipeline:
    """Co-ordinates guardrail scoring, sanitization, and reporting."""

    def __init__(
        self,
        guardrail_config: Optional[GuardrailConfig] = None,
        sanitization_config: Optional[SanitizationConfig] = None,
    ) -> None:
        self.guardrail_client = SemanticGuardrailClient(guardrail_config or GuardrailConfig())
        self.sanitizer = PromptSanitizer(sanitization_config or SanitizationConfig())

    def process_prompt(
        self,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TrialCenterReport:
        guardrail_result = self.guardrail_client.score_prompt(prompt, metadata)
        sanitization_result = self.sanitizer.sanitize(prompt)

        return TrialCenterReport(
            guardrail=guardrail_result,
            sanitization=sanitization_result,
        )


def load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_report(report: TrialCenterReport, output_dir: Path, stem: str) -> Dict[str, Path]:
    ensure_directory(output_dir)
    sanitized_path = output_dir / f"{stem}_sanitized.txt"
    report_path = output_dir / f"{stem}_report.json"

    sanitized_path.write_text(report.sanitization.sanitized_prompt, encoding="utf-8")
    report_path.write_text(report.to_json(), encoding="utf-8")

    return {"sanitized": sanitized_path, "report": report_path}


def process_from_file(
    prompt_path: Path,
    output_dir: Path,
    metadata: Optional[Dict[str, Any]] = None,
    pipeline: Optional[TrialCenterPipeline] = None,
) -> TrialCenterReport:
    """Utility wrapper to process a prompt file and persist outputs."""
    pipeline = pipeline or TrialCenterPipeline()
    prompt_text = load_prompt(prompt_path)
    report = pipeline.process_prompt(prompt_text, metadata=metadata)
    write_report(report, output_dir, stem=prompt_path.stem)
    return report


__all__ = [
    "TrialCenterPipeline",
    "GuardrailConfig",
    "SanitizationConfig",
    "TrialCenterReport",
    "process_from_file",
]
