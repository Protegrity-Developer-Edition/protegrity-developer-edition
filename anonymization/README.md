# Anonymization

Anonymize sensitive fields in datasets for privacy-preserving data processing.

## Services

Start the anonymization stack:

```bash
docker compose up -d
```

## Samples

### Python

- **`sample-app-anonymization/`** — Jupyter notebook walkthrough for anonymization.

## Service Endpoint

- Anonymization API: `http://localhost:${ANON_PORT:-8085}/pty/anonymization/v3`
