# Protegrity Developer Edition

Welcome to the `protegrity-developer-edition` repository, part of the Protegrity Developer Edition suite. This repository provides a self-contained experimentation platform for discovering and protecting sensitive data using Protegrity’s Data Discovery and Protection APIs.

## 🚀 Overview

This repository enables developers to:
- Rapidly set up a local environment using Docker Compose.
- Experiment with unstructured text classification, PII discovery, redaction, masking, and tokenization-like protection.
- Experiment with semantic guardrails to secure GenAI applications using messaging risk scoring, conversation risk scoring, and PII scanning.
- Integrate Protegrity APIs into GenAI and traditional applications.
- Use sample applications and data to understand integration workflows.

## 📦 Repository Structure

```text
.
├── CHANGELOG
├── CONTRIBUTIONS.md
├── LICENSE
├── README.md
├── docker-compose.yml               # Orchestrates data discovery + semantic guardrail services
├── data-discovery/                  # Low-level classification examples
│   ├── sample-classification-commands.sh
│   └── sample-classification-python.py
├── semantic-guardrail/              # GenAI security risk & PII multi-turn scanning examples
│   ├── sample-guardrail-command.sh
│   └── sample-guardrail-python.py
└── samples/                         # High-level Python SDK samples
    ├── config.json
    ├── requirements.txt
    ├── sample-app-find.py           # Discover and list PII entities
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

- **Data Discovery**: REST-based classification and entity detection of unstructured text.
- **PII Discovery**: Enumerate detected entities with confidence scores.
- **Redaction / Masking**: Replace detected entities (configurable masking char, mapping).
- **Protection (Tokenization-like)**: Protect and unprotect specific data elements using `sample-app-protection.py` and combined find + protect sample.
- **Semantic Guardrail**: Message and conversation level risk scoring + PII scanning for GenAI flows.
- **Multi-turn Examples**: Use the curl and Python samples from the semantic guardrail directory.
- **Configurable Samples**: Adjust behavior through `samples/config.json`.
- **Cross-platform**: Works on Linux, MacOS, and Windows.

## 🛠️ Getting Started

### Prerequisites
- [Python >= 3.12.11](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installation/)
- [Python Virtual Environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) 
- Container management software:
    - For Linux/Windows: [Docker](https://docs.docker.com/reference/cli/docker/)
    - For MacOS: [Docker Desktop](https://docs.docker.com/reference/cli/docker/) or Colima
- [Docker Compose V2](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)
- Optional: If the Developer Edition is already installed, then complete the following tasks:
    - Back up any customized files
    - Stop any running Developer Edition-related containers
    - Remove the `protegrity-developer-python` module

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
    3. Add the following parameter.
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
    >   **Note: After cloning switch to the pre-release-1.0.0 branch `git checkout pre-release-1.0.0`**
4.  Start the services (classification + semantic guardrail) in background. The dependent containers are large; downloads may take time.
    ```
    docker compose up -d
    ```
    Based on your configuration use the `docker-compose up -d` command.
5. Install the `protegrity-developer-python` module. It is recommended to install and activate the Python virtual environment before installing the module.
    ```
    pip install --index-url https://test.pypi.org/simple/ --no-deps protegrity-developer-python
    ```
    The installation completes and the success message is displayed.
    >   **Note: The above pip install command will change to `pip install protegrity-developer-python` once the python module is pushed to Prod PyPi.

If protection and tokenization is not required, then proceed to [Run the Sample Applications](#run-the-sample-applications).

**Additional settings for using the Developer Edition API Service**
  
Prior registration is required to obtain credentials for accessing the Developer Edition API Service. The following samples demonstrate how to protect and unprotect data using the Protection APIs. The Protection APIs rely on authenticated access to the Developer Edition API Service.
- `samples/sample-app-find-and-protect.py`
- `samples/sample-app-protection.py`

1.  Register for a free API key and password to access the Developer Edition API Service.
    1.  Open a web browser.
    2.  Navigate to [https://www.protegrity.com/developers/register ](https://protegritywpst.wpenginepowered.com/developers/register).
    3.  Specify the following details:
        -   First Name
        -   Last Name
        -   Work Email
        -   Job Title
        -   Company Name
        -   Country
    4.  Click the Terms & Conditions link and read the terms and conditions.
    5.  Select the check box to accept the terms and conditions.
        The request is analyzed. After the request is approved, a password and API key to access the Developer Edition API Service is sent to the Work Email specified.

2.  Add the authentication information to the environment.
    1.  Open a command prompt.
    2.  Initialize a Python virtual environment.
    3.  Add the details to the environment.
        ```
        export DEV_EDITION_EMAIL='<Email_used_for_registration>'
        export DEV_EDITION_PASSWORD='<Password_provided_in_email>'
        export DEV_EDITION_API_KEY='<API_key_provided_in_email>'
        ```
    6.  Verify that the variables are set.
        ```
        test -n "$DEV_EDITION_EMAIL" && echo "EMAIL set" || echo "EMAIL missing"
        test -n "$DEV_EDITION_PASSWORD" && echo "PASSWORD set" || echo "PASSWORD missing"
        test -n "$DEV_EDITION_API_KEY" && echo "API KEY set" || echo "API KEY missing"
        ```

## Running the Sample Applications

The quick runs for each sample is provided here. Open a command prompt and run the command from the repository root. Ensure the [Getting Started](#️-getting-started) steps are completed first.

### 1. Discover PII 

List the PII entities.
```
python samples/sample-app-find.py
```
The logs list discovered entities as JSON. No modification of file contents is performed.

### 2. Find and Redact 

Find and redact or mask information using the default settings. Redaction and masking is controlled using the `method`, that is `redact` or `mask`, and `masking_char` in the `samples/config.json` file.
```
python samples/sample-app-find-and-redact.py
```
This produces the `samples/sample-data/output-redact.txt` file with entities redacted, that is removed, or masked.

### 3. Semantic Guardrail using curl

Test the feature using the `curl` command. 
```
bash semantic-guardrail/sample-guardrail-command.sh
```
This returns the HTTP status and the JSON with risk scores.

### 4. Semantic Guardrail using Python

Test the feature using Python. 
```
python semantic-guardrail/sample-guardrail-python.py
```
This submits a multi-turn conversation with semantic and performs PII processing.

### 5. Find and Protect 

Test the protection workflow.
```
python samples/sample-app-find-and-protect.py
```
This produces the `samples/sample-data/output-protect.txt` file with protected, this is tokenized-like, values.

### 6. Direct Protect and Unprotect from the CLI

Use the Protection utility to protect and unprotect data. Add the `--protect` or `--unprotect` flags to limit operation. 

```
python samples/sample-app-protection.py --input_data "John Smith" --policy_user superuser --data_element name
```
The protect and unprotect operations are performed sequentially.


## 📄 Configuration

Edit `samples/config.json` to customize SDK behavior. 
Keys:
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

#### Service Endpoints (default using docker compose)
- Classification API: `http://localhost:${CLASSIFICATION_PORT:-8580}/pty/data-discovery/v1.0/classify`
- Semantic Guardrail API: `http://localhost:${SGR_PORT:-8581}/pty/semantic-guardrail/v1.0/conversations/messages/scan`

If you change published ports in `docker-compose.yml`, update `endpoint_url`. Also, if required, update the semantic guardrail URL in the scripts.

#### Docker Compose Services
`docker-compose.yml` provisions:
- `presidio-provider-service` and `roberta-provider-service`: ML provider backends.
- `classification-service`: Exposes Data Discovery REST API. Uses port 8580 by default.
- `semantic-guardrail-service`: Conversation risk and PII scanning depends on classification. Uses port 8581 by default.

Restart stack:
```
docker compose down && docker compose up -d
```

Check health using curl:
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
