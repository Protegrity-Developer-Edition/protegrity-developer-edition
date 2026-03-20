# Protegrity AI (LLM)
## What this example does

This example provides a secure, full-stack LLM chatbot that scans user prompts and model responses for sensitive data, applies guardrail checks, and enforces privacy controls before content is returned to users.

## Demo video

Here is the fastest way to understand the app flow before you run it locally:

- https://www.youtube.com/watch?v=DcSQH0ZOf3E

## Quickstart (3 steps)

1. **Set environment file**
	```bash
	cp app/backend/.env.example app/backend/.env
	```
	Then fill provider credentials in `app/backend/.env`.

2. **Run the app**
	```bash
	cd app
	./run.sh
	```

3. **Open and try it**
	- Frontend: http://localhost:5173
	- Backend: http://127.0.0.1:8000
	- Send a normal prompt, then a fake-PII prompt, then a policy-violating prompt.

## Expected result

- Normal prompt: assistant responds normally.
- Fake PII prompt: sensitive values are sanitized/redacted in processing.
- Policy-violating prompt: content is blocked or safely handled by guardrails.

## Use case

Developer and platform teams need a production-style reference for building GenAI chat experiences that protect sensitive data while keeping app setup fast and repeatable.

## What it demonstrates

- Industry-first sample packaging under `community-solutions/ai-chat`.
- Protegrity data discovery and redaction integrated in chat workflow.
- Semantic guardrails applied before and after LLM interaction.
- Provider-agnostic LLM configuration through environment variables (Azure OpenAI, OpenAI, Anthropic, Bedrock).

## Features showcased

- data-discovery
- pii-redaction
- tokenization
- semantic-guardrails
- auditing-logging

## Products/components used

- Protegrity AI Developer Edition
- Django backend service
- React frontend console

## Architecture

- Frontend sends chat prompts to backend endpoints.
- Backend classifies sensitive content and applies guardrail policy.
- Backend invokes configured LLM provider for approved prompts.
- Response is scanned/redacted as needed before returning to user.

Diagram and implementation docs:

- `docs/architecture.md`
- `docs/protegrity-integration.md`

## Getting started

### Prereqs

- Docker + Docker Compose
- Python 3.12+
- Node.js 20+ (for local frontend workflow)

### Setup (env vars)

From this folder (`community-solutions/ai-chat/protegrity-ai-llm`):

```bash
cp app/backend/.env.example app/backend/.env
```

Then fill provider credentials in `app/backend/.env`.

### Run (docker/local)

```bash
cd app
./run.sh
```

Open:

- Frontend: http://localhost:5173
- Backend: http://127.0.0.1:8000

## Try it

- Ask a normal customer-support style question.
- Send a fake-PII prompt and verify sanitized behavior.
- Ask for restricted/off-topic content and verify guardrail handling.
- Ask a follow-up question to test multi-turn continuity.

## Security & privacy notes

- Use synthetic/demo prompts only.
- Do not commit `app/backend/.env`.
- Keep provider keys and Protegrity credentials in env vars only.
- Review backend logs before sharing outputs externally.

## Troubleshooting

- Ensure Protegrity services are up (`docker compose up -d` at repo root).
- Confirm at least one LLM provider is fully configured in `app/backend/.env`.
- If startup fails, rerun from `app/` and inspect `run.sh` output.

## Next steps / extensions

- Add screenshots under `docs/screenshots/`.
- Add synthetic datasets under `data/`.
- Add infra deployment assets under `infra/` as needed.

## License

See the repository root `LICENSE` file.
