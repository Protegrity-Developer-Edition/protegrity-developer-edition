# Changelog

All notable changes to the Protegrity Developer Edition project will be documented in this file.

## [Current Release]

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

## [Previous Release] - README.md Baseline

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

---

*Note: This release represents a major evolution from a simple data discovery and redaction tool to a comprehensive data protection and AI security platform with advanced semantic guardrail capabilities, authentication systems, and multiple workflow options.*