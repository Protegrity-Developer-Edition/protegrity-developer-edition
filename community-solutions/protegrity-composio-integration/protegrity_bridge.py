"""
Protegrity Bridge — wraps the Developer Edition SDK for:
  • find_and_protect   (discover PII → tokenize)
  • find_and_unprotect (detokenize, RBAC-gated)
  • find_and_redact    (replace with [REDACTED])
  • semantic_guardrail (risk scoring)

Adapted from the existing BankingPortalChatbot patterns.
"""
from __future__ import annotations
import os, re, logging, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import Config, load_config

logger = logging.getLogger(__name__)

# ── Entity → SDK data-element mapping ────────────────────────────────────────
NAMED_ENTITY_MAP: Dict[str, str] = {
    "EMAIL_ADDRESS": "email",
    "PERSON": "string",
    "PHONE_NUMBER": "phone",
    "SOCIAL_SECURITY_ID": "ssn",
    "SOCIAL_SECURITY_NUMBER": "ssn",
    "CREDIT_CARD": "ccn",
    "LOCATION": "address",
    "IP_ADDRESS": "address",
    "ORGANIZATION": "string",
    "URL": "address",
    "USERNAME": "string",
    "URL|EMAIL_ADDRESS": "email",
    "URL|EMAIL_ADDRESS|USERNAME": "email",
    "EMAIL_ADDRESS|URL": "email",
    "EMAIL_ADDRESS|USERNAME": "email",
    "PERSON|LOCATION": "string",
    "CREDIT_CARD|PERSON": "ccn",
}

_sdk_configured = False
_sdk_configured_at: float = 0.0
# The appython Session default idle timeout is 15 minutes. Re-initialise every
# 12 minutes as a safety net, AND always create sessions with an 8-hour timeout.
_SDK_SESSION_TTL = 720  # seconds (12 min — just under the 15-min idle default)
_SESSION_TIMEOUT_MINUTES = 480  # 8 hours — passed to create_session()
_token_map: Dict[str, bool] = {}   # tracks live tokens for unprotect

# Entity tags the SDK does not map out of the box; merged into its mapping below.
ENTITY_TO_DATA_ELEMENT: Dict[str, str] = {
    "PERSON": "string",
    "EMAIL_ADDRESS": "email",
    "PHONE_NUMBER": "phone",
    "SOCIAL_SECURITY_ID": "ssn",
    "SOCIAL_SECURITY_NUMBER": "ssn",
    "CREDIT_CARD": "ccn",
    "LOCATION": "address",
    "IP_ADDRESS": "address",
    "ORGANIZATION": "string",
    "URL": "address",
    "USERNAME": "string",
    "DATETIME": "datetime",
    "DOB": "datetime",
    "HEALTH_CARE_ID": "string",
    "BANK_ACCOUNT": "number",
    "ACCOUNT_NUMBER": "string",
    "TAX_ID": "ssn",
    "NATIONAL_ID": "ssn",
}

# ── SDK bootstrap ─────────────────────────────────────────────────────────────

def _import_sdk():
    import protegrity_developer_python as sdk
    return sdk


def _reset_protector_session():
    """Force the appython Protector session to re-authenticate on next use."""
    try:
        from protegrity_developer_python.utils import protector as _pty_protector
        _pty_protector.instance = None
        _pty_protector.session = None
        logger.info("Protegrity protector session cleared.")
    except Exception as e:
        logger.warning("Could not reset protector session: %s", e)


def _create_long_lived_session():
    """Replace the default 15-minute session with an 8-hour one."""
    try:
        from protegrity_developer_python.utils import protector as _pty_protector
        _reset_protector_session()
        inst = _pty_protector._initialize_protector()
        _pty_protector.instance = inst
        _pty_protector.session = inst.create_session(
            "superuser", timeout=_SESSION_TIMEOUT_MINUTES
        )
        logger.info(
            "Protegrity session created with %d-minute timeout.",
            _SESSION_TIMEOUT_MINUTES,
        )
    except Exception as e:
        logger.warning("Could not create long-lived session (using default): %s", e)


