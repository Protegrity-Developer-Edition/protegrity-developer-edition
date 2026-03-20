"""
Comprehensive tests for Protegrity Developer Edition integration service.

Tests cover:
- Semantic guardrail checks (input validation)
- PII discovery (entity detection)
- Data protection (tokenization)
- Data unprotection (detokenization)
- Data redaction (masking)
- Full pipeline processing
- LLM response processing
- Error handling and edge cases
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import requests
from apps.core.protegrity_service import ProtegrityService, get_protegrity_service


@pytest.fixture
def protegrity_service():
    """Create a fresh ProtegrityService instance for testing."""
    return ProtegrityService()


@pytest.fixture
def mock_requests_post():
    """Mock requests.post for guardrails API calls."""
    with patch('apps.core.protegrity_service.requests.post') as mock:
        yield mock


@pytest.fixture
def mock_protegrity_discover():
    """Mock protegrity.discover for PII detection."""
    with patch('apps.core.protegrity_service.protegrity.discover') as mock:
        yield mock


@pytest.fixture
def mock_protegrity_protect():
    """Mock protegrity.find_and_protect for tokenization."""
    with patch('apps.core.protegrity_service.protegrity.find_and_protect') as mock:
        yield mock


@pytest.fixture
def mock_protegrity_unprotect():
    """Mock protegrity.find_and_unprotect for detokenization."""
    with patch('apps.core.protegrity_service.protegrity.find_and_unprotect') as mock:
        yield mock


@pytest.fixture
def mock_protegrity_redact():
    """Mock protegrity.find_and_redact for masking."""
    with patch('apps.core.protegrity_service.protegrity.find_and_redact') as mock:
        yield mock


class TestGuardrailChecks:
    """Test semantic guardrail validation."""
    
    def test_check_guardrails_accepted(self, protegrity_service, mock_requests_post):
        """Test that safe prompts are accepted."""
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = {
            "messages": [
                {"score": 0.1, "content": "test"}
            ]
        }
        
        result = protegrity_service.check_guardrails("What is Python?")
        
        assert result["outcome"] == "accepted"
        assert result["risk_score"] == 0.1
        assert result["risk_score"] < 0.7
        mock_requests_post.assert_called_once()
    
    def test_check_guardrails_rejected_high_risk(self, protegrity_service, mock_requests_post):
        """Test that high-risk prompts are rejected."""
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = {
            "messages": [
                {"score": 0.95, "content": "dangerous prompt"}
            ]
        }
        
        result = protegrity_service.check_guardrails("Dangerous prompt")
        
        assert result["outcome"] == "rejected"
        assert result["risk_score"] == 0.95
        assert result["risk_score"] > 0.7
    
    def test_check_guardrails_api_error(self, protegrity_service, mock_requests_post):
        """Test handling of API errors."""
        mock_requests_post.return_value.status_code = 500
        mock_requests_post.return_value.text = "Internal server error"
        
        result = protegrity_service.check_guardrails("Test")
        
        assert result["outcome"] == "error"
        assert result["risk_score"] == 0.0
        assert "error" in result["details"]
    
    def test_check_guardrails_network_error(self, protegrity_service, mock_requests_post):
        """Test handling of network errors."""
        mock_requests_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        result = protegrity_service.check_guardrails("Test")
        
        assert result["outcome"] == "error"
        assert result["risk_score"] == 0.0
        assert "error" in result["details"]
    
    def test_check_guardrails_empty_messages(self, protegrity_service, mock_requests_post):
        """Test handling when API returns empty messages array."""
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = {
            "messages": []
        }
        
        result = protegrity_service.check_guardrails("Test")
        
        assert result["outcome"] == "accepted"
        assert result["risk_score"] == 0.0


class TestPIIDiscovery:
    """Test PII entity discovery."""
    
    def test_discover_entities_with_pii(self, protegrity_service, mock_protegrity_discover):
        """Test discovering PII entities in text."""
        mock_protegrity_discover.return_value = {
            "EMAIL": [{
                "score": 0.99,
                "start_index": 10,
                "end_index": 30,
                "entity_text": "john@example.com"
            }],
            "PHONE": [{
                "score": 0.95,
                "start_index": 50,
                "end_index": 62,
                "entity_text": "555-123-4567"
            }]
        }
        
        result = protegrity_service.discover_entities("Contact john@example.com or call 555-123-4567")
        
        assert "EMAIL" in result
        assert "PHONE" in result
        assert len(result["EMAIL"]) == 1
        assert result["EMAIL"][0]["entity_text"] == "john@example.com"
        mock_protegrity_discover.assert_called_once()
    
    def test_discover_entities_no_pii(self, protegrity_service, mock_protegrity_discover):
        """Test text with no PII."""
        mock_protegrity_discover.return_value = {}
        
        result = protegrity_service.discover_entities("Hello world")
        
        assert result == {}
        mock_protegrity_discover.assert_called_once()
    
    def test_discover_entities_error(self, protegrity_service, mock_protegrity_discover):
        """Test error handling in discovery."""
        mock_protegrity_discover.side_effect = Exception("Discovery failed")
        
        result = protegrity_service.discover_entities("Test")
        
        assert result == {}


class TestDataProtection:
    """Test data tokenization/protection."""
    
    def test_protect_data_success(self, protegrity_service, mock_protegrity_protect):
        """Test successful data protection."""
        mock_protegrity_protect.return_value = "Contact [TOKEN_1] or call [TOKEN_2]"
        
        protected_text, metadata = protegrity_service.protect_data("Contact john@example.com or call 555-123-4567")
        
        assert protected_text == "Contact [TOKEN_1] or call [TOKEN_2]"
        assert metadata["success"] is True
        assert metadata["method"] == "tokenization"
        mock_protegrity_protect.assert_called_once()
    
    def test_protect_data_error(self, protegrity_service, mock_protegrity_protect):
        """Test error handling in protection."""
        mock_protegrity_protect.side_effect = Exception("Protection failed")
        
        protected_text, metadata = protegrity_service.protect_data("Test")
        
        assert protected_text is None
        assert metadata["success"] is False
        assert "error" in metadata


class TestDataUnprotection:
    """Test data detokenization/unprotection."""
    
    def test_unprotect_data_success(self, protegrity_service, mock_protegrity_unprotect):
        """Test successful data unprotection."""
        mock_protegrity_unprotect.return_value = "Contact john@example.com or call 555-123-4567"
        
        unprotected_text, metadata = protegrity_service.unprotect_data("Contact [TOKEN_1] or call [TOKEN_2]")
        
        assert unprotected_text == "Contact john@example.com or call 555-123-4567"
        assert metadata["success"] is True
        mock_protegrity_unprotect.assert_called_once()
    
    def test_unprotect_data_error(self, protegrity_service, mock_protegrity_unprotect):
        """Test error handling in unprotection."""
        mock_protegrity_unprotect.side_effect = Exception("Unprotection failed")
        
        unprotected_text, metadata = protegrity_service.unprotect_data("Test")
        
        assert unprotected_text is None
        assert metadata["success"] is False
        assert "error" in metadata


class TestDataRedaction:
    """Test data redaction/masking."""
    
    def test_redact_data_success(self, protegrity_service, mock_protegrity_redact):
        """Test successful data redaction."""
        mock_protegrity_redact.return_value = "Contact [EMAIL] or call [PHONE]"
        
        redacted_text, metadata = protegrity_service.redact_data("Contact john@example.com or call 555-123-4567")
        
        assert redacted_text == "Contact [EMAIL] or call [PHONE]"
        assert metadata["success"] is True
        assert metadata["method"] == "redact"
        mock_protegrity_redact.assert_called_once()
    
    def test_redact_data_error(self, protegrity_service, mock_protegrity_redact):
        """Test error handling in redaction - returns original text."""
        original_text = "Contact john@example.com"
        mock_protegrity_redact.side_effect = Exception("Redaction failed")
        
        redacted_text, metadata = protegrity_service.redact_data(original_text)
        
        assert redacted_text == original_text  # Original text returned on error
        assert metadata["success"] is False
        assert "error" in metadata


class TestFullPipeline:
    """Test the complete Protegrity processing pipeline."""
    
    def test_full_pipeline_redact_mode_accepted(
        self, protegrity_service, mock_requests_post, mock_protegrity_discover, mock_protegrity_redact
    ):
        """Test full pipeline in redact mode with accepted prompt."""
        # Mock guardrails - accepted
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = {
            "messages": [{"score": 0.2}]
        }
        
        # Mock discovery
        mock_protegrity_discover.return_value = {
            "EMAIL": [{"entity_text": "john@example.com"}]
        }
        
        # Mock redaction
        mock_protegrity_redact.return_value = "Email: [EMAIL]"
        
        result = protegrity_service.process_full_pipeline("Email: john@example.com", mode="redact")
        
        assert result["original_text"] == "Email: john@example.com"
        assert result["processed_text"] == "Email: [EMAIL]"
        assert result["should_block"] is False
        assert result["guardrails"]["outcome"] == "accepted"
        assert "EMAIL" in result["discovery"]
        assert result["redaction"]["success"] is True
        assert result["mode"] == "redact"
    
    def test_full_pipeline_protect_mode(
        self, protegrity_service, mock_requests_post, mock_protegrity_discover, mock_protegrity_protect
    ):
        """Test full pipeline in protect mode."""
        # Mock guardrails - accepted
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = {
            "messages": [{"score": 0.1}]
        }
        
        # Mock discovery
        mock_protegrity_discover.return_value = {
            "SSN": [{"entity_text": "123-45-6789"}]
        }
        
        # Mock protection
        mock_protegrity_protect.return_value = "SSN: [TOKEN_SSN]"
        
        result = protegrity_service.process_full_pipeline("SSN: 123-45-6789", mode="protect")
        
        assert result["original_text"] == "SSN: 123-45-6789"
        assert result["processed_text"] == "SSN: [TOKEN_SSN]"
        assert result["should_block"] is False
        assert result["protection"]["success"] is True
        assert result["mode"] == "protect"
    
    def test_full_pipeline_blocked_by_guardrails(
        self, protegrity_service, mock_requests_post, mock_protegrity_discover
    ):
        """Test that high-risk prompts are blocked before processing."""
        # Mock guardrails - rejected
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = {
            "messages": [{"score": 0.95}]
        }
        
        result = protegrity_service.process_full_pipeline("Dangerous prompt", mode="redact")
        
        assert result["should_block"] is True
        assert result["processed_text"] is None
        assert result["guardrails"]["outcome"] == "rejected"
        # Discovery should not be called if blocked
        mock_protegrity_discover.assert_not_called()


class TestLLMResponseProcessing:
    """Test processing of LLM responses."""
    
    def test_process_llm_response_clean(
        self, protegrity_service, mock_requests_post, mock_protegrity_discover, mock_protegrity_redact
    ):
        """Test processing clean LLM response."""
        # Mock guardrails - accepted
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = {
            "messages": [{"score": 0.1}]
        }
        
        # Mock discovery - no PII
        mock_protegrity_discover.return_value = {}
        
        # Mock redaction - no changes
        original_response = "Python is a programming language."
        mock_protegrity_redact.return_value = original_response
        
        result = protegrity_service.process_llm_response(original_response)
        
        assert result["original_response"] == original_response
        assert result["processed_response"] == original_response
        assert result["should_filter"] is False
        assert result["guardrails"]["outcome"] == "accepted"
    
    def test_process_llm_response_with_leaked_pii(
        self, protegrity_service, mock_requests_post, mock_protegrity_discover, mock_protegrity_redact
    ):
        """Test LLM response that leaked PII."""
        # Mock guardrails - accepted
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = {
            "messages": [{"score": 0.3}]
        }
        
        # Mock discovery - found PII
        mock_protegrity_discover.return_value = {
            "EMAIL": [{"entity_text": "leaked@email.com"}]
        }
        
        # Mock redaction
        mock_protegrity_redact.return_value = "The email is [EMAIL]"
        
        result = protegrity_service.process_llm_response("The email is leaked@email.com")
        
        assert result["original_response"] == "The email is leaked@email.com"
        assert result["processed_response"] == "The email is [EMAIL]"
        assert result["should_filter"] is False
        assert "EMAIL" in result["discovery"]
    
    def test_process_llm_response_rejected_by_guardrails(
        self, protegrity_service, mock_requests_post, mock_protegrity_discover, mock_protegrity_redact
    ):
        """Test LLM response rejected by guardrails."""
        # Mock guardrails - rejected
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = {
            "messages": [{"score": 0.85}]
        }
        
        # Mock discovery and redaction
        mock_protegrity_discover.return_value = {}
        mock_protegrity_redact.return_value = "Harmful content"
        
        result = protegrity_service.process_llm_response("Harmful content")
        
        assert result["should_filter"] is True
        assert result["guardrails"]["outcome"] == "rejected"


class TestServiceSingleton:
    """Test the singleton pattern for ProtegrityService."""
    
    def test_get_protegrity_service_singleton(self):
        """Test that get_protegrity_service returns the same instance."""
        service1 = get_protegrity_service()
        service2 = get_protegrity_service()
        
        assert service1 is service2
        assert isinstance(service1, ProtegrityService)
