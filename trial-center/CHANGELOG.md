# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-06-19

### Changed

- **Upstream alignment**: bumped to track
  [Protegrity AI Developer Edition v1.2.0](https://github.com/Protegrity-AI-Developer-Edition/protegrity-ai-developer-edition/tree/pre-release-1.2.0).
- **Data Discovery API**: migrated from `POST /pty/data-discovery/v1.1/classify`
  (JSON body) to the v2 contract:
  - Discovery: `POST /pty/data-discovery/v2/classify/text` (raw `text/plain`)
  - Redaction: `POST /pty/data-discovery/v2/transform/label` (raw `text/plain`)
- **SDK package**: switched from `protegrity-developer-python>=1.1.1`
  (Python 3.12.11+) to `protegrity-ai-developer-python>=1.2.0` (Python 3.10+).
  The Python import name (`protegrity_developer_python`) is unchanged.
- **Entity normalization**: added `SOCIAL_SECURITY_ID` → `SSN` mapping
  (legacy `SOCIAL_SECURITY_NUMBER` retained for backward compat).
- **Pipeline config**: `SanitizationConfig` accepts a new `transform_url`
  field, which is injected into the SDK config dict after `configure()` (the
  SDK's `configure()` only handles `endpoint_url`).
- **Compose / docs**: trial-center image tag and `TRIAL_CENTER_VERSION`
  default bumped to `1.2.0`; upstream container images now reference
  `ghcr.io/protegrity-ai-developer-edition/*`.

### Documentation

- README updated to point at `pre-release-1.2.0` and to list the new minimum
  backend versions (Semantic Guardrail `1.1.1+`, Classification `2.0.0+`).
- ARCHITECTURE updated with the v2 Data Discovery endpoints and the renamed
  GHCR namespace.

## [1.1.0] - 2026-05-14

### Changed

- **Compose topology**: `docker-compose.yml` now defines only the
  `trial-center` UI service. The Semantic Guardrail and Classification /
  Discovery backends are an external prerequisite delivered by Protegrity
  Developer Edition.
- **Backend service URLs**: replaced port-only configuration with full URL
  overrides (`SEMANTIC_GUARDRAIL_URL`, `CLASSIFICATION_SERVICE_URL`).
  Defaults route to `host.docker.internal:8581` / `:8580`.
- **Linux compatibility**: added `extra_hosts: host.docker.internal:host-gateway`
  so the container can reach host services on Linux Docker Engine as well as
  Docker Desktop.
- **Healthcheck**: switched from `curl` (not present in `python:3.11-slim`) to
  `python -c "import urllib.request..."`.
- **Image tagging**: trial-center image is now built and tagged as
  `protegrity/trial-center:${TRIAL_CENTER_VERSION:-1.1.0}`.
- **Deploy script**: prerequisite check now verifies backend reachability
  instead of trying to bind backend ports.

### Documentation

- README rewritten around the new external-backend topology.
- `docs/GETTING_STARTED.md` lists Semantic Guardrail and Classification
  Service as explicit prerequisites and adds an Apple Silicon / arm64 note.
- `docs/ARCHITECTURE.md` updated with the single-container diagram and new
  service-discovery model.

### Fixed

- `app.py` now reads `SEMANTIC_GUARDRAIL_URL` / `CLASSIFICATION_SERVICE_URL`
  (full URL) instead of building hard-coded `http://localhost:PORT` strings,
  so it works correctly from inside a container.
