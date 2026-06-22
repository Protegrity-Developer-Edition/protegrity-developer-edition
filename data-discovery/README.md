# Data Discovery

Classify and discover sensitive data in your datasets using Protegrity's Data Discovery API.

## What is Data Discovery?

Data Discovery is a feature that identifies and detects sensitive information within text and tabular data. It helps you understand what sensitive data exists in your systems, which is the first step towards protecting it.

## Directory Structure

```
data-discovery/
├── samples/                # Example implementations by language
│   ├── python/             # Python-based discovery scripts
│   ├── bash/               # Shell-based discovery scripts
│   └── jupyter/            # Jupyter notebook examples
├── data/                   # Sample input data for discovery demos
├── docker-compose.yml      # Service definition for data-discovery
└── README.md              # This file
```

## Samples

### Python Samples

- **sample-classification-python-text.py** - Classify sensitive data in text content
- **sample-classification-python-tabular.py** - Classify sensitive data in tabular/CSV content
- **sample-redaction-python.py** - Redact discovered sensitive data

### Bash Samples

- **sample-classification-bash-text.sh** - Shell script for classifying text data
- **sample-classification-bash-tabular.sh** - Shell script for classifying tabular data
- **sample-redaction-bash.sh** - Shell script for redacting sensitive data

### Jupyter Notebooks

- **sample-classification-jupyter-text.ipynb** - Interactive notebook for text classification
- **sample-classification-jupyter-tabular.ipynb** - Interactive notebook for tabular classification
- **sample-redaction-jupyter-text.ipynb** - Interactive notebook for data redaction

## Sample Data

The `data/` directory contains sample datasets used by the discovery examples:

- **input.csv** - Sample tabular data for classification and redaction examples

## Getting Started

### Prerequisites

- Docker CLI, Docker Compose and Python installed, please see [AI Developer Edition, Pre-requisites Guide](https://developer.docs.protegrity.com/docs/install/deved_prereq/).
- Data Discovery services running, see [Docker Compose Setup](#docker-compose-setup) below.
- Bash >= 5.1.8 and curl >= 7.76.1 (for shell samples)
- JupyterLab >= 4.5.6 (for notebook samples)

### Running Discovery Samples

#### Python

```bash
cd samples/python/
python sample-classification-python-text.py
python sample-classification-python-tabular.py
python sample-redaction-python.py
```

#### Bash

```bash
cd samples/bash/
./sample-classification-bash-text.sh
./sample-classification-bash-tabular.sh
./sample-redaction-bash.sh
```

#### Jupyter Notebooks

- Start Jupyter Lab.
- Navigate into the `samples/jupyter/` directory:
- Open each notebook in the Jupyter Lab and run the cells to see the data-discovery process in action.

```bash
sample-classification-jupyter-text.ipynb
sample-classification-jupyter-tabular.ipynb
sample-redaction-jupyter-text.ipynb

```


## Docker Compose Setup

The `docker-compose.yml` file in this directory defines the service containers needed for data discovery. Start the services with:

```bash
docker-compose up -d
```

## API Reference

For complete documentation on the Data Discovery API, refer to the [Data Discovery Documentation](https://docs.protegrity.com/data-discovery/2.0.0/docs/restapi/).

## Support

For issues, questions, or feature requests, please refer to the main project documentation or contact the Protegrity team.
