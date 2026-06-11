# Synthetic Data

Generate privacy-safe synthetic datasets that mimic production data without exposing sensitive information.

## Services

Start the synthetic data stack:

```bash
docker compose up -d
```

## Samples

### Python

- **`sample-app-synthetic-data/`** — Jupyter notebook walkthrough for synthetic data generation.

## Service Endpoint

- Synthetic Data API: `http://localhost:${SYN_PORT:-8095}/pty/syntheticdata/v2`
