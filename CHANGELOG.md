# Changelog

All notable changes to the Protegrity AI Developer Edition project will be documented in this file.

## [1.1.0] - 2025-12-15

### 🎉 Major New Features

#### General Enhancements
- **README Improvements**: Added badges for improved visibility and quick access to key resources
- **Repository Restructuring**: Reorganized folders for better organization of samples and source code
- **Documentation Updates**: Comprehensive updates to getting started guides and feature documentation

#### Data Discovery v1.1.1
- **Structured Text Classification**: Added support for structured data classification
- **Harmonized Classifications**: Introduced categorized "harmonized" entity classifications for consistent data element mapping
- **Performance Improvements**: General enhancements to classification accuracy and speed
- **Enhanced Entity Mapping**: Updated entity-to-data-element mapping to align with Discover 1.1

#### Semantic Guardrails v1.1
- **Richer Examples**: Included more comprehensive examples in sample files for easier understanding
- **Vertical-Specific Models**: Added pre-trained support for additional industry verticals (Finance and Healthcare)
- **Jupyter Notebook Sample**: New interactive notebook for seamless evaluation and execution (`samples/python/sample-app-semantic-guardrails/`)
- **Port Updates**: Service now runs on port 8581 with updated image paths

#### Synthetic Data Generation (NEW)
- **Synthetic Data Feature**: New capability for generating synthetic test data to support testing and experimentation
- **Jupyter Notebook Sample**: Interactive notebook for synthetic data generation (`samples/python/sample-app-synthetic-data/`)
- **Docker Compose Profile**: New `synthetic` profile for orchestrating Synthetic Data services
- **Service Integration**: Seamless integration with existing AI Developer Edition infrastructure

#### Expanded Language & Platform Support
- **Java SDK Samples**: Complete Java implementation with CLI scripts for all major workflows
  - Data discovery, classification, protection, and redaction
  - Full source code provided for customization and compilation
  - Cross-platform compatibility (Linux, macOS, Windows)
- **Python SDK Updates**: Enhanced Python samples with better error handling and documentation
- **Dual Language Support**: Maintained feature parity between Python and Java implementations
- **Java 11+ Compatibility**: Ensured compatibility with modern Java versions
- **Python 3.12+ Support**: Updated minimum Python version requirement

### 🏗️ Architecture & Structure Changes

#### Repository Structure Enhancements
- **New Java Samples Directory**: Added `samples/java/` with comprehensive sample applications
  - `sample-app-find.sh` - PII discovery CLI
  - `sample-app-find-and-redact.sh` - Discovery and redaction workflow
  - `sample-app-find-and-protect.sh` - Discovery and protection workflow
  - `sample-app-find-and-unprotect.sh` - Discovery and unprotection workflow
  - `sample-app-protection.sh` - Direct protection/unprotection CLI
  - Windows `.bat` equivalents for all scripts
- **Enhanced Python Samples**: Updated `samples/python/` structure
  - New semantic guardrails Jupyter notebook
  - New synthetic data Jupyter notebook
- **Sample Data Organization**: Improved organization of configuration files and test data
- **Cross-Platform Scripts**: Ensured all shell scripts work on Linux, macOS, and Windows

#### Docker Compose Evolution
- **Multi-Profile Support**: Enhanced `docker-compose.yml` with profile-based orchestration
  - Default profile: Classification and Semantic Guardrail services
  - `synthetic` profile: Adds Synthetic Data generation services
- **Service Dependencies**: Proper orchestration and startup order management
- **Resource Optimization**: Improved container download and deployment efficiency

#### Service Endpoints
- **Classification API**: `http://localhost:8580/pty/data-discovery/v1.1/classify`
- **Semantic Guardrail API**: `http://localhost:8581/pty/semantic-guardrail/v1.1/conversations/messages/scan`
- **Synthetic Data API**: New endpoints for synthetic data generation (when using synthetic profile)

### 🔧 Enhanced Configuration & Service Features

#### Configuration Updates
- **Expanded Entity Mapping**: Enhanced `config.json` with additional entity types
- **Simplified Schema**: Streamlined configuration keys for easier customization
- **Java Configuration Support**: Added `config.ini` format for Java samples

#### Service Health & Logging
- **Improved Health Checks**: Enhanced service health verification procedures
- **Better Logging**: Improved logging options and error messages across all services
- **Restart Procedures**: Documented comprehensive docker compose management commands

### 🧑‍💻 Sample Applications Evolution

#### Java Sample Applications (NEW)
- Complete Java implementation of all Python sample workflows
- Maven-based build system with wrapper scripts
- Fat JAR generation for easy distribution
- Shell and batch scripts for cross-platform execution
- Full source code available for customization