def _configure_sdk(cfg: Config):
    global _sdk_configured, _sdk_configured_at
    now = time.time()
    if _sdk_configured and (now - _sdk_configured_at) > _SDK_SESSION_TTL:
        logger.info("SDK session TTL exceeded — forcing re-authentication.")
        _sdk_configured = False
        _reset_protector_session()
    if _sdk_configured:
        return _import_sdk()
    sdk = _import_sdk()
    # Patch extra entity mappings
    if hasattr(sdk, "DATA_ELEMENT_MAPPING"):
        for k, v in ENTITY_TO_DATA_ELEMENT.items():
            sdk.DATA_ELEMENT_MAPPING.setdefault(k, v)
    try:
        from protegrity_developer_python.utils import pii_processing
        for k, v in {**ENTITY_TO_DATA_ELEMENT, **{
            ek: ev for ek, ev in NAMED_ENTITY_MAP.items() if "|" in ek
        }}.items():
            pii_processing.entity_endpoint_mapped[k] = v
    except Exception as e:
        logger.warning("Could not patch entity mappings: %s", e)

    sdk.configure(
        endpoint_url=cfg.classify_url,
        named_entity_map=NAMED_ENTITY_MAP,
        classification_score_threshold=0.1,
        enable_logging=False,
        log_level="warning",
    )
    _create_long_lived_session()
    _sdk_configured = True
    _sdk_configured_at = time.time()
    logger.info("Protegrity SDK configured: endpoint=%s", cfg.classify_url)
    return sdk


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ProtectResult:
    original: str
    protected: str
    elements_found: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def pii_detected(self) -> bool:
        return self.original != self.protected or bool(self.elements_found)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "protected": self.protected,
            "pii_detected": self.pii_detected,
            "elements_found": self.elements_found,
            "error": self.error,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

_TAG_RE = re.compile(r'\[([A-Z_|]+)\](.*?)\[/\1\]')


def _extract_elements(original: str, protected: str) -> List[Dict[str, Any]]:
    elements = []
    for m in re.finditer(r'\[([A-Z_|]+)\](.*?)\[/\1\]', protected):
        entity_type = m.group(1).split("|")[0]
        token_value = m.group(2)
        elements.append({"type": entity_type, "token": token_value})
        _token_map[token_value] = True
    if not elements and original != protected:
        elements.append({"type": "UNKNOWN", "note": "text was modified"})
    return elements


def _strip_pii_tags(text: str) -> str:
    return re.sub(r'\[([A-Z_|]+)\](.*?)\[/\1\]', r'\2', text)


# ── Discover-based fallback protection ────────────────────────────────────────
# Used when sdk.find_and_protect() returns unchanged text (dev-edition limitation)

_ENTITY_PRIORITY: Dict[str, int] = {
    "SOCIAL_SECURITY_ID": 10, "SOCIAL_SECURITY_NUMBER": 10,
    "CREDIT_CARD": 9, "CREDIT_CARD_NUMBER": 9,
    "EMAIL_ADDRESS": 8,
    "PHONE_NUMBER": 7,
    "PERSON": 6,
    "IP_ADDRESS": 5,
    "LOCATION": 4,
    "ORGANIZATION": 3,
    "URL": 1,   # lowest — frequently overlaps with email addresses
}
_SKIP_FALLBACK_TYPES = {"URL"}   # suppressed to reduce false positives
_FALLBACK_MIN_SCORE = 0.6


def _collect_spans(text: str, sdk) -> List[tuple]:
    """Non-overlapping (start, end, entity_type) PII spans found by discover()."""
    try:
        discovered = sdk.discover(text)
    except Exception as e:
        logger.warning("Discover failed: %s", e)
        return []

    spans: List[tuple] = []
    for entity_type, hits in discovered.items():
        if entity_type in _SKIP_FALLBACK_TYPES:
            continue
        priority = _ENTITY_PRIORITY.get(entity_type, 3)
        for hit in hits:
            score = hit.get("score", 0)
            if score < _FALLBACK_MIN_SCORE:
                continue
            loc = hit.get("location", {})
            start = loc.get("start_index")
            end = loc.get("end_index")
            if start is None or end is None or end <= start:
                continue
            # Reject spans that cut a word in half ("octocat" -> "octo"), which
            # would otherwise fragment identifiers like owner/repo.
            if start > 0 and (text[start - 1].isalnum() or text[start - 1] in "-_"):
                continue
            if end < len(text) and (text[end].isalnum() or text[end] in "-_"):
                continue
            if entity_type == "PERSON":
                start = _extend_name_start(text, start)
            spans.append((start, end, entity_type, priority, score))

    if not spans:
        return []

    # Remove overlapping spans — prefer highest priority, then highest score
    spans.sort(key=lambda x: (x[0], -x[3], -x[4]))
    filtered: List[tuple] = []
    for span in spans:
        s, e = span[0], span[1]
        if any(not (e <= fs or s >= fe) for fs, fe, *_ in filtered):
            continue
        filtered.append(span)
    return filtered


