"""
Protegrity Dual-Gate security for Banking Portal Chatbot.
Gate 1 (Input):  semantic_guardrail -> find_and_protect
Gate 2 (Output): find_and_unprotect  OR  find_and_redact

Uses the real Protegrity Developer Edition SDK.
"""
from __future__ import annotations
import re
import copy
import logging
import requests
import base64
import hashlib
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass

# Import session-aware request helper for REST API calls (SGR, classify)
try:
    from services.protegrity_dev_edition_helper import protegrity_request, invalidate_session as _invalidate_api_session
    _SESSION_HELPER_AVAILABLE = True
except ImportError:
    _SESSION_HELPER_AVAILABLE = False
    _invalidate_api_session = lambda: None

from config.protegrity_config import (
    NAMED_ENTITY_MAP, COMBINED_ENTITY_MAPPINGS,
    ENTITY_TO_DATA_ELEMENT, get_data_element,
    CLASSIFY_URL, SGR_URL, SGR_PROCESSOR,
)

logger = logging.getLogger(__name__)

# Merge base + combined for SDK calls
_FULL_ENTITY_MAP = {**NAMED_ENTITY_MAP, **COMBINED_ENTITY_MAPPINGS}

# SDK session resilience settings
_SDK_MAX_RETRIES = 2
_SDK_RETRY_DELAY = 1.0

_token_map = {}
_token_map_lock = threading.Lock()
_sdk_lock = threading.Lock()
_sdk_configured = False

# Top-level SDK import — Python caches this, so it's only loaded once
try:
    import protegrity_developer_python as _sdk_module
    _SDK_INSTALLED = True
except ImportError:
    _sdk_module = None
    _SDK_INSTALLED = False
    print("[WARNING] Protegrity SDK not found. SDK-dependent features will fail.")


def _configure_sdk():
    """Configure the SDK (once). Returns the module or None on failure."""
    global _sdk_configured
    with _sdk_lock:
        if _sdk_configured:
            return _sdk_module
        if not _SDK_INSTALLED:
            return None
        try:
            _sdk_module.configure(
                endpoint_url=CLASSIFY_URL,
                named_entity_map=_FULL_ENTITY_MAP,
                classification_score_threshold=0.1,
                enable_logging=False,
                log_level="warning",
            )

            if hasattr(_sdk_module, "DATA_ELEMENT_MAPPING"):
                for k, v in ENTITY_TO_DATA_ELEMENT.items():
                    _sdk_module.DATA_ELEMENT_MAPPING[k] = v
                    logger.info("Patched DATA_ELEMENT_MAPPING: %s -> %s", k, v)

            try:
                from protegrity_developer_python.utils import pii_processing
                for k, v in ENTITY_TO_DATA_ELEMENT.items():
                    pii_processing.entity_endpoint_mapped[k] = v
                    logger.info("Patched entity_endpoint_mapped: %s -> %s", k, v)
                for k, v in COMBINED_ENTITY_MAPPINGS.items():
                    pii_processing.entity_endpoint_mapped[k] = v

                _original_merge = pii_processing._merge_overlapping_entities

                def _patched_merge(entity_spans):
                    result = _original_merge(entity_spans)
                    patched = {}
                    for key, (entity, score) in result.items():
                        if "|" in entity:
                            parts = entity.split("|")
                            preferred = [
                                "EMAIL_ADDRESS", "PERSON", "CREDIT_CARD", "PHONE_NUMBER",
                                "SOCIAL_SECURITY_ID", "LOCATION", "ORGANIZATION", "USERNAME", "URL",
                            ]
                            best = parts[0]
                            for pref in preferred:
                                if (pref in parts):
                                    best = pref
                                    break
                            remaining = [p for p in parts if p != best]
                            patched[key] = ("|".join([best] + remaining), score)
                        else:
                            patched[key] = (entity, score)
                    return patched

                pii_processing._merge_overlapping_entities = _patched_merge
                logger.info("Patched merge to prefer EMAIL_ADDRESS over URL")
            except Exception as pe:
                logger.warning("Could not patch entity_endpoint_mapped: %s", pe)

            _sdk_configured = True
            logger.info("Protegrity SDK configured: endpoint=%s", CLASSIFY_URL)
            print("[Protegrity] SDK configured successfully.")
            return _sdk_module
        except Exception as e:
            logger.warning("SDK config error: %s", e)
            print(f"[WARNING] Protegrity SDK config error: {e}. SDK-dependent features will fail.")
            return None


