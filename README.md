# Protegrity Developer Edition

Welcome to the `protegrity-developer-edition` repository, part of the Protegrity Developer Edition suite. This repository provides a self-contained experimentation platform for discovering and protecting sensitive data using Protegrity’s Data Discovery, Semantic Guardrail, and Protection APIs.

## 🚀 Overview

This repository enables developers to:
- Rapidly set up a local environment using Docker Compose.
- Experiment with unstructured text classification, PII discovery, redaction, masking, and tokenization-like protection.
- Experiment with semantic guardrails to secure GenAI applications using messaging risk scoring, conversation risk scoring, and PII scanning.
- Integrate Protegrity APIs into GenAI and traditional applications.
- Use sample applications and data to understand integration workflows.

### Quick Links

- [Prerequisites](#prerequisites)
- [Additional prerequisites for MacOS](#additional-prerequisites-for-macos)
- [Preparing the system](#preparing-the-system)
- If your setup is ready, [run the samples](#running-the-sample-applications)

## 📦 Repository Structure

```text
.
├── CHANGELOG
├── CONTRIBUTIONS.md
├── LICENSE
├── README.md
├── docker-compose.yml                   # Orchestrates data discovery + semantic guardrail services
├── data-discovery/                      # Low-level classification examples
│   ├── sample-classification-commands.sh
│   └── sample-classification-python.py
├── semantic-guardrail/                  # GenAI security risk & PII multi-turn scanning examples
│   └── sample-guardrail-python.py
└── samples/                             # High-level Python SDK samples
    ├── config.json
    ├── requirements.txt
    ├── sample-app-find.py               # Discover and list PII entities
    ├── sample-app-find-and-redact.py    # Discover + redact or mask entities
    ├── sample-app-find-and-protect.py   # Discover + protect entities (tokenize style)
    ├── sample-app-find-and-unprotect.py # Unprotect protected entities
    ├── sample-app-protection.py         # Direct protect / unprotect (CLI style)
    └── sample-data/
        ├── input.txt
        ├── output-redact.txt            # Produced by redact workflow
        ├── output-protect.txt           # Produced by protect workflow
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
  > **Note**: Ensure that the python command on your system points to a supported python3 version, for example, Python 3.12.11. You can verify this by running `python --version`. 
- [pip](https://pip.pypa.io/en/stable/installation/)
- [Python Virtual Environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) 
- Container management software:
    - For Linux/Windows: [Docker](https://docs.docker.com/reference/cli/docker/)
    - For MacOS: [Docker Desktop](https://docs.docker.com/reference/cli/docker/) or Colima
- [Docker Compose V2](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)
- For more information about the minimum requirements, refer to [Prerequisites](https://developer.docs.protegrity.com/docs/install/deved_prereq/).
- Optional: If the Developer Edition is already installed, then complete the following tasks:
    - Back up any customized files.
    - Stop any Developer Edition containers that are running using the `docker compose` command.
    - Remove the `protegrity-developer-python` module using the `pip uninstall protegrity-developer-python` command.

Linux and Windows users can proceed to [Preparing the system](#preparing-the-system).

### Additional prerequisites for MacOS
  
MacOS requires additional steps for Docker and for systems with Apple Silicon chips. Complete the following steps before using Developer Edition. 

1.  Complete one of the following options to apply the settings.
    - For Colima: 
        1. Open a command prompt.
        2. Run the following command.
            ```
            colima start --vm-type vz --vz-rosetta --memory 16
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
            colima start --vm-type vz --vz-rosetta --memory 16
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
    5. Run the `docker compose up -d` from the `protegrity-developer-edition` directory.

### Preparing the system

Complete the steps provided here to use the samples provided with  Developer Edition. 

>   For MacOS, ensure that the [Additional prerequisites for MacOS](#additional-prerequisites-for-macos) steps are complete.

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
    ```
    pip install protegrity-developer-python
    ```
    The installation completes and the success message is displayed.
   

### Running the Sample Applications

The quick runs for each sample is provided here. Open a command prompt and run the command from the repository root. Ensure the [Getting Started](#%EF%B8%8F-getting-started) steps are completed first. For more information about running the application, refer to the [Running the sample application section](https://developer.docs.protegrity.com/docs/running/#running-the-script-for-protecting-data).

#### 1. Discover PII 

List the PII entities.
```
python samples/sample-app-find.py
```
The logs list discovered entities as JSON. No modification of file contents is performed.

#### 2. Find and Redact 

Find and redact or mask information using the default settings. Redaction and masking is controlled using the `method`, that is `redact` or `mask`, and `masking_char` in the `samples/config.json` file.
```
python samples/sample-app-find-and-redact.py
```
This produces the `samples/sample-data/output-redact.txt` file with entities redacted, that is removed, or masked.

#### 3. Semantic Guardrail using Python

Run the sample using Python. 
```
python semantic-guardrail/sample-guardrail-python.py
```
This submits a multi-turn conversation with semantic and performs PII processing.

#### 4. Setting the environment variables

The next steps has samples that demonstrate how to protect and unprotect data using the Protection APIs. The Protection APIs rely on authenticated access to the Developer Edition API Service.
- `samples/sample-app-find-and-protect.py`
- `samples/sample-app-protection.py`

Perform the steps from [Additional settings for using the Developer Edition API Service](#additional-settings-for-using-the-developer-edition-api-service) to obtain the API key and password for setting the environment variables. If you already have the API key and password, then proceed to export the environment variables.   

- For Linux and MacOS:
    ```
    export DEV_EDITION_EMAIL='<Email_used_for_registration>'
    ```

    ```
    export DEV_EDITION_PASSWORD='<Password_provided_in_email>'
    ```

    ```
    export DEV_EDITION_API_KEY='<API_key_provided_in_email>'
    ```  

    Verify that the variables are set.
    ```
    test -n "$DEV_EDITION_EMAIL" && echo "EMAIL $DEV_EDITION_EMAIL set" || echo "EMAIL missing"
    test -n "$DEV_EDITION_PASSWORD" && echo "PASSWORD $DEV_EDITION_PASSWORD set" || echo "PASSWORD missing"
    test -n "$DEV_EDITION_API_KEY" && echo "API KEY $DEV_EDITION_API_KEY set" || echo "API KEY missing"
    ```

- For Windows PowerShell:  
    ```
    $env:DEV_EDITION_EMAIL = '<Email_used_for_registration>' 
    ```

    ``` 
    $env:DEV_EDITION_PASSWORD = '<Password_provided_in_email>' 
    ```

    ``` 
    $env:DEV_EDITION_API_KEY = '<API_key_provided_in_email>'  
    ```  

    Verify that the variables are set
    ```
    if ($env:DEV_EDITION_EMAIL) { Write-Output "EMAIL $env:DEV_EDITION_EMAIL set"} else { Write-Output "EMAIL missing"} 
    if ($env:DEV_EDITION_PASSWORD) { Write-Output "PASSWORD $env:DEV_EDITION_PASSWORD set" } else { Write-Output "PASSWORD missing" } 
    if ($env:DEV_EDITION_API_KEY) { Write-Output "API KEY $env:DEV_EDITION_API_KEY set" } else { Write-Output "API KEY missing" } 
    ```

#### 5. Find and Protect 

Ensure that the [environment variables are exported](#4-setting-the-environment-variables) and then run the sample code. 

```
python samples/sample-app-find-and-protect.py
```
This produces the `samples/sample-data/output-protect.txt` file with protected, this is tokenized-like, values.

To get original data run:
```
python samples/sample-app-find-and-unprotect.py
```
This reads the `samples/sample-data/output-protect.txt` file and produces the `samples/sample-data/output-unprotect.txt` file with original values.

#### 6. Direct Protect and Unprotect from the CLI

Use the sample commands below to protect and unprotect data. Ensure that the [environment variables are exported](#4-setting-the-environment-variables) and then run the sample code.

For information about the users, roles, and data elements, refer to [*Understanding Users and Roles* and *Understanding the Data Elements*](https://developer.docs.protegrity.com/docs/running/#running-the-script-for-protecting-data)

```
# protect
python samples/sample-app-protection.py --input_data "John Smith" --policy_user superuser --data_element name --protect
```
```
# unprotect
python samples/sample-app-protection.py --input_data "protected_data" --policy_user superuser --data_element name --unprotect
```
The `protected_data` value is obtained from the output of the protect command.

Similarly, to encrypt and decrypt data, run the following commands:
```
# encrypt
python samples/sample-app-protection.py --input_data "John Smith" --policy_user superuser --data_element text --enc
```
```
# decrypt
python samples/sample-app-protection.py --input_data "encrypted_data" --policy_user superuser --data_element text --dec
```
The `encrypted_data` value is obtained from the output of the encrypt command.

For more information about the `sample-app-protection.py`, run the following command:
```
python samples/sample-app-protection.py --help
```

##### Additional settings for using the Developer Edition API Service
  
Prior registration is required to obtain credentials for accessing the Developer Edition API Service. The following samples demonstrate how to protect and unprotect data using the Protection APIs. The Protection APIs rely on authenticated access to the Developer Edition API Service.
- `samples/sample-app-find-and-protect.py`
- `samples/sample-app-protection.py`

1.  Open a web browser.
2.  Navigate to [https://www.protegrity.com/developers/get-api-credentials ](https://www.protegrity.com/developers/get-api-credentials).
3.  Specify the following details:
    -   First Name
    -   Last Name
    -   Work Email
    -   Job Title
    -   Company Name
    -   Country
4.  Click the Terms & Conditions link and read the terms and conditions.
5.  Select the check box to accept the terms and conditions.
    The request is analyzed. After the request is approved, an API key and password to access the Developer Edition API Service is sent to the Work Email specified. Keep the API key and password safe. You need to export them to environment variables for using the Developer Edition API Service.  

    > **Note**: After completing registration, allow 1-2 minutes for the confirmation email to arrive. If you do not see it in your inbox, check your spam or junk folder before retrying.  

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

### Service Endpoints (default using docker compose)
- Classification API: `http://localhost:${CLASSIFICATION_PORT:-8580}/pty/data-discovery/v1.0/classify`
- Semantic Guardrail API: `http://localhost:${SGR_PORT:-8581}/pty/semantic-guardrail/v1.0/conversations/messages/scan`

If you change published ports in `docker-compose.yml`, update `endpoint_url`. Also, if required, update the semantic guardrail URL in the scripts.

### Docker Compose Services
`docker-compose.yml` provisions:
- `presidio-provider-service` and `roberta-provider-service`: ML provider backends.
- `classification-service`: Exposes Data Discovery REST API. Uses port 8580 by default.
- `semantic-guardrail-service`: Conversation risk and PII scanning depends on classification. Uses port 8581 by default.

Restart stack after changes to `docker-compose.yml` file from `protegrity-developer-edition` directory:
```
docker compose down && docker compose up -d
```

Check service logs for any errors from `protegrity-developer-edition` directory:
```
docker compose logs
```
## 📚 Documentation

- The Protegrity Developer Edition documentation is available at [https://developer.docs.protegrity.com/](https://developer.docs.protegrity.com/).
- For API reference and tutorials, visit the Developer Portal at [https://www.protegrity.com/developers](https://www.protegrity.com/developers).

## 📢 Community & Support

- Join the discussion on https://github.com/orgs/Protegrity-Developer-Edition/discussions.
- Anonymous downloads supported; registration required for participation.
- Issues / feature requests: please include sample script name & log snippet.

## 📜 License

See [LICENSE](https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition/blob/main/LICENSE) for terms and conditions.
