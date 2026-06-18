from __future__ import annotations

from unittest import mock

from trial_center.core.pipeline import (
    GuardianPromptForge,
    GuardrailConfig,
    SanitizationConfig,
)


def _mock_guardrail_response(score: float = 0.7, outcome: str = "accepted"):
    return {
        "messages": [
            {
                "id": "1",
                "outcome": outcome,
                "score": score,
                "processors": [
                    {"name": "semantic", "score": score, "explanation": "sensitive"}
                ],
            }
        ]
    }


@mock.patch("trial_center.core.pipeline.protegrity.configure")
@mock.patch(
    "trial_center.core.pipeline.protegrity.discover",
    return_value={"PERSON": []},
)
@mock.patch(
    "trial_center.core.pipeline.protegrity.find_and_protect",
    side_effect=RuntimeError("protection unavailable"),
)
@mock.patch(
    "trial_center.core.pipeline.protegrity.find_and_redact",
    return_value="[REDACTED]",
)
@mock.patch(
    "trial_center.core.pipeline.requests.post",
    return_value=mock.Mock(
        raise_for_status=mock.Mock(),
        json=mock.Mock(return_value=_mock_guardrail_response()),
    ),
)
def test_trial_center_forge_reports_protection_failure(
    mock_post,
    mock_redact,
    mock_protect,
    mock_discover,
    mock_configure,
):
    forge = GuardianPromptForge(
        guardrail_config=GuardrailConfig(rejection_threshold=0.6),
        sanitization_config=SanitizationConfig(method="protect"),
    )

    report = forge.process_prompt("Sensitive prompt with PII")

    assert report.guardrail.outcome == "accepted"
    assert report.sanitization.method_used == "protect"
    assert report.sanitization.sanitize_error == "protection unavailable"
    assert report.sanitization.sanitized_prompt == "Sensitive prompt with PII"  # Returns original on error
    mock_post.assert_called_once()
    mock_protect.assert_called_once()
    mock_redact.assert_not_called()


@mock.patch("trial_center.core.pipeline.protegrity.configure")
@mock.patch(
    "trial_center.core.pipeline.protegrity.discover",
    return_value={},
)
@mock.patch(
    "trial_center.core.pipeline.protegrity.find_and_redact",
    return_value="Sentence one. Sentence two.",
)
@mock.patch(
    "trial_center.core.pipeline.requests.post",
    return_value=mock.Mock(
        raise_for_status=mock.Mock(),
        json=mock.Mock(return_value=_mock_guardrail_response(score=0.2)),
    ),
)
def test_trial_center_forge_accepts_low_risk_prompt(
    mock_post,
    mock_redact,
    mock_discover,
    mock_configure,
):
    forge = GuardianPromptForge(
        guardrail_config=GuardrailConfig(rejection_threshold=0.6),
        sanitization_config=SanitizationConfig(method="redact"),
    )

    report = forge.process_prompt("Sentence one. Sentence two.")

    assert report.guardrail.outcome == "accepted"
    assert report.sanitization.sanitized_prompt == "Sentence one. Sentence two."
    assert report.sanitization.display_prompt == "Sentence one. Sentence two."


@mock.patch("trial_center.core.pipeline.protegrity.configure")
@mock.patch(
    "trial_center.core.pipeline.protegrity.discover",
    return_value={},
)
@mock.patch(
    "trial_center.core.pipeline.protegrity.find_and_redact",
    return_value="Sanitized",
)
@mock.patch(
    "trial_center.core.pipeline.requests.post",
    return_value=mock.Mock(
        raise_for_status=mock.Mock(),
        json=mock.Mock(return_value=_mock_guardrail_response(score=0.49, outcome="approved")),
    ),
)
def test_trial_center_forge_preserves_service_outcome(
    mock_post,
    mock_redact,
    mock_discover,
    mock_configure,
):
    forge = GuardianPromptForge(
        guardrail_config=GuardrailConfig(rejection_threshold=0.3),
        sanitization_config=SanitizationConfig(method="redact"),
    )

    report = forge.process_prompt("Prompt")

    assert report.guardrail.outcome == "approved"
    assert report.sanitization.sanitized_prompt == "Sanitized"
    assert report.sanitization.display_prompt == "Sanitized"
