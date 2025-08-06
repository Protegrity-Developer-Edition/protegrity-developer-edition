# Protegrity Developer Edition

Welcome to the `protegrity-developer-edition` repository, part of the Protegrity Developer Edition suite. This repository provides a self-contained experimentation platform for discovering and protecting sensitive data using Protegrity’s Data Discovery and Protection APIs.

## 🚀 Overview

This repository enables developers to:
- Rapidly set up a local environment using Docker Compose.
- Experiment with unstructured text classification and PII redaction.
- Integrate Protegrity APIs into GenAI and traditional applications.
- Use sample applications and data to understand integration workflows.

## 📦 Repository Structure

```text
.
├── CHANGELOG
├── CONTRIBUTIONS.md
├── LICENSE
├── README.md
├── data-discovery
│   ├── sample-classification-commands.sh
│   └── sample-classification-python.py
├── docker-compose.yml
└── samples
    ├── config.json
    ├── requirements.txt
    ├── sample-app-find-and-redact.py
    ├── sample-app-find.py
    └── sample-data
        └── sample-find-redact.txt
```

## 🧰 Features

- **Data Discovery**: REST-based classification of unstructured text using Data Discovery.
- **Data Protection**: Integration with a sample Python application for redaction or masking.
- **Sample App**: Demonstrates how to find and redact PII.
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
4.  Start the Data Discovery services in background. The dependent containers are large in size. Based on the network connection, the containers might take time to download and deploy.
    ```
    docker compose up -d
    ```
    Based on your configuration use the `docker-compose up -d` command.
5. Install the `protegrity-developer-python` module. It is recommended to install and activate the Python virtual environment before installing the module.
    ```bash
    pip install protegrity-developer-python
    ```
    The installation completes and the success message is displayed.


### Run the Sample application

Complete the steps provided here to run the sample application. The sample application reads the `sample-find-redact.txt` file, classifies and redacts the sensitive data, and the `output.txt` file is saved to the folder `samples/sample-data`.

1.  Open a command prompt.
2.  Navigate to the `protegrity-developer-edition` directory in the cloned location.
3.  Run the sample application.
    ```
    python samples/sample-app-find-and-redact.py
    ```
> **💡Note:** By default, all sensitive data is redacted, even if the entities are not mapped in the `named_entity_map` configuration.

## 📄 Configuration

Edit `samples/config.json` to customize the Python module:
- API endpoint (Default: `localhost`)
- Named entity mappings
- Redaction method (`redact` or `mask`, Default: `redact`)
- Masking Character (Default: `#`)
- Classification score threshold (Default: `0.6`)
- Enable logging (Default: `true`)
```json
{
  "api_endpoint": "http://localhost:8580/pty/data-discovery/v1.0/classify",
  "named_entity_map": {
        "CREDIT_CARD": "CCN",
        "DATE_TIME": "DATE"
   },
  "redaction_method": "redact",
  "masking_character": "#",
  "classification_threshold": 0.6,
  "enable_logging": true
}
```

## 📚 Documentation

- The Protegrity Developer Edition documentation is available at [http://developer.docs.protegrity.com/](http://developer.docs.protegrity.com/).
- For API reference and tutorials, visit the Developer Portal at [https://www.protegrity.com/developers](https://www.protegrity.com/developers).

## 📢 Community & Support

- Join the discussion on https://github.com/orgs/Protegrity-Developer-Edition/discussions.
- Anonymous downloads supported; registration required for participation.

## 📜 License

See [LICENSE](https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition/blob/main/LICENSE) for terms and conditions.
