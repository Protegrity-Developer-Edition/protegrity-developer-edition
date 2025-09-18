# Protegrity Developer Edition

Welcome to the `protegrity-developer-edition` repository, part of the Protegrity Developer Edition suite. This repository provides a self-contained experimentation platform for discovering and protecting sensitive data using Protegrity’s Data Discovery and Protection APIs.

## 🚀 Overview

This repository enables developers to:
- Rapidly set up a local environment using Docker Compose.
- Experiment with unstructured text classification, PII discovery, redaction, masking, and tokenization-like protection.
- Experiment with semantic guardrails to secure GenAI applications (message / conversation risk scoring + PII scanning).
- Integrate Protegrity APIs into GenAI and traditional applications.
- Use sample applications and data to understand integration workflows.

## 📦 Repository Structure

```text
.
├── CHANGELOG
├── CONTRIBUTIONS.md
├── LICENSE
├── README.md
├── docker-compose.yml                # Orchestrates classification + semantic guardrail services
├── data-discovery/                  # Low-level classification examples
│   ├── sample-classification-commands.sh
│   └── sample-classification-python.py
├── semantic-guardrail/              # GenAI security risk & PII multi-turn scanning examples
│   ├── sample-guardrail-command.sh
│   └── sample-guardrail-python.py
└── samples/                         # High-level Python SDK samples
    ├── config.json
    ├── requirements.txt
    ├── sample-app-find.py           # Discover (list) PII entities
    ├── sample-app-find-and-redact.py# Discover + redact or mask entities
    ├── sample-app-find-and-protect.py# Discover + protect entities (tokenize style)
    ├── sample-app-protection.py     # Direct protect / unprotect (CLI style)
    └── sample-data/
        ├── input.txt
        ├── output-redact.txt        # Produced by redact workflow
        ├── output-protect.txt       # Produced by protect workflow
        └── (generated files ...)
```

## 🧰 Features

- **Data Discovery**: REST-based classification & entity detection of unstructured text.
- **PII Discovery**: Enumerate detected entities with confidence scores.
- **Redaction / Masking**: Replace detected entities (configurable masking char, mapping).
- **Protection (Tokenization-like)**: Protect & unprotect specific data elements via `sample-app-protection.py` and combined find+protect sample.
- **Semantic Guardrail**: Message & conversation level risk scoring + PII scanning for GenAI flows.
- **Multi-turn Examples**: Provided for curl and Python (semantic guardrail folder).
- **Configurable Samples**: Adjust behavior through `samples/config.json`.
- **Cross-platform**: Works on Linux, Windows, and MacOS.

## 🛠️ Getting Started