#### Python Sample Enhancements
- Enhanced semantic guardrails samples with richer examples
- New Jupyter notebooks for interactive exploration
- Improved error handling and user feedback
- Better documentation and inline comments

#### Jupyter Notebook Integration
- **Semantic Guardrails Notebook**: Step-by-step guide for conversation scanning and risk assessment
- **Synthetic Data Notebook**: Interactive guide for generating synthetic test data
- **Prerequisites Documentation**: Clear instructions for Jupyter Lab setup

### 🤖 GenAI & AI Integration

#### Advanced AI Security Features
- **Improved Risk Scoring**: Enhanced semantic guardrail capabilities for multi-turn conversations
- **PII Scanning**: Advanced PII detection across conversation history
- **Privacy in Conversational AI**: Better support for securing LLM interactions
- **Prompt Sanitization**: Enhanced capabilities for cleaning LLM prompts

### 📚 Documentation & Developer Experience

#### Improved Getting Started Guides
- **Python Setup**: Updated prerequisites and installation instructions
- **Java Setup**: New comprehensive Java environment setup guide
- **Feature Documentation**: Detailed documentation for all new features
- **Troubleshooting**: Enhanced debugging guidance for common issues

#### Community Support
- **Issue Reporting**: Clear guidelines for reporting issues with sample scripts
- **Log Requirements**: Specified log snippet requirements for better issue resolution
- **Example Code**: More comprehensive code examples across documentation

### ⚙️ Infrastructure & Operations

#### Docker Compose Improvements
- **Profile-Based Orchestration**: Use `--profile synthetic` to enable synthetic data services
- **Optimized Downloads**: Reduced container download times
- **Better Resource Management**: Improved memory and CPU allocation
- **Port Configuration**: Flexible port management with environment variable support

### 🔄 Dependencies
- Updated `requirements.txt` with latest compatible versions
- Enhanced Maven dependencies for Java samples
- Updated Docker image references to latest stable versions

### ⚠️ Breaking Changes
None - This release maintains backward compatibility with 1.0.0

---

## [1.0.0] - 2025-09-30

### 🎉 Major New Features

#### Enhanced Data Protection Capabilities
- **Protection (Tokenization-like)**: New protect & unprotect functionality for specific data elements
- **Find and Protect**: Combined discovery and protection workflow via `sample-app-find-and-protect.py`
- **Direct Protection CLI**: New `sample-app-protection.py` for command-line protect/unprotect operations
- **PII Discovery**: Enhanced entity enumeration with confidence scores via `sample-app-find.py`

#### Semantic Guardrail Integration
- **GenAI Security**: Message & conversation level risk scoring for AI applications
- **Multi-turn Conversation Support**: PII scanning across conversation history
- **Dual Interface Support**: Both cURL and Python examples provided in `semantic-guardrail/` folder
- **Risk Assessment**: Comprehensive risk scoring for GenAI flows

### 🏗️ Architecture & Structure Changes

#### Repository Structure Enhancements
- **New Semantic Guardrail Module**: Added `semantic-guardrail/` directory
  - `sample-guardrail-command.sh` - cURL-based examples
  - `sample-guardrail-python.py` - Python integration examples
- **Enhanced Sample Applications**: Expanded `samples/` directory structure
  - **NEW**: `sample-app-find.py` - Dedicated PII discovery (list entities only)
  - **ENHANCED**: `sample-app-find-and-redact.py` - Improved redaction/masking
  - **NEW**: `sample-app-find-and-protect.py` - Combined find and protect workflow
  - **NEW**: `sample-app-protection.py` - Direct protection CLI interface
- **Enhanced Sample Data**: Expanded `sample-data/` structure
  - **RENAMED**: `sample-find-redact.txt` → `input.txt`
  - **NEW**: `output-redact.txt` - Produced by redact workflow
  - **NEW**: `output-protect.txt` - Produced by protect workflow
  - Dynamic file generation based on operation type

#### Docker Compose Orchestration
- **Multi-Service Architecture**: Enhanced `docker-compose.yml` with semantic guardrail services
- **ML Provider Backends**: Added `presidio-provider-service` & `roberta-provider-service`
- **Service Dependencies**: Proper orchestration between classification and semantic guardrail services
- **Port Management**: Classification (8580) + Semantic Guardrail (8581) services

### 🔧 Enhanced Configuration & Service Features

