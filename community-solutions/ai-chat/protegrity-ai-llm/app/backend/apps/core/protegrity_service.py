# backend/apps/core/protegrity_service.py
"""
Protegrity Developer Edition Integration Service

Integrates with Protegrity Developer Edition REST APIs to provide:
- Semantic guardrails (prompt validation)
- PII discovery (entity detection)
- Data redaction (masking)

Based on: Direct REST API calls to Protegrity Developer Edition services
"""

import os
import requests
import logging
from typing import Dict, List, Any, Optional, Tuple
import re

logger = logging.getLogger(__name__)


class ProtegrityService:
    """
    Service class for interacting with Protegrity Developer Edition REST APIs.
    """
    
    def __init__(self):
        self.email = os.getenv("DEV_EDITION_EMAIL", "")
        self.password = os.getenv("DEV_EDITION_PASSWORD", "")
        self.api_key = os.getenv("DEV_EDITION_API_KEY", "")
        
        # Data Discovery API configuration
        self.classification_url = "http://localhost:8580/pty/data-discovery/v1.1/classify"
        self.classification_threshold_input = self._get_float_env(
            "PROTEGRITY_CLASSIFICATION_THRESHOLD_INPUT",
            "PROTEGRITY_CLASSIFICATION_THRESHOLD",
            default=0.6,
        )
        self.classification_threshold_output = self._get_float_env(
            "PROTEGRITY_CLASSIFICATION_THRESHOLD_OUTPUT",
            "PROTEGRITY_CLASSIFICATION_THRESHOLD",
            default=0.6,
        )
        
        # Semantic Guardrail configuration
        self.guardrails_url = "http://localhost:8581/pty/semantic-guardrail/v1.1/conversations/messages/scan"
        self.guardrail_threshold_input = self._get_float_env(
            "PROTEGRITY_GUARDRAIL_THRESHOLD_INPUT",
            "PROTEGRITY_GUARDRAIL_THRESHOLD",
            default=0.8,
        )
        self.guardrail_threshold_output = self._get_float_env(
            "PROTEGRITY_GUARDRAIL_THRESHOLD_OUTPUT",
            "PROTEGRITY_GUARDRAIL_THRESHOLD",
            default=0.8,
        )
        
        # Entity mappings for redaction
        self.entity_map = {
            "US_SSN": "SSN",
            "SOCIAL_SECURITY_NUMBER": "SSN",
            "EMAIL_ADDRESS": "EMAIL",
            "PHONE_NUMBER": "PHONE",
            "CREDIT_CARD": "CREDIT_CARD",
            "PERSON": "PERSON",
            "US_DRIVER_LICENSE": "DRIVER_LICENSE",
            "US_PASSPORT": "PASSPORT",
            "IP_ADDRESS": "IP_ADDRESS",
            "IBAN_CODE": "IBAN",
            "MEDICAL_LICENSE": "MEDICAL_LICENSE",
            "DATE_TIME": "DATE",
            "LOCATION": "LOCATION",
            "CITY": "CITY",
            "STATE": "STATE",
            "AGE": "AGE",
            "USERNAME": "USERNAME"
        }
        
        self.masking_char = "#"

    def _get_float_env(self, primary_name: str, legacy_name: str, default: float) -> float:
        """Read a float from env with legacy fallback and safe default."""
        raw = os.getenv(primary_name)
        source_name = primary_name
        if raw is None or raw == "":
            raw = os.getenv(legacy_name)
            source_name = legacy_name

        if raw is None or raw == "":
            return default

        try:
            return float(raw)
        except (TypeError, ValueError):
            logger.warning(
                "Invalid float value for %s=%r. Falling back to default %s",
                source_name,
                raw,
                default,
            )
            return default
    
    def check_guardrails(self, text: str, message_direction: str = "user_to_ai") -> Dict[str, Any]:
        """
        Step 1: Check semantic guardrails for policy violations.
        
        Uses Semantic Guardrail REST API to analyze message risk.
        
        Args:
            text: The prompt text to evaluate
            message_direction: Either "user_to_ai" for user input or "ai_to_user" for AI responses
            
        Returns:
            {
                "outcome": "accepted" | "rejected",
                "risk_score": float (0.0 to 1.0),
                "policy_signals": ["signal1", "signal2"],
                "details": {...}
            }
        """
        try:
            # Configure message based on direction
            if message_direction == "user_to_ai":
                message = {
                    "from": "user",
                    "to": "ai",
                    "content": text,
                    "processors": ["customer-support"]
                }
            else:  # ai_to_user
                message = {
                    "from": "ai",
                    "to": "user",
                    "content": text,
                    "processors": ["pii"]
                }
            
            data = {"messages": [message]}
            
            response = requests.post(
                self.guardrails_url,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract message-level score
                message_risk = 0.0
                if "messages" in result and len(result["messages"]) > 0:
                    message_risk = result["messages"][0].get("score", 0.0)
                
                risk_threshold = (
                    self.guardrail_threshold_input
                    if message_direction == "user_to_ai"
                    else self.guardrail_threshold_output
                )

                # Determine outcome based on direction-specific risk threshold (configurable via env var)
                outcome = "rejected" if message_risk > risk_threshold else "accepted"
                
                return {
                    "outcome": outcome,
                    "risk_score": message_risk,
                    "threshold": risk_threshold,
                    "policy_signals": [],  # Can extract from semantic analysis
                    "details": result
                }
            else:
                logger.error(f"Guardrails check failed: {response.status_code} - {response.text}")
                return {
                    "outcome": "error",
                    "risk_score": 0.0,
                    "policy_signals": [],
                    "details": {"error": response.text}
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Guardrails API error: {str(e)}")
            return {
                "outcome": "error",
                "risk_score": 0.0,
                "policy_signals": [],
                "details": {"error": str(e)}
            }
    
    def discover_entities(self, text: str, score_threshold: Optional[float] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Step 2: Discover PII and sensitive entities in the text.
        
        Uses Protegrity Data Discovery REST API.
        
        Args:
            text: The text to analyze
            
        Returns:
            {
                "EMAIL": [{
                    "score": 0.99,
                    "start_index": 10,
                    "end_index": 30,
                    "entity_text": "john@example.com"
                }],
                "SSN": [...],
                ...
            }
        """
        try:
            headers = {"Content-Type": "text/plain"}
            threshold = self.classification_threshold_input if score_threshold is None else score_threshold
            params = {"score_threshold": threshold}
            
            response = requests.post(
                self.classification_url,
                headers=headers,
                data=text,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                classifications = result.get("classifications", {})
                
                # Transform to match expected format
                transformed = {}
                for entity_type, detections in classifications.items():
                    mapped_type = self.entity_map.get(entity_type, entity_type)
                    transformed[mapped_type] = [
                        {
                            "score": det["score"],
                            "location": {
                                "start_index": det["location"]["start_index"],
                                "end_index": det["location"]["end_index"]
                            },
                            "entity_text": text[det["location"]["start_index"]:det["location"]["end_index"]]
                        }
                        for det in detections
                    ]
                
                return transformed
            else:
                logger.error(f"Discovery API error: {response.status_code} - {response.text}")
                return {}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Discovery API error: {str(e)}")
            return {}
    
    def protect_data(self, text: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Step 3: Protect sensitive data through tokenization.
        
        NOTE: Tokenization requires Protegrity enterprise platform.
        For Developer Edition, use redaction instead.
        
        Args:
            text: The text to protect
            
        Returns:
            (protected_text, metadata)
            protected_text: Text with tokens replacing sensitive values
            metadata: Protection details and token mappings
        """
        logger.warning("Tokenization not available in Developer Edition. Using redaction instead.")
        return self.redact_data(text)
    
    def redact_data(self, text: str, score_threshold: Optional[float] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Step 5: Redact sensitive data by replacing with entity labels.
        
        First discovers entities using REST API, then applies redactions.
        
        Args:
            text: The text to redact
            
        Returns:
            (redacted_text, metadata)
            redacted_text: Text with [ENTITY_TYPE] labels replacing sensitive values
            metadata: Redaction details
        """
        try:
            # Discover entities first
            entities = self.discover_entities(text, score_threshold=score_threshold)
            
            if not entities:
                return text, {"success": True, "method": "redact", "entities_found": 0}
            
            # Build list of all replacements with their positions
            replacements = []
            total_entities = 0
            
            for entity_type, detections in entities.items():
                for detection in detections:
                    replacements.append({
                        "start": detection["location"]["start_index"],
                        "end": detection["location"]["end_index"],
                        "type": entity_type,
                        "original": detection["entity_text"]
                    })
                    total_entities += 1
            
            # Sort by start position (reverse order so we don't mess up indices)
            replacements.sort(key=lambda x: x["start"], reverse=True)
            
            # Apply redactions
            redacted_text = text
            for replacement in replacements:
                redacted_value = f"[{replacement['type']}]"
                redacted_text = (
                    redacted_text[:replacement["start"]] +
                    redacted_value +
                    redacted_text[replacement["end"]:]
                )
            
            return redacted_text, {
                "success": True,
                "method": "redact",
                "entities_found": total_entities,
                "entities": entities
            }
            
        except Exception as e:
            logger.error(f"Redaction API error: {str(e)}")
            return text, {"error": str(e), "success": False}
    
    def process_full_pipeline(self, text: str, mode: str = "redact") -> Dict[str, Any]:
        """
        Execute the full Protegrity pipeline on input text.
        
        Args:
            text: The text to process
            mode: "redact" | "protect" - determines which method to use for LLM
            
        Returns:
            {
                "original_text": "...",
                "processed_text": "...",  # Text to send to LLM
                "guardrails": {...},
                "discovery": {...},
                "protection": {...},
                "redaction": {...},
                "should_block": bool
            }
        """
        result = {
            "original_text": text,
            "processed_text": text,
            "should_block": False,
            "guardrails": {},
            "discovery": {},
            "protection": {},
            "redaction": {},
            "mode": mode
        }
        
        # Step 1: Check guardrails
        logger.info("Step 1: Checking guardrails...")
        guardrails = self.check_guardrails(text)
        result["guardrails"] = guardrails
        
        if guardrails.get("outcome") == "rejected":
            result["should_block"] = True
            result["processed_text"] = None
            logger.warning(f"Guardrails rejected prompt. Risk score: {guardrails.get('risk_score')}")
            return result
        
        # Step 2: Discover entities
        logger.info("Step 2: Discovering entities...")
        discovery = self.discover_entities(text, score_threshold=self.classification_threshold_input)
        result["discovery"] = discovery
        
        # Step 3 & 5: Process based on mode
        if mode == "protect":
            logger.info("Step 3: Protecting data...")
            protected_text, protection_meta = self.protect_data(text)
            result["protection"] = protection_meta
            if protected_text:
                result["processed_text"] = protected_text
        elif mode == "redact":
            logger.info("Step 5: Redacting data...")
            redacted_text, redaction_meta = self.redact_data(
                text,
                score_threshold=self.classification_threshold_input,
            )
            result["redaction"] = redaction_meta
            result["processed_text"] = redacted_text
        
        return result
    
    def process_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Process LLM response through Protegrity pipeline.
        
        This checks the response for:
        - Guardrail violations (data leakage, harmful content)
        - Unexpected PII in output
        - Applies same protections/redactions
        
        Args:
            response_text: The LLM's response
            
        Returns:
            {
                "original_response": "...",
                "processed_response": "...",
                "guardrails": {...},
                "discovery": {...},
                "redaction": {...},
                "should_filter": bool
            }
        """
        result = {
            "original_response": response_text,
            "processed_response": response_text,
            "should_filter": False,
            "guardrails": {},
            "discovery": {},
            "redaction": {}
        }
        
        # Check response guardrails
        guardrails = self.check_guardrails(response_text, message_direction="ai_to_user")
        result["guardrails"] = guardrails
        
        if guardrails.get("outcome") == "rejected":
            result["should_filter"] = True
            logger.warning("LLM response rejected by guardrails")
        
        # Discover entities in response
        discovery = self.discover_entities(
            response_text,
            score_threshold=self.classification_threshold_output,
        )
        result["discovery"] = discovery
        
        # Redact any PII that leaked into response
        redacted_response, redaction_meta = self.redact_data(
            response_text,
            score_threshold=self.classification_threshold_output,
        )
        result["redaction"] = redaction_meta
        result["processed_response"] = redacted_response
        
        return result


# Singleton instance
_protegrity_service = None

def get_protegrity_service() -> ProtegrityService:
    """Get or create the Protegrity service singleton."""
    global _protegrity_service
    if _protegrity_service is None:
        _protegrity_service = ProtegrityService()
    return _protegrity_service