### Prerequisites
- [Python >= 3.9.23](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installation/)
- [Python Virtual Environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) 
- Container management software:
    - For Linux/Windows: [Docker](https://docs.docker.com/reference/cli/docker/)
    - For MacOS: [Docker Desktop](https://docs.docker.com/reference/cli/docker/) or Colima
- [Docker Compose V2](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)

Linux and Windows users can proceed to [Setup Instructions](#setup-instructions).

**Additional settings for MacOS**
  
MacOS requires additional steps for Docker and for systems with Apple Silicon chips. Complete the following steps before using Developer Edition. 

1.  Complete one of the following options to apply the settings.
    - For Colima: 
        1. Open a command prompt.
        2. Run the following command.
            ```
            colima start --vm-type vz --vz-rosetta
            ```
    - For Docker Desktop: 
        1.  Open Docker Desktop.
        2.  Go to **Settings > General**.
        3.  Enable the following check boxes:
            -   **Use Virtualization framework**
            -   **Use Rosetta for x86_64/amd64 emulation on Apple Silicon**
        4.  Click **Apply & restart**.

2.  Update one of the following options for resolving  certificate related errors.
    - For Colima:
        1.  Open a command prompt.
        2.  Navigate and open the following file.
    
            ```
            ~/.colima/default/colima.yaml
            ```
        3.  Update the following configuration in `colima.yaml` to add the path for obtaining the required images.

            Before update:
            ```
            docker: {}
            ```
      
            After update:
            ```
            docker:
                insecure-registries:
                    - ghcr.io
            ```
        4. Save and close the file.
        5. Stop colima.
            ```
            colima stop
            ```
        6. Close and start the command prompt.
        7. Start colima.
            ```
            colima start --vm-type vz --vz-rosetta
            ```
    - For Docker Desktop: 
        1.  Open Docker Desktop.
        2.  Click the gear or settings icon.
        3.  Click **Docker Engine** from the sidebar. The editor with your current Docker daemon configuration `daemon.json` opens.
        4.  Locate and add the `insecure-registries` key in the root JSON object. Ensure that you add a comma after the last value in the existing configuration.

            After update:
            ```
            {
                .
                .
                <existing configuration>,
                "insecure-registries": [
                    "ghcr.io",
                    "githubusercontent.com"
                ]
            }
            ```

        5.  Click **Apply & Restart** to save the changes and restart Docker Desktop.
        6.  Verify: After Docker restarts, run `docker info` in your terminal and confirm that the required registry is listed under **Insecure Registries**.

3.  Optional: If the *The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8) and no specific platform was requested* error is displayed.

    1.  Start a command prompt.
    2.  Navigate and open the following file.

        ```
        ~/.docker/config.json
        ```
    3. Add the following paramater.
        ```
        "default-platform": "linux/amd64"
        ```
    4. Save and close the file.
    5. Run the `docker compose up -d` from the `protegrity-developer-edition` directory if already cloned, else proceed to Setup Instructions.

### Setup Instructions

Complete the steps provided here to clone, install, find, and test the Developer Edition.

1.  Open a command prompt.
2.  Clone the git repository.
    ```
    git clone https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition.git
    ```
3.  Navigate to the `protegrity-developer-edition` directory in the cloned location.
4.  Start the services (classification + semantic guardrail) in background. The dependent containers are large; downloads may take time.
    ```
    docker compose up -d
    ```
    Based on your configuration use the `docker-compose up -d` command.
5. Install the `protegrity-developer-python` module. It is recommended to install and activate the Python virtual environment before installing the module.
    ```bash
    pip install protegrity-developer-python
    ```
    The installation completes and the success message is displayed.


### Run the Sample Applications

Below are quick runs for each sample (run from repository root). Ensure `pip install protegrity-developer-python` is completed first.

#### 1. Discover PII (list entities only)
```
python samples/sample-app-find.py
```
Logs list discovered entities as JSON (no modification of file contents).

#### 2. Find and Redact (default method)
```
python samples/sample-app-find-and-redact.py
```
Produces `samples/sample-data/output-redact.txt` with entities removed (redacted) or masked.

### Protection Samples Prerequisites (Registration Required)
The following samples invoke Protection (protect / unprotect) APIs and REQUIRE prior registration to obtain credentials:
- `samples/sample-app-find-and-protect.py`
- `samples/sample-app-protection.py`

After registration you will receive the following credentials: email, password, and API key. Export them before running protection samples.

Required environment variables:
```bash
export DEV_EDITION_EMAIL="<your_registered_email>"
export DEV_EDITION_PASSWORD="<your_portal_password>"
export DEV_EDITION_API_KEY="<your_api_key>"
```
Verification:
```bash
test -n "$DEV_EDITION_EMAIL" && echo "EMAIL set" || echo "EMAIL missing"
test -n "$DEV_EDITION_PASSWORD" && echo "PASSWORD set" || echo "PASSWORD missing"
test -n "$DEV_EDITION_API_KEY" && echo "API KEY set" || echo "API KEY missing"
```
Missing variables will cause authentication / authorization failures when calling protect or unprotect operations.

#### 3. Find and Protect (protection workflow)
```
python samples/sample-app-find-and-protect.py
```
Produces `samples/sample-data/output-protect.txt` with protected (tokenized-like) values.

#### 4. Direct Protect / Unprotect CLI
```
python samples/sample-app-protection.py --input_data "John Smith" --policy_user superuser --data_element name
```
Add `--protect` or `--unprotect` to limit operation. Without flags both are performed sequentially.

#### 5. Semantic Guardrail (curl)
```
bash semantic-guardrail/sample-guardrail-command.sh
```
Returns HTTP status then JSON with risk scores.

#### 6. Semantic Guardrail (Python)
```
python semantic-guardrail/sample-guardrail-python.py
```
Submits multi-turn conversation with semantic + PII processors.

> Note: Redaction vs masking is controlled via `method` ("redact" or "mask") and `masking_char` in `samples/config.json`.

## 📄 Configuration

Edit `samples/config.json` to customize SDK behavior. Keys:
- `named_entity_map`: Optional mappings (friendly labels) used during redact/mask.
- `method`: `redact` (remove) or `mask` (replace with masking char).
- `masking_char`: Character for masking (when `method` = mask).
- `classification_score_threshold`: Minimum confidence (default 0.6 if omitted).
- `endpoint_url`: Override classification endpoint (defaults internally to docker compose service `http://localhost:8580/...`).
- `enable_logging`, `log_level`.

Current example:
```json
{
    "masking_char": "#",
    "named_entity_map": {
        "USERNAME": "USERNAME",
        "STATE": "STATE",
        "PHONE_NUMBER": "PHONE",
        "SOCIAL_SECURITY_NUMBER": "SSN",
        "AGE": "AGE",
        "CITY": "CITY",
        "PERSON": "PERSON"
    },
    "method": "redact"
}
```

#### Service Endpoints (default via docker compose)
- Classification API: `http://localhost:${CLASSIFICATION_PORT:-8580}/pty/data-discovery/v1.0/classify`
- Semantic Guardrail API: `http://localhost:${SGR_PORT:-8581}/pty/semantic-guardrail/v1.0/conversations/messages/scan`

If you change published ports in `docker-compose.yml`, update `endpoint_url` (and guardrail URL in scripts if needed).

#### Docker Compose Services
`docker-compose.yml` provisions:
- `presidio-provider-service` & `roberta-provider-service`: ML provider backends.
- `classification-service`: Exposes Data Discovery REST API (port 8580 default).
- `semantic-guardrail-service`: Conversation risk + PII scanning (port 8581 default) depends on classification.

Restart stack:
```
docker compose down && docker compose up -d
```

Check health (simple curl):
```
curl -s http://localhost:8580/pty/data-discovery/v1.0/classify -o /dev/null -w "%{http_code}\n"  # Expect 405/400 on GET (endpoint requires POST)
```

## 📚 Documentation

- The Protegrity Developer Edition documentation is available at [http://developer.docs.protegrity.com/](http://developer.docs.protegrity.com/).
- For API reference and tutorials, visit the Developer Portal at [https://www.protegrity.com/developers](https://www.protegrity.com/developers).

## 📢 Community & Support

- Join the discussion on https://github.com/orgs/Protegrity-Developer-Edition/discussions.
- Anonymous downloads supported; registration required for participation.
- Issues / feature requests: please include sample script name & log snippet.

## 📜 License

See [LICENSE](https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition/blob/main/LICENSE) for terms and conditions.