#### New Service Endpoints & Health Checks
- **Classification API**: `http://localhost:8580/pty/data-discovery/v1.0/classify`
- **Semantic Guardrail API**: `http://localhost:8581/pty/semantic-guardrail/v1.0/conversations/messages/scan`
- **Health Monitoring**: Built-in service health verification procedures
- **Service Restart**: Comprehensive docker compose management commands

### 🔐 Authentication & Registration Requirements

#### Protection API Authentication (NEW)
- **Registration Requirement**: Protection features now require user registration
- **Credential Management**: Support for email, password, and API key authentication
- **Environment Variables**: Secure credential handling for protection operations
```bash
export DEV_EDITION_EMAIL="<your_registered_email>"
export DEV_EDITION_PASSWORD="<your_portal_password>"
export DEV_EDITION_API_KEY="<your_api_key>"
```
- **Credential Verification**: Built-in verification commands for environment setup

### 📋 Sample Applications Evolution

#### From Single to Multiple Application Suite
**Previous:**
- Single sample: `sample-app-find-and-redact.py`
- Basic redaction workflow only
- Single output file

**Current (README.md):**
1. **Discovery Only**: `sample-app-find.py` - Entity enumeration with JSON output
2. **Find and Redact**: Enhanced redaction/masking with configurable output
3. **Find and Protect**: Tokenization-like protection workflow (requires registration)
4. **Direct Protection**: CLI-based protect/unprotect operations (requires registration)
5. **Semantic Guardrail (cURL)**: Risk assessment via command line
6. **Semantic Guardrail (Python)**: Multi-turn conversation security

#### Enhanced Workflow Documentation
- **Step-by-step Guides**: Detailed instructions for each sample application
- **Prerequisites Separation**: Clear distinction between basic and registration-required features
- **Output Documentation**: Detailed explanation of generated files and their purposes

### 🎯 GenAI & AI Integration (NEW)

#### Advanced AI Security Features
- **Conversation Risk Scoring**: Real-time risk assessment for AI conversations
- **Multi-turn PII Scanning**: Persistent PII detection across conversation history
- **GenAI Application Support**: Dedicated features for securing AI applications
- **Semantic Analysis**: Advanced semantic understanding for context-aware protection

### 📚 Documentation & Developer Experience

#### Enhanced Overview & Features
**Previous**: Basic data discovery and redaction
**Current**: Comprehensive platform with:
- Unstructured text classification, PII discovery, redaction, masking, and tokenization-like protection
- Semantic guardrails for GenAI applications
- Message/conversation risk scoring + PII scanning

#### Improved Developer Guidance
- **Detailed Setup Instructions**: Step-by-step guides with verification steps
- **Configuration Examples**: Comprehensive configuration documentation with examples
- **Troubleshooting**: Enhanced error handling and debugging guidance
- **Community Support**: Expanded issue reporting with sample script name & log snippet requirements

### ⚙️ Infrastructure & Operations

#### Docker Compose Evolution
**Previous**: Simple data discovery service startup
**Current**: Multi-service orchestration
- **Service Description**: Detailed explanation of each container service
- **Dependency Management**: Proper service startup order and dependencies
- **Resource Management**: Optimized container download and deployment
- **Port Configuration**: Flexible port management with environment variable support

### 🐛 Configuration Breaking Changes

#### Configuration Schema Updates
**Previous config.json structure:**
```json
{
  "api_endpoint": "http://localhost:8580/pty/data-discovery/v1.0/classify",
  "named_entity_map": { "CREDIT_CARD": "CCN", "DATE_TIME": "DATE" },
  "redaction_method": "redact",
  "masking_character": "#",
  "classification_threshold": 0.6,
  "enable_logging": true
}
```

**Current config.json structure:**
```json
{
    "masking_char": "#",
    "named_entity_map": {
        "USERNAME": "USERNAME", "STATE": "STATE",
        "PHONE_NUMBER": "PHONE", "SOCIAL_SECURITY_NUMBER": "SSN",
        "AGE": "AGE", "CITY": "CITY", "PERSON": "PERSON"
    },
    "method": "redact"
}
```

**Key Changes:**
- Simplified structure with smart defaults
- Expanded entity mapping
- Streamlined configuration keys
- Internal endpoint management

---

## [0.9.0] - README.md Baseline

### Features (Baseline)
- Basic unstructured text classification and PII redaction
- Single Docker service for data discovery
- Single sample application (`sample-app-find-and-redact.py`)
- Basic configuration via `config.json`
- Simple repository structure with `data-discovery/` and `samples/` folders

### Limitations (Baseline)
- No protection/unprotection capabilities
- No semantic guardrail functionality
- No authentication or registration system
- Single output format (redacted text only)
- Limited configuration options
- Basic docker compose setup

