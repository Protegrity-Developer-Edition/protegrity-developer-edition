# Semantic Guardrail

Secure GenAI applications using message-level risk scoring, conversation-level risk scoring, and PII scanning.

## Services

Start the semantic guardrail stack (includes classification dependencies):

```bash
cd ../data-discovery
docker compose up -d

cd ../semantic-guardrail
docker compose up -d
```

## Samples

### Python

- **`sample-guardrail-python.py`** — Multi-turn conversation with semantic risk and PII processing.
- **`sample-app-semantic-guardrails/`** — Jupyter notebook walkthrough.

### Bash

- **`sample-guardrail-command.sh`** — curl-based guardrail examples.

## Service Endpoint

- Semantic Guardrail API: `http://localhost:${SGR_PORT:-8581}/pty/semantic-guardrail/v1.1/conversations/messages/scan`
