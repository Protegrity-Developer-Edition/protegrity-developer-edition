<div align="center">

# Protegrity AI Developer Edition
[![Version](https://img.shields.io/badge/version-1.1.0-green.svg?style=flat)](https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat)](https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition/blob/main/LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat)](https://www.python.org/downloads/)
[![Java 11+](https://img.shields.io/badge/java-11+-blue.svg?style=flat)](https://www.oracle.com/java/technologies/javase-jdk11-downloads.html)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=black)](https://www.linux.org/)
[![Windows](https://img.shields.io/badge/Windows-0078D6?style=flat&logo=windows&logoColor=white)](https://www.microsoft.com/windows/)
[![macOS](https://img.shields.io/badge/mac%20os-000000?style=flat&logo=macos&logoColor=F0F0F0)](https://www.apple.com/macos/)
[![PyPI 1.1.1](https://img.shields.io/pypi/v/protegrity-developer-python.svg)](https://pypi.org/project/protegrity-developer-python/)
[![Anaconda 1.1.1](https://anaconda.org/protegrity/protegrity-developer-python/badges/version.svg?style=flat)](https://anaconda.org/protegrity/protegrity-developer-python)
[![Maven Central 1.0.1](https://img.shields.io/maven-central/v/com.protegrity/protegrity-developer-edition.svg?style=flat)](https://search.maven.org/artifact/com.protegrity/protegrity-developer-edition)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Protegrity-Developer-Edition/protegrity-developer-edition)
</div>

Welcome to the `protegrity-developer-edition` repository, part of the Protegrity AI Developer Edition suite. This repository provides a self-contained experimentation platform for discovering and protecting sensitive data using Protegrity’s Data Discovery, Semantic Guardrail, and Protection APIs. Use the online [Protegrity notebook](https://mybinder.org/v2/gh/Protegrity-Developer-Edition/protegrity-developer-edition/main?filepath=samples/python/sample-app-protect-unprotect/getting-started-protection.ipynb) to quickly test tokenization.

## 🚀 Overview

This repository enables developers to:
- Rapidly set up a local environment using Docker Compose.
- Experiment with unstructured text classification, PII discovery, redaction, masking, and tokenization-like protection.
- Experiment with semantic guardrails to secure GenAI applications using messaging risk scoring, conversation risk scoring, and PII scanning.
- Integrate Protegrity APIs into GenAI and traditional applications.
- Use sample applications and data to understand integration workflows.

**Why This Matters**

AI is transforming every industry, but privacy can’t be an afterthought. Protegrity AI Developer Edition 1.1.0 makes enterprise-grade data discovery and data protection developer-friendly, so you can build secure, privacy-first solutions for both AI pipelines and traditional data workflows. Whether you’re protecting sensitive information in analytics pipelines, business applications, or next-generation AI, Protegrity AI Developer Edition empowers you to innovate confidently while keeping data safe. 

Protegrity AI Developer Edition enables secure data and AI pipelines, including:

- **Privacy in conversational AI:** Sensitive chatbot inputs are protected before they reach generative AI models.

- **Prompt sanitization for LLMs:** Automated PII masking reduces risk during large language model prompt engineering and inference.

- **Experimentation with Jupyter notebooks:** Data scientists can prototype directly in Jupyter notebooks for agile experimentation.

- **Output redaction and leakage prevention:** Detect and protect sensitive data in model outputs before returning them to end users.

- **Privacy-enhanced AI training:** Sensitive fields in training datasets are de-identified to support compliant and secure AI development.

- **Synthetic data generation for privacy-preserving AI:** Automatically create realistic, anonymized datasets that mimic production data without exposing sensitive information, enabling safe model training and testing.

### Quick Links

- [Prerequisites](#prerequisites)
- [Preparing the system](#preparing-the-system)
- [Additional prerequisites for MacOS](#additional-prerequisites-for-macos)
- If your setup is ready, [run the samples](#running-the-sample-applications)

### Repositories

Protegrity AI Developer Edition provides the files required and also the source code for customization. The following repositories are available:

-   [protegrity-developer-edition](https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition): This is the main repository with the files and samples required for experiencing Protegrity AI Developer Edition.
-   [protegrity-developer-python](https://github.com/Protegrity-Developer-Edition/protegrity-developer-python): This is the repository with the source code for the Python module. Use the files in this repository only to customize and use the Python module.
-   [protegrity-developer-java](https://github.com/Protegrity-Developer-Edition/protegrity-developer-java): This is the repository with the source code for the Java library. Use the files in this repository only to customize and use the Java library.


## 📦 Repository Structure 

```text
.
├── CHANGELOG
├── CONTRIBUTIONS.md
├── LICENSE
├── README.md
├── docker-compose.yml                   # Orchestrates data discovery + semantic guardrail services
├── data-discovery/                      # Low-level classification examples
│   ├── sample-classification-bash-text.sh
│   ├── sample-classification-bash-tabular.sh
│   ├── sample-classification-python-text.py
│   └── sample-classification-python-tabular.py
├── semantic-guardrail/                  # GenAI security risk & PII multi-turn scanning examples
│   └── sample-guardrail-python.py
└── samples/                             # High-level SDK samples (Python & Java)
    ├── python/
    │   ├── sample-app-protect-unprotect/    # Protect / Unprotect Jupyter Notebook samples
    │   │   ├── getting-started-protection.ipynb
    │   ├── sample-app-semantic-guardrails/  # Semantic Guardrail Jupyter Notebook samples
    │   │   ├── Sample Application.ipynb
    │   ├── sample-app-synthetic-data/       # Synthetic Data Jupyter Notebook samples
    │   │   ├── synthetic_data.ipynb
    │   ├── sample-app-find.py               # Discover and list PII entities
    │   ├── sample-app-find-and-redact.py    # Discover + redact or mask entities
    │   ├── sample-app-find-and-protect.py   # Discover + protect entities (tokenize style)
    │   ├── sample-app-find-and-unprotect.py # Unprotect protected entities
    │   └── sample-app-protection.py         # Direct protect / unprotect (CLI style)
    ├── java/                            # Java SDK samples
    │   ├── sample-app-find.sh               # Discover and list PII entities
    │   ├── sample-app-protection.sh         # Direct protect / unprotect (CLI style)
    │   ├── sample-app-find-and-protect.sh   # Discover + protect entities
    │   ├── sample-app-find-and-unprotect.sh # Unprotect protected entities
    │   └── sample-app-find-and-redact.sh    # Discover + redact entities
    ├── config.json
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
- **Synthetic Data**: Synthetic Data is a privacy-enhancing technology that generates artificial data from real datasets while preserving statistical properties and relationships without exposing actual personal information.
- **Multi-turn Examples**: Use the curl and Python samples from the semantic guardrail directory.
- **Configurable Samples**: Adjust behavior through `samples/config.json`.
- **Cross-platform**: Works on Linux, MacOS, and Windows.

## 🛠️ Getting Started

### Prerequisites
- [Python >= 3.12.11](https://www.python.org/downloads/) (for Python samples)  
  > **Note**: Ensure that the python command on your system points to a supported python3 version, for example, Python 3.12.11. You can verify this by running `python --version`. 
- [pip](https://pip.pypa.io/en/stable/installation/) (for Python samples)
- [Python Virtual Environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) (for Python samples)
- [Java 11 or later](https://www.oracle.com/java/technologies/javase-jdk11-downloads.html) (for Java samples)
- [Maven 3.6+](https://maven.apache.org/download.cgi) or use the included Maven wrapper (for Java samples) 
- Container management software:
    - For Linux/Windows: [Docker](https://docs.docker.com/reference/cli/docker/)
    - For MacOS: [Docker Desktop](https://docs.docker.com/reference/cli/docker/) or Colima
- [Docker Compose > 2.30 ](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)
- For more information about the minimum requirements, refer to [Prerequisites](https://developer.docs.protegrity.com/docs/install/deved_prereq/).
- Optional: If the AI Developer Edition is already installed, then complete the following tasks:
    - Back up any customized files.
    - Stop any AI Developer Edition containers that are running using the `docker compose down --remove-orphans` command.
    - Remove the `protegrity-developer-python` module using the `pip uninstall protegrity-developer-python` command.

### Preparing the system

Complete the steps provided here to use the samples provided with AI Developer Edition. 

>   For MacOS, ensure that the [Additional prerequisites for MacOS](#additional-prerequisites-for-macos) steps are complete.

1.  Open a command prompt.
2.  Clone the git repository.
    ```
    git clone https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition.git
    ```
3.  Navigate to the `protegrity-developer-edition` directory in the cloned location.
   
4.  Start the services (classification + semantic guardrail + Synthetic Data [with profile]) in background. The dependent containers are large; downloads may take time.
    - To start the Data Discovery and Semantic Guardrail services, run: 
    ```
    docker compose up -d
    ```
    - To start the Data Discovery, Semantic Guardrail, and Synthetic Data services, run: 
    ```
    docker compose --profile synthetic up -d
    ```
    Based on your configuration use the `docker-compose up -d` command.
5. Install the `protegrity-developer-python` module.
    > **Note**: It is recommended to install and activate the Python virtual environment before installing the module.
    ```
    pip install protegrity-developer-python
    ```
    The installation completes and the success message is displayed. Alternatively, to build the module from source, refer to [Building the Python module from source](https://github.com/Protegrity-Developer-Edition/protegrity-developer-python?tab=readme-ov-file#build-the-protegrity-developer-python-module).
6. For Java samples, the `protegrity-developer-java` module is automatically downloaded from Maven Central when you run a sample for the first time.
    Alternatively, to build the java library from source, refer to [Building the Java module from source](https://github.com/Protegrity-Developer-Edition/protegrity-developer-java?tab=readme-ov-file#build-the-protegrity-developer-java-modules).
7. Install Jupyter Lab to run the notebook samples provided for Semantic Guardrail and Synthetic Data.
    > **Note**: It is recommended to install and activate the Python virtual environment. 
    ```
    pip install -r samples/python/requirements.txt
    ```  

### Running the Sample Applications

The quick runs for each sample is provided here. Open a command prompt and run the command from the repository root. Ensure the [Getting Started](#%EF%B8%8F-getting-started) steps are completed first. For more information about running the application, refer to the [Running the sample application section](https://developer.docs.protegrity.com/docs/running/#running-the-script-for-protecting-data).

> **Note**: Both Python and Java samples are available. Python samples are located in `samples/python/` and Java samples in `samples/java/`. Choose the language that best fits your project needs.

#### 1. Discover PII 

List the PII entities.

**Python:**
```
python samples/python/sample-app-find.py
```

**Java:**
```
bash samples/java/sample-app-find.sh
```

The logs list discovered entities as JSON. No modification of file contents is performed.

#### 2. Find and Redact 

Find and redact or mask information using the default settings. Redaction and masking is controlled using the `method`, that is `redact` or `mask`, and `masking_char` in the `samples/config.json` file.

**Python:**
```
python samples/python/sample-app-find-and-redact.py
```

**Java:**
```
bash samples/java/sample-app-find-and-redact.sh
```

This produces the `samples/sample-data/output-redact.txt` file with entities redacted, that is removed, or masked.

#### 3. Running Data Discovery on tabular data
 
The `sample-classification-python-tabular` analyzes text from the `data-discovery/input.csv` file.
 
```
cd data-discovery
python sample-classification-python-tabular.py
```

#### 4. Semantic Guardrail using Python

Run the sample using Python. 
```
python semantic-guardrail/sample-guardrail-python.py
```
This submits a multi-turn conversation with semantic and performs PII processing.

#### 5. Semantic Guardrail using Jupyter Notebook
> **Note**: It is recommended to install and activate the Python virtual environment. 
1.	Run the following command to start Jupyter Lab for running Semantic Guardrail.
    ```
    jupyter lab
    ```
2.	Copy the URL displayed and navigate to the site from a web browser. Ensure that localhost is replaced with the IP address of the system where the AI Developer Edition is set up.
3.	In the left pane of the notebook, navigate to `samples/python/sample-app-semantic-guardrails`.
4.	Open the `Sample Application.ipynb` file.
5.	Click the Play icon and follow the prompts in the notebook.

#### 6. Synthetic Data using Jupyter Notebook
A Jupyter Notebook is provided for using Protegrity Synthetic Data. 

> **Note**: It is recommended to install and activate the Python virtual environment. 
1. Start Jupyter Lab using the following command.
    ```
    jupyter lab
   ```
    The Jupyter lab starts and a URL with a token is displayed. 
2. Copy the URL displayed and navigate to the site from a web browser. Ensure that localhost is replaced with the IP address of the system where the AI Developer Edition is set up.
3. In the left pane of the notebook, navigate to `samples/python/sample-app-synthetic-data`.
4. Open the `synthetic_data.ipynb` file.
5. Click the Play icon and follow the steps in the notebook to explore the synthetic data capabilities.


#### 7. Setting the environment variables

The next steps has samples that demonstrate how to protect and unprotect data using the Protection APIs. The Protection APIs rely on authenticated access to the AI Developer Edition API Service.
- `samples/python/sample-app-find-and-protect.py`
- `samples/python/sample-app-protection.py`
- `samples/python/sample-app-find-and-unprotect.py`
- `samples/java/sample-app-find-and-protect.sh`
- `samples/java/sample-app-protection.sh`
- `samples/java/sample-app-find-and-unprotect.sh`

Perform the steps from [Additional settings for using the AI Developer Edition API Service](#additional-settings-for-using-the-ai-developer-edition-api-service) to obtain the API key and password for setting the environment variables. If you already have the API key and password, then proceed to export the environment variables.   

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

#### 8. Find and Protect 

Ensure that the [environment variables are exported](#4-setting-the-environment-variables) and then run the sample code. 

**Python:**
```
python samples/python/sample-app-find-and-protect.py
```

**Java:**
```
bash samples/java/sample-app-find-and-protect.sh
```

This produces the `samples/sample-data/output-protect.txt` file with protected, this is tokenized-like, values.

To get original data run:

**Python:**
```
python samples/python/sample-app-find-and-unprotect.py
```

**Java:**
```
bash samples/java/sample-app-find-and-unprotect.sh
```

This reads the `samples/sample-data/output-protect.txt` file and produces the `samples/sample-data/output-unprotect.txt` file with original values.

#### 9. Direct Protect and Unprotect from the CLI

Use the sample commands below to protect and unprotect data. Ensure that the [environment variables are exported](#4-setting-the-environment-variables) and then run the sample code.

For information about the users, roles, and data elements, refer to [*Understanding Users and Roles* and *Understanding the Data Elements*](https://developer.docs.protegrity.com/docs/running/#running-the-script-for-protecting-data)

**Python:**
```
# protect
python samples/python/sample-app-protection.py --input_data "John Smith" --policy_user superuser --data_element name --protect
```
```
# unprotect
python samples/python/sample-app-protection.py --input_data "<protected_data>" --policy_user superuser --data_element name --unprotect
```

**Java:**
```
# protect
bash samples/java/sample-app-protection.sh --input_data "John Smith" --policy_user superuser --data_element name --protect
```
```
# unprotect
bash samples/java/sample-app-protection.sh --input_data "<protected_data>" --policy_user superuser --data_element name --unprotect
```

The `<protected_data>` value is obtained from the output of the protect command.

Similarly, to encrypt and decrypt data, run the following commands:

**Python:**
```
# encrypt
python samples/python/sample-app-protection.py --input_data "John Smith" --policy_user superuser --data_element text --enc
```
```
# decrypt
python samples/python/sample-app-protection.py --input_data "<encrypted_data>" --policy_user superuser --data_element text --dec
```

**Java:**
```
# encrypt
bash samples/java/sample-app-protection.sh --input_data "John Smith" --policy_user superuser --data_element text --enc
```
```
# decrypt
bash samples/java/sample-app-protection.sh --input_data "<encrypted_data>" --policy_user superuser --data_element text --dec
```

The `<encrypted_data>` value is obtained from the output of the encrypt command.

For more information, run the help command:

**Python:**
```
python samples/python/sample-app-protection.py --help
```

**Java:**
```
bash samples/java/sample-app-protection.sh --help
```

### Additional settings for using the AI Developer Edition API Service
  
Prior registration is required to obtain credentials for accessing the AI Developer Edition API Service. The following samples demonstrate how to protect and unprotect data using the Protection APIs. The Protection APIs rely on authenticated access to the AI Developer Edition API Service.
- `samples/python/sample-app-find-and-protect.py`
- `samples/python/sample-app-protection.py`
- `samples/python/sample-app-find-and-unprotect.py`
- `samples/java/sample-app-find-and-protect.sh`
- `samples/java/sample-app-protection.sh`
- `samples/java/sample-app-find-and-unprotect.sh`

1.  Open a web browser.
2.  Navigate to [https://www.protegrity.com/developers/dev-edition-api ](https://www.protegrity.com/developers/dev-edition-api).
3.  Specify the following details:
    -   First Name
    -   Last Name
    -   Work Email
    -   Job Title
    -   Company Name
    -   Country
4.  Click the Terms & Conditions link and read the terms and conditions.
5.  Select the check box to accept the terms and conditions.
    The request is analyzed. After the request is approved, an API key and password to access the AI Developer Edition API Service is sent to the Work Email specified. Keep the API key and password safe. You need to export them to environment variables for using the AI Developer Edition API Service.  

    > **Note**: After completing registration, allow 1-2 minutes for the confirmation email to arrive. If you do not see it in your inbox, check your spam or junk folder before retrying.  
    
### Additional prerequisites for MacOS
  
MacOS requires additional steps for Docker and for systems with Apple Silicon chips. Complete the following steps before using AI Developer Edition. 

1.  Complete one of the following options to apply the settings.
    - For Colima: 
        1. Open a command prompt.
        2. Run the following command.
            ```
            colima start --vm-type vz --vz-rosetta --memory 8
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
            colima start --vm-type vz --vz-rosetta --memory 8
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
    5. Some services are profile enabled, ensure to use the `--profile` flag while starting the services.
       - Run the `docker compose up -d` from the `protegrity-developer-edition` directory to start the default services.
       - Run the `docker compose --profile synthetic up -d` from the `protegrity-developer-edition` directory to start the `synthetic` profiled services.

## 📄 Configuration

Edit `samples/config.json` to customize SDK behavior. 
Keys:
- `named_entity_map`: Optional mappings (friendly labels) used during redact/mask. [Supported Classification Entities](https://developer.docs.protegrity.com/docs/entities/)
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
        "PERSON": "PERSON",
        "LOCATION": "LOCATION",
        "SOCIAL_SECURITY_ID": "SSN",
        "PHONE_NUMBER": "PHONE",
        "AGE": "AGE",
        "USERNAME": "USERNAME"
    },
    "method": "redact"
}
```

### Service Endpoints (default using docker compose)
- Classification API: `http://localhost:${CLASSIFICATION_PORT:-8580}/pty/data-discovery/v1.1/classify`
- Semantic Guardrail API: `http://localhost:${SGR_PORT:-8581}/pty/semantic-guardrail/v1.1/conversations/messages/scan`
- Synthetic Data API: `http://localhost:${SYNTHETIC_DATA_PORT:-8095}/pty/synthetic-data/v1`

If you change published ports in `docker-compose.yml`, update `endpoint_url`. Also, if required, update the semantic guardrail URL in the scripts.

### Docker Compose Services
`docker-compose.yml` provisions:
- `pattern-provider-service` and `context-provider-service`: ML provider backends.
- `classification-service`: Exposes Data Discovery REST API. Uses port 8580 by default.
- `semantic-guardrail-service`: Conversation risk and PII scanning depends on classification. Uses port 8581 by default.
- `synthetic-data-service`: Synthetic Data service (--profile synthetic). Uses port 8095 by default.

Restart stack after changes to `docker-compose.yml` file from `protegrity-developer-edition` directory:
```
docker compose down && docker compose up -d
```

Check service logs for any errors from `protegrity-developer-edition` directory:
```
docker compose logs
```
## 📚 Documentation

- The Protegrity AI Developer Edition documentation is available at https://developer.docs.protegrity.com/.
- For more API reference and tutorials, refer to the Developer Portal at https://www.protegrity.com/developers.
- For more information about Data Discovery, refer to the [Data Discovery documentation]( https://docs.protegrity.com/data-discovery/1.1.1/docs/).
- For more information about Semantic Guardrails, refer to the [Semantic Guardrails documentation]( https://docs.protegrity.com/sem_guardrail/1.1.0/docs/).
- For more information about Synthetic Data, refer to the [Synthetic Data documentation]( https://docs.protegrity.com/synthetic-data/1.0.0/docs/).
- For more information about Application Protector Python, refer to the [Application Protector Python documentation]( https://docs.protegrity.com/protectors/10.0/docs/ap/ap_python/).
- For more information about Application Protector Java, refer to the [Application Protector Java documentation]( https://docs.protegrity.com/protectors/10.0/docs/ap/ap_java/).

## 📢 Community & Support

- Join the discussion on https://github.com/orgs/Protegrity-Developer-Edition/discussions.
- Anonymous downloads supported; registration required for participation.
- Issues / feature requests: please include sample script name & log snippet.

## 📜 License

See [LICENSE](https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition/blob/main/LICENSE) for terms and conditions.
