# Data Protection

Protect and unprotect data using tokenization and encryption via the Protegrity Protection APIs.

## Samples

### Python

- **`sample-app-protect-unprotect/`** — Jupyter notebook walkthrough for protect/unprotect operations.
- **`sample-app-protection.py`** — Standalone CLI script for direct protect, unprotect, encrypt, and decrypt operations.

### Java

- **`sample-app-protection.sh`** / **`sample-app-protection.bat`** — Shell/batch wrappers for the Java protection sample.
- Full Maven project with source under `src/`.

## Prerequisites

- Registered credentials for the AI Developer Edition API Service (see [main README](../README.md)).
- Environment variables `DEV_EDITION_EMAIL`, `DEV_EDITION_PASSWORD`, and `DEV_EDITION_API_KEY` exported.

## Quick Start

```bash
# Python — protect
python data-protection/samples/python/sample-app-protection.py --input_data "John Smith" --policy_user superuser --data_element name --protect

# Java — protect
bash data-protection/samples/java/sample-app-protection.sh --input_data "John Smith" --policy_user superuser --data_element name --protect
```