@dataclass
class GateResult:
    original_text: str
    transformed_text: str
    risk_score: Optional[float] = None
    risk_accepted: bool = True
    elements_found: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def _extract_elements(original, protected):
    elements = []
    for m in re.finditer(r'\[([A-Z_]+)\](.*?)\[/\1\]', protected):
        entity_type = m.group(1)
        token_value = m.group(2)
        elements.append({"type": entity_type, "token": token_value})
        with _token_map_lock:
            _token_map[token_value] = True
    if not elements and original != protected:
        elements.append({"type": "UNKNOWN", "note": "text changed"})
    return elements


def _strip_pii_tags(text):
    return re.sub(r'\[([A-Z_]+)\](.*?)\[/\1\]', r'\2', text)


def register_tokens_from_context(text):
    count = 0
    for m in re.finditer(r'\[([A-Z_]+)\](.*?)\[/\1\]', text):
        token_value = m.group(2)
        with _token_map_lock:
            if token_value not in _token_map:
                _token_map[token_value] = True
                count += 1
    if count:
        logger.info("Registered %d tokens from context into token_map", count)


def _obfuscate_date(date_str: str) -> str:
    """Deterministically obfuscate a date string (YYYY-MM-DD) to another valid-looking date."""
    try:
        from datetime import datetime as _dt
        dt = _dt.strptime(date_str, "%Y-%m-%d")
        h = int(hashlib.sha256(date_str.encode()).hexdigest()[:8], 16)
        offset_months = (h % 12) + 1
        new_year = dt.year + ((dt.month + offset_months - 1) // 12)
        new_month = ((dt.month + offset_months - 1) % 12) + 1
        new_day = min(dt.day, 28)
        return f"{new_year:04d}-{new_month:02d}-{new_day:02d}"
    except (ValueError, ImportError):
        return base64.b64encode(date_str.encode()).decode()


SGR_PROCESSORS = [SGR_PROCESSOR]


class ProtegrityGuard:
    def __init__(self):
        self.sdk = _configure_sdk()
        self.sdk_available = self.sdk is not None

    def _reinitialize_sdk(self):
        """Re-initialize the SDK if the underlying session has gone stale."""
        global _sdk_configured
        with _sdk_lock:
            logger.info("Re-initializing Protegrity SDK...")
            _sdk_configured = False
            if _SESSION_HELPER_AVAILABLE:
                _invalidate_api_session()
        self.sdk = _configure_sdk()
        self.sdk_available = self.sdk is not None
        if self.sdk_available:
            logger.info("SDK re-initialized successfully after session error")
        else:
            logger.warning("SDK re-initialization failed")

    def _sdk_call_with_retry(self, sdk_method_name: str, *args, **kwargs):
        """
        Call an SDK method (find_and_protect / find_and_unprotect) with
        automatic SDK re-initialization on session errors.
        """
        last_exception = None
        for attempt in range(1, _SDK_MAX_RETRIES + 1):
            try:
                method = getattr(self.sdk, sdk_method_name)
                return method(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                is_session_error = any(
                    kw in error_str
                    for kw in (
                        "session", "expired", "unauthorized", "401", "auth",
                        "invalid", "connection", "timeout", "refused",
                        "reset", "broken", "closed",
                    )
                )
                if is_session_error and attempt < _SDK_MAX_RETRIES:
                    logger.warning(
                        "SDK session error on attempt %d/%d calling %s: %s "
                        "— re-initializing SDK",
                        attempt, _SDK_MAX_RETRIES, sdk_method_name, e
                    )
                    self._reinitialize_sdk()
                    if not self.sdk_available:
                        raise
                    time.sleep(_SDK_RETRY_DELAY * attempt)
                else:
                    raise
        raise last_exception

    def _request_with_retry(self, method, url, retries=3, **kwargs):
        """Fallback retry logic when protegrity_dev_edition_helper is not available."""
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.request(method, url, **kwargs)
                if resp.status_code == 401:
                    logger.warning(
                        "401 on attempt %d/%d to %s — retrying",
                        attempt, retries, url
                    )
                    if attempt < retries:
                        time.sleep(1.0 * attempt)
                        continue
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                last_exception = e
                logger.warning(
                    "Request to %s failed (attempt %d/%d): %s",
                    url, attempt, retries, e
                )
                if attempt < retries:
                    time.sleep(1.0 * attempt)
        raise last_exception

    def semantic_guardrail_check(self, text, *, threshold=0.7) -> GateResult:
        max_risk_score = 0.0
        final_outcome = "accepted"
        final_explanation = ""
        processor_results = []
        all_responses = {}

        for processor in SGR_PROCESSORS:
            try:
                payload = {
                    "messages": [
                        {
                            "from": "user",
                            "to": "ai",
                            "content": text,
                            "processors": [processor],
                        }
                    ]
                }

                # Use session-aware request if available, with retry on 401/session expiry
                if _SESSION_HELPER_AVAILABLE:
                    resp = protegrity_request("POST", SGR_URL, json=payload, timeout=60)
                else:
                    resp = self._request_with_retry("POST", SGR_URL, json=payload, timeout=60)

                data = resp.json()
                all_responses[processor] = data

                proc_score = 0.0
                proc_outcome = "accepted"
                proc_explanation = ""

                if "messages" in data:
                    for msg in data["messages"]:
                        msg_score = float(msg.get("score", 0.0))
                        proc_score = max(proc_score, msg_score)
                        if msg.get("outcome") == "rejected":
                            proc_outcome = "rejected"
                        for p in msg.get("processors", []):
                            if p.get("explanation"):
                                proc_explanation = p["explanation"]
                            p_score = float(p.get("score", 0.0))
                            proc_score = max(proc_score, p_score)
                            if p.get("outcome") == "rejected":
                                proc_outcome = "rejected"

                if "batch" in data:
                    batch_score = float(data["batch"].get("score", 0.0))
                    proc_score = max(proc_score, batch_score)
                    if data["batch"].get("outcome") == "rejected":
                        proc_outcome = "rejected"

                processor_results.append({
                    "processor": processor,
                    "score": proc_score,
                    "outcome": proc_outcome,
                    "explanation": proc_explanation,
                })

                max_risk_score = max(max_risk_score, proc_score)
                if proc_outcome == "rejected":
                    final_outcome = "rejected"
                    if proc_explanation:
                        final_explanation = f"[{processor}] {proc_explanation}"

                logger.info("Guardrail [%s]: score=%.3f outcome=%s explanation=%s",
                            processor, proc_score, proc_outcome, proc_explanation[:60])

            except Exception as e:
                logger.warning("Guardrail [%s] failed: %s", processor, e)
                processor_results.append({
                    "processor": processor,
                    "score": 0.0,
                    "outcome": "error",
                    "explanation": str(e),
                })
                all_responses[processor] = {"error": str(e)}

        accepted = (final_outcome != "rejected") and (max_risk_score <= threshold)

        return GateResult(
            original_text=text, transformed_text=text,
            risk_score=max_risk_score, risk_accepted=accepted,
            metadata={
                "guardrail_responses": all_responses,
                "outcome": final_outcome,
                "explanation": final_explanation,
                "processors": processor_results,
                "threshold": threshold,
            },
        )

    def find_and_protect(self, text, *, classify_threshold=None) -> GateResult:
        if not self.sdk_available:
            raise RuntimeError("Protegrity SDK is required but not installed")

        sdk = self.sdk
        if classify_threshold is not None:
            try:
                sdk.configure(
                    endpoint_url=CLASSIFY_URL,
                    named_entity_map=_FULL_ENTITY_MAP,
                    classification_score_threshold=classify_threshold,
                    enable_logging=False,
                    log_level="warning",
                )
            except Exception:
                pass

        lines = text.split('\n')
        protected_lines = []
        all_elements = []

        for line in lines:
            stripped = line.rstrip()
            if stripped:
                try:
                    # Session-aware retry
                    protected_line = self._sdk_call_with_retry(
                        "find_and_protect", stripped
                    )
                    if isinstance(protected_line, str):
                        line_elements = _extract_elements(stripped, protected_line)
                        all_elements.extend(line_elements)
                        protected_lines.append(protected_line)
                    else:
                        protected_lines.append(stripped)
                except Exception as e:
                    logger.warning("Line protection failed: %s", e)
                    protected_lines.append(stripped)
            else:
                protected_lines.append(line)

            time.sleep(0.05)

        protected = '\n'.join(protected_lines)
        logger.info(
            "find_and_protect: %d elements, %d->%d chars",
            len(all_elements), len(text), len(protected)
        )
        return GateResult(
            original_text=text, transformed_text=protected,
            elements_found=all_elements, metadata={},
        )

    def find_and_unprotect(self, text) -> GateResult:
        if not self.sdk_available:
            raise RuntimeError("Protegrity SDK is required but not installed")

        sdk = self.sdk

        def _is_likely_token(value, entity_type):
            if entity_type == "PERSON":
                if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', value):
                    return False
                return True
            return True

        guard_ref = self  # capture self for use in nested function

        def _replace_token(match):
            entity_type = match.group(1)
            token_value = match.group(2)
            tagged = match.group(0)

            with _token_map_lock:
                mapped = _token_map.get(token_value)
                in_map = token_value in _token_map
            if mapped is not None and mapped is not True:
                return mapped

            if in_map:
                try:
                    # Session-aware retry
                    result = guard_ref._sdk_call_with_retry(
                        "find_and_unprotect", tagged
                    )
                    if isinstance(result, str) and result != tagged:
                        return (
                            _strip_pii_tags(result)
                            if re.search(r'\[([A-Z_]+)\]', result)
                            else result
                        )
                except Exception as e:
                    logger.warning(
                        "Token unprotect failed for %s: %s", entity_type, e
                    )
                return token_value

            if _is_likely_token(token_value, entity_type):
                try:
                    result = guard_ref._sdk_call_with_retry(
                        "find_and_unprotect", tagged
                    )
                    if isinstance(result, str) and result != tagged:
                        return (
                            _strip_pii_tags(result)
                            if re.search(r'\[([A-Z_]+)\]', result)
                            else result
                        )
                except Exception as e:
                    logger.warning(
                        "Heuristic unprotect failed for %s: %s", entity_type, e
                    )
                return token_value
            else:
                logger.info(
                    "Skipping plain-text %s: '%s'", entity_type, token_value[:30]
                )
                return token_value

        result = re.sub(r'\[([A-Z_]+)\](.*?)\[/\1\]', _replace_token, text)
        return GateResult(
            original_text=text, transformed_text=result,
            elements_found=[], metadata={},
        )

    def find_and_redact(self, text) -> GateResult:
        redacted = re.sub(r'\[([A-Z_]+)\](.*?)\[/\1\]', '[REDACTED]', text)
        return GateResult(original_text=text, transformed_text=redacted, elements_found=[], metadata={})

    def gate1_input(self, text, *, risk_threshold=0.7, classify_threshold=None) -> GateResult:
        gr = self.semantic_guardrail_check(text, threshold=risk_threshold)
        if not gr.risk_accepted:
            gr.transformed_text = ""
            gr.metadata["blocked"] = True
            return gr
        pr = self.find_and_protect(text, classify_threshold=classify_threshold)
        pr.risk_score = gr.risk_score
        pr.risk_accepted = gr.risk_accepted
        pr.metadata["guardrail_response"] = gr.metadata.get("guardrail_response")
        return pr

    def gate2_output(self, text, *, restore=True) -> GateResult:
        if restore:
            return self.find_and_unprotect(text)
        return self.find_and_redact(text)

    def protect_customer(self, customer: dict) -> dict:
        """Protect customer PII by wrapping fields with context for the classifier."""
        protected = copy.deepcopy(customer)

        field_context = {
            "name": "My name is {}",
            "email": "My email address is {}",
            "phone": "My phone number is {}",
            "ssn": "My social security number is {}",
            "address": "{}",
            "dob": "dob: {}",
        }
        field_fallback_tag = {
            "name": "PERSON",
            "email": "EMAIL_ADDRESS",
            "phone": "PHONE_NUMBER",
            "ssn": "SOCIAL_SECURITY_ID",
            "address": "LOCATION",
            "dob": "DATETIME",
        }
        field_prefix = {
            "name": "My name is ",
            "email": "My email address is ",
            "phone": "My phone number is ",
            "ssn": "My social security number is ",
            "address": "",
            "dob": "dob: ",
        }

        max_retries = 3

        for fld, template in field_context.items():
            val = protected.get(fld)
            if not val or not isinstance(val, str):
                continue

            contextual = template.format(val)
            detected = False

            for attempt in range(max_retries):
                result = self.find_and_protect(contextual)
                if result.transformed_text != contextual and result.elements_found:
                    prefix = field_prefix[fld]
                    tokenized_full = result.transformed_text
                    if prefix and tokenized_full.startswith(prefix):
                        tokenized_value = tokenized_full[len(prefix):]
                    else:
                        tokenized_value = tokenized_full

                    tags = re.findall(r'\[([A-Z_]+)\](.*?)\[/\1\]', tokenized_value)
                    with _token_map_lock:
                        for entity_tag, token_val in tags:
                            _token_map[token_val] = True

                    if tags:
                        if len(tags) == 1:
                            entity_tag, token_val = tags[0]
                            protected[fld] = f"[{entity_tag}]{token_val}[/{entity_tag}]"
                        else:
                            protected[fld] = tokenized_value
                        logger.info("protect_customer: %s -> %d tags (attempt %d), value='%s'",
                                    fld, len(tags), attempt + 1, protected[fld][:60])
                        detected = True
                        break
                    else:
                        logger.info("protect_customer: %s no tags extracted (attempt %d)", fld, attempt + 1)
                else:
                    logger.info("protect_customer: %s not detected (attempt %d/%d)",
                                fld, attempt + 1, max_retries)

                # Wait before retry, increasing delay
                if attempt < max_retries - 1:
                    delay = 0.5 * (attempt + 1)
                    logger.info("  Retrying %s in %.1fs...", fld, delay)
                    time.sleep(delay)

            if not detected:
                fallback = field_fallback_tag.get(fld, "PII")
                protected[fld] = f"[{fallback}]{val}[/{fallback}]"
                logger.info("protect_customer: %s wrapped with fallback [%s] after %d attempts",
                            fld, fallback, max_retries)

        for card in protected.get("credit_cards", []):
            if "card_number" in card and isinstance(card["card_number"], str):
                cc_val = card["card_number"]
                contextual = f"My credit card number is {cc_val}"
                detected_cc = False
                for attempt in range(max_retries):
                    result = self.find_and_protect(contextual)
                    if result.transformed_text != contextual and result.elements_found:
                        tags = re.findall(r'\[([A-Z_]+)\](.*?)\[/\1\]', result.transformed_text)
                        if tags:
                            entity_tag, token_val = tags[0]
                            card["card_number"] = f"[{entity_tag}]{token_val}[/{entity_tag}]"
                            with _token_map_lock:
                                _token_map[token_val] = True
                            detected_cc = True
                            break
                    if attempt < max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))
                if not detected_cc:
                    card["card_number"] = f"[CREDIT_CARD]{cc_val}[/CREDIT_CARD]"

        for acct in protected.get("accounts", []):
            for fld in ["account_number", "routing_number"]:
                if fld in acct and isinstance(acct[fld], str):
                    orig_val = acct[fld]
                    contextual = f"My bank {fld.replace('_', ' ')} is {orig_val}"
                    detected_acct = False
                    for attempt in range(max_retries):
                        result = self.find_and_protect(contextual)
                        if result.transformed_text != contextual and result.elements_found:
                            tags = re.findall(r'\[([A-Z_]+)\](.*?)\[/\1\]', result.transformed_text)
                            if tags:
                                entity_tag, token_val = tags[0]
                                acct[fld] = f"[{entity_tag}]{token_val}[/{entity_tag}]"
                                with _token_map_lock:
                                    _token_map[token_val] = True
                                detected_acct = True
                                break
                        if attempt < max_retries - 1:
                            time.sleep(0.5 * (attempt + 1))
                    if not detected_acct:
                        acct[fld] = f"[BANK_ACCOUNT]{orig_val}[/BANK_ACCOUNT]"

        protected.pop("password_plain", None)
        return protected

    def unprotect_customer(self, customer: dict) -> dict:
        unprotected = copy.deepcopy(customer)
        pii_fields = ["name", "email", "phone", "ssn", "address", "dob"]
        for fld in pii_fields:
            if fld in unprotected and isinstance(unprotected[fld], str):
                result = self.find_and_unprotect(unprotected[fld])
                unprotected[fld] = result.transformed_text
        for card in unprotected.get("credit_cards", []):
            for fld in ["card_number", "cvv"]:
                if fld in card and isinstance(card[fld], str):
                    result = self.find_and_unprotect(card[fld])
                    card[fld] = result.transformed_text
        for acct in unprotected.get("accounts", []):
            for fld in ["account_number", "routing_number"]:
                if fld in acct and isinstance(acct[fld], str):
                    result = self.find_and_unprotect(acct[fld])
                    acct[fld] = result.transformed_text
        return unprotected

    def protect_text(self, text: str) -> str:
        result = self.find_and_protect(text)
        return result.transformed_text

    def unprotect_text(self, text: str) -> str:
        result = self.find_and_unprotect(text)
        return result.transformed_text

    def protect_for_llm(self, prompt: str, customer_context: str) -> tuple[str, str]:
        return self.protect_text(prompt), self.protect_text(customer_context)

    def unprotect_llm_response(self, response: str) -> str:
        return self.unprotect_text(response)

_guard_instance = None
_guard_lock = threading.Lock()


def get_guard() -> ProtegrityGuard:
    global _guard_instance
    if _guard_instance is None:
        with _guard_lock:
            if _guard_instance is None:
                _guard_instance = ProtegrityGuard()
    return _guard_instance


if __name__ == "__main__":
    guard = get_guard()
    print(f"SDK available: {guard.sdk_available}")

    test_text = "My name is John Smith, my SSN is 123-45-6789 and email is john@example.com"
    print(f"\nOriginal:  {test_text}")

    result = guard.gate1_input(test_text)
    print(f"Protected: {result.transformed_text}")
    print(f"Risk:      {result.risk_score}")
    print(f"Elements:  {result.elements_found}")

    restored = guard.gate2_output(result.transformed_text)
    print(f"Restored:  {restored.transformed_text}")