def _extend_name_start(text: str, start: int) -> int:
    """
    Pull a preceding capitalised word into a PERSON span.

    The classifier often returns only the surname ("Alex Johnson" -> "Johnson").
    A capital mid-sentence is a strong name signal; over-reaching only
    over-protects.
    """
    prefix = text[:start]
    m = re.search(rf"(?<=[a-z,]\s)({_NAME_WORD})\s+$", prefix)
    if m and m.group(1) not in _NAME_STOPWORDS:
        return m.start(1)
    return start


def find_pii_spans(text: str, cfg: Optional[Config] = None) -> List[Dict[str, Any]]:
    """
    PII spans with their original values, taken directly from *text*.

    Used where the caller must keep the real value (e.g. to restore it in an
    outbound tool call). Recovering it by detokenizing is unreliable — the SDK
    sometimes returns the token unchanged, which silently yields a fake value.
    """
    cfg = cfg or load_config()
    try:
        sdk = _configure_sdk(cfg)
    except Exception as e:
        logger.error("find_pii_spans error: %s", e)
        return []
    return [
        {"start": s, "end": e, "type": t, "value": text[s:e]}
        for s, e, t, _, _ in _collect_spans(text, sdk)
    ]


def _discover_and_protect_fallback(text: str, sdk) -> str:
    """
    Fallback: call sdk.discover() to locate PII entities by character position,
    then wrap each span in [TYPE]original_value[/TYPE] tags.
    Invoked when sdk.find_and_protect() returns unchanged text.
    """
    filtered = _collect_spans(text, sdk)
    if not filtered:
        return text

    # Replace from end → start so earlier indices stay valid
    filtered = sorted(filtered, key=lambda x: x[0], reverse=True)
    result = text
    for start, end, entity_type, _, _ in filtered:
        value = text[start:end]
        result = result[:start] + f"[{entity_type}]{value}[/{entity_type}]" + result[end:]

    return result


# The classifier often tags only part of a name ("Alex Johnson" -> "Johnson").
# Words capitalised mid-sentence next to a PERSON tag are pulled in as their own
# PERSON tags; a mid-sentence capital is a strong name signal and a false
# positive only over-protects.
_NAME_WORD = r"[A-Z][a-z]{1,20}"
_NAME_BEFORE_PERSON = re.compile(rf"(?<=[a-z,]\s)({_NAME_WORD})(\s+\[PERSON\])")
_NAME_AFTER_PERSON = re.compile(rf"(\[/PERSON\]\s+)({_NAME_WORD})(?=[\s,.;:)]|$)")
_NAME_STOPWORDS = {
    "The", "This", "That", "These", "Those", "There", "Then", "They", "Their",
    "And", "But", "For", "With", "From", "Please", "Contact", "Find", "Look",
    "Send", "Get", "Show", "List", "Fetch", "Update", "Create", "Delete",
    "Issue", "Repo", "Repository", "Email", "Phone", "Address", "Name",
}


def _tag_adjacent_name_words(text: str) -> str:
    """Absorb an adjacent capitalised word into its own PERSON tag."""
    if "[PERSON]" not in text:
        return text

    def _before(m: re.Match) -> str:
        word = m.group(1)
        if word in _NAME_STOPWORDS:
            return m.group(0)
        return f"[PERSON]{word}[/PERSON]{m.group(2)}"

    def _after(m: re.Match) -> str:
        word = m.group(2)
        if word in _NAME_STOPWORDS:
            return m.group(0)
        return f"{m.group(1)}[PERSON]{word}[/PERSON]"

    text = _NAME_BEFORE_PERSON.sub(_before, text)
    return _NAME_AFTER_PERSON.sub(_after, text)


# A tag butted against a letter or digit means the SDK split a word mid-way
# ("octocat" -> "[LOCATION]mWGk[/LOCATION]cat"), which corrupts identifiers.
_MIDWORD_TAG = re.compile(r"[A-Za-z0-9](?=\[[A-Z_|]+\])|\[/[A-Z_|]+\](?=[A-Za-z0-9])")


