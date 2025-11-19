from __future__ import annotations

from unittest import mock

from dev_edition_trial_center.trial_center_pipeline import (
    GuardrailConfig,
    TrialCenterPipeline,
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


@mock.patch("dev_edition_trial_center.trial_center_pipeline.protegrity.configure")
@mock.patch(
    "dev_edition_trial_center.trial_center_pipeline.protegrity.discover",
    return_value={"PERSON": []},
)
@mock.patch(
    "dev_edition_trial_center.trial_center_pipeline.protegrity.find_and_protect",
    side_effect=RuntimeError("protection unavailable"),
)
@mock.patch(
    "dev_edition_trial_center.trial_center_pipeline.protegrity.find_and_redact",
    return_value="[REDACTED]",
)
@mock.patch(
    "dev_edition_trial_center.trial_center_pipeline.requests.post",
    return_value=mock.Mock(
        raise_for_status=mock.Mock(),
        json=mock.Mock(return_value=_mock_guardrail_response()),
    ),
)
def test_trial_center_forge_falls_back_to_redaction(
    mock_post,
    mock_redact,
    mock_protect,
    mock_discover,
    mock_configure,
):
    pipeline = TrialCenterPipeline(
        guardrail_config=GuardrailConfig(rejection_threshold=0.6),
        sanitization_config=SanitizationConfig(method="protect"),
    )

    report = pipeline.process_prompt("Sensitive prompt with PII")

    assert report.guardrail.outcome == "accepted"
    assert report.sanitization.method_used == "redact"
    assert report.sanitization.sanitized_prompt == "[REDACTED]"
    assert report.sanitization.display_prompt == "[REDACTED]"
    mock_post.assert_called_once()
    mock_redact.assert_called_once()


@mock.patch("dev_edition_trial_center.trial_center_pipeline.protegrity.configure")
@mock.patch(
    "dev_edition_trial_center.trial_center_pipeline.protegrity.discover",
    return_value={},
)
@mock.patch(
    "dev_edition_trial_center.trial_center_pipeline.protegrity.find_and_redact",
    return_value="Sentence one. Sentence two.",
)
@mock.patch(
    "dev_edition_trial_center.trial_center_pipeline.requests.post",
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
    pipeline = TrialCenterPipeline(
        guardrail_config=GuardrailConfig(rejection_threshold=0.6),
        sanitization_config=SanitizationConfig(method="redact"),
    )

    report = pipeline.process_prompt("Sentence one. Sentence two.")

    assert report.guardrail.outcome == "accepted"
    assert report.sanitization.sanitized_prompt == "Sentence one. Sentence two."
    assert report.sanitization.display_prompt == "Sentence one. Sentence two."


@mock.patch("dev_edition_trial_center.trial_center_pipeline.protegrity.configure")
@mock.patch(
    "dev_edition_trial_center.trial_center_pipeline.protegrity.discover",
    return_value={},
)
@mock.patch(
    "dev_edition_trial_center.trial_center_pipeline.protegrity.find_and_redact",
    return_value="Sanitized",
)
@mock.patch(
    "dev_edition_trial_center.trial_center_pipeline.requests.post",
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
    pipeline = TrialCenterPipeline(
        guardrail_config=GuardrailConfig(rejection_threshold=0.3),
        sanitization_config=SanitizationConfig(method="redact"),
    )

    report = pipeline.process_prompt("Prompt")

    assert report.guardrail.outcome == "approved"
    assert report.sanitization.sanitized_prompt == "Sanitized"
    assert report.sanitization.display_prompt == "Sanitized"
