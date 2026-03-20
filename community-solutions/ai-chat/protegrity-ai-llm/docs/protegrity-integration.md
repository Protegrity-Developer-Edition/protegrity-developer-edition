# Protegrity Integration

## What is protected

Both sides of the chat flow are protected:

- **Input protection:** user prompts are checked for policy risk and sensitive entities before LLM submission.
- **Output protection:** model responses are checked before being shown to users.

## Pipeline

1. Guardrails check (policy/risk)
2. Sensitive data discovery
3. Redaction or protection step
4. Safe text continues through the flow

If a guardrail check fails, the message/response is blocked and the user receives a safe fallback message.

## Key backend files

- `app/backend/apps/core/protegrity_service.py`
- `app/backend/apps/core/orchestrator.py`
- `app/backend/apps/core/views.py`

## Modes

- `redact`: replace detected sensitive values with labels.
- `protect`: tokenize values (when configured).
- `none`: bypass processing (debug/testing only).

## Environment variables (backend)

Set these in `app/backend/.env`:

- `PROTEGRITY_API_URL`
- `DEV_EDITION_EMAIL`
- `DEV_EDITION_PASSWORD`
- `DEV_EDITION_API_KEY`

## Quick verification

1. Start services with `app/run.sh`.
2. Send a synthetic prompt containing fake PII.
3. Confirm the response and analysis show sanitized content.
4. Try a policy-violating prompt and confirm blocked behavior.