def _has_midword_tags(text: str) -> bool:
    return bool(_MIDWORD_TAG.search(text))


def _protect_lines(text: str, sdk) -> str:
    lines = text.split('\n')
    out = []
    for line in lines:
        stripped = line.rstrip()
        if stripped:
            try:
                result = sdk.find_and_protect(stripped)
                # Key the fallback off tags, not off "text changed": the SDK may
                # reformat a value (e.g. strip dashes from a card) without
                # tagging anything, which would otherwise suppress the fallback
                # for the whole line and leak every other entity on it.
                if (not isinstance(result, str) or not _TAG_RE.search(result)
                        or _has_midword_tags(result)):
                    result = _discover_and_protect_fallback(stripped, sdk)
                out.append(_tag_adjacent_name_words(result))
            except Exception as e:
                logger.warning("Line protect failed: %s", e)
                out.append(_tag_adjacent_name_words(
                    _discover_and_protect_fallback(stripped, sdk)))
        else:
            out.append(line)
    return '\n'.join(out)


# ── Public API ────────────────────────────────────────────────────────────────

def find_and_protect(text: str, cfg: Optional[Config] = None) -> ProtectResult:
    """Classify + tokenize all PII in *text*."""
    cfg = cfg or load_config()
    try:
        sdk = _configure_sdk(cfg)
        protected = _protect_lines(text, sdk)
        elements = _extract_elements(text, protected)
        return ProtectResult(original=text, protected=protected, elements_found=elements)
    except Exception as e:
        logger.error("find_and_protect error: %s", e)
        return ProtectResult(original=text, protected=text, error=str(e))


def find_and_unprotect(text: str, cfg: Optional[Config] = None) -> ProtectResult:
    """Detokenize all [TYPE]token[/TYPE] tags back to original values."""
    cfg = cfg or load_config()
    try:
        sdk = _configure_sdk(cfg)

        def _replace(match: re.Match) -> str:
            entity_type = match.group(1)
            token = match.group(2)
            tagged = match.group(0)
            # Heuristic: if it looks like a real name/value, skip unprotect
            if entity_type == "PERSON" and re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', token):
                return token
            try:
                result = sdk.find_and_unprotect(tagged)
                if isinstance(result, str) and result != tagged:
                    return _strip_pii_tags(result) if re.search(r'\[', result) else result
            except Exception as e:
                logger.warning("Token unprotect failed (%s): %s", entity_type, e)
            return token

        restored = re.sub(r'\[([A-Z_|]+)\](.*?)\[/\1\]', _replace, text)
        return ProtectResult(original=text, protected=restored)
    except Exception as e:
        logger.error("find_and_unprotect error: %s", e)
        return ProtectResult(original=text, protected=text, error=str(e))


def find_and_redact(text: str, cfg: Optional[Config] = None) -> ProtectResult:
    """Replace all [TYPE]token[/TYPE] with [REDACTED]."""
    redacted = re.sub(r'\[([A-Z_|]+)\](.*?)\[/\1\]', '[REDACTED]', text)
    return ProtectResult(original=text, protected=redacted)


def semantic_guardrail_check(text: str, cfg: Optional[Config] = None,
                              threshold: float = 0.7) -> Dict[str, Any]:
    """Call the Protegrity Semantic Guardrail. Returns risk metadata."""
    import requests
    cfg = cfg or load_config()
    # Processor 'pii' only allowed on from:ai messages (outbound content scan)
    payload = {
        "messages": [{"from": "ai", "to": "user", "content": text,
                       "processors": ["pii"]}]
    }
    try:
        resp = requests.post(cfg.sgr_url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        risk_score = 0.0
        outcome = "accepted"
        for msg in data.get("messages", []):
            risk_score = max(risk_score, float(msg.get("score", 0.0)))
            if msg.get("outcome") == "rejected":
                outcome = "rejected"
        if "batch" in data:
            risk_score = max(risk_score, float(data["batch"].get("score", 0.0)))
            if data["batch"].get("outcome") == "rejected":
                outcome = "rejected"
        accepted = outcome != "rejected" and risk_score <= threshold
        return {"risk_score": risk_score, "outcome": outcome,
                "accepted": accepted, "raw": data}
    except Exception as e:
        logger.warning("Semantic guardrail failed (continuing): %s", e)
        return {"risk_score": 0.0, "outcome": "accepted", "accepted": True,
                "error": str(e)}
