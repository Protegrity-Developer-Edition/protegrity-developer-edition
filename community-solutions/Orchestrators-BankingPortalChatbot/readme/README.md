# Banking Portal Chatbot — Protegrity Dual-Gate Demo

> **Version 1.0** · Protegrity Developer Edition  
> Guardrail · Discover · Protect · Unprotect

A secure AI-powered banking demo that processes sensitive customer data through
Protegrity's **dual-gate architecture** — ensuring PII is **never exposed** to an
LLM in clear text. The project ships two complementary applications:

| App | Port | Audience | Purpose |
|---|---|---|---|
| **TechnicalApp** | 5002 | Engineers / Demos | Configurable orchestrator explorer — switch LLM, orchestrator, data sources, Protegrity roles live |
| **BusinessCustomerApp** | 5003 | End Customers | Self-service banking portal — dashboard, account data, AI chat assistant |

Both apps share the same orchestration layer, Protegrity services, and protected
customer dataset (`customers_protected.json`).

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Apps](#running-the-apps)
6. [Running Tests](#running-tests)
7. [Architecture](#architecture)
8. [Project Structure](#project-structure)
9. [Orchestrators & Data Sources](#orchestrators--data-sources)
10. [Users & Roles](#users--roles)
11. [Further Reading](#further-reading)

---

## Quick Start

```bash
# 1. Clone and enter the project
cd BankingPortalChatbot

# 2. Install Protegrity (containers + Python SDK) — skip if already installed
bash scripts/setup_protegrity.sh

# 3. Install Python dependencies
pip install -r config/requirements.txt

# 4. Configure environment
cp .env.example .env   # edit with your API keys

# 5. Start both apps
python3 TechnicalApp/run.py &        # → http://localhost:5002
python3 BusinessCustomerApp/run.py & # → http://localhost:5003
```

---

## Prerequisites

- **Python 3.10+** (3.12 recommended)
- **Docker** + **Docker Compose ≥ 2.30** (for Protegrity containers)
- **Git**
- **LLM API keys** — at least one of:
  - [OpenAI](https://platform.openai.com/) (`OPENAI_API_KEY`)
  - [Anthropic](https://console.anthropic.com/) (`ANTHROPIC_API_KEY`)
  - [Groq](https://console.groq.com/) (`GROQ_API_KEY`)

### Protegrity Developer Edition

Sign up for a free account at [protegrity.com/developers/dev-edition-api](https://www.protegrity.com/developers/dev-edition-api).
You will receive credentials by email:

| Credential | Environment Variable |
|---|---|
| Email | `DEV_EDITION_EMAIL` |
| Password | `DEV_EDITION_PASSWORD` |
| API Key | `DEV_EDITION_API_KEY` |

---

## Installation

### Step 1 — Install Protegrity Developer Edition

The setup script checks for and installs both the **Docker containers** (Data Discovery + Semantic Guardrail) and the **Python SDK** (`protegrity-developer-python`):

```bash
# Check what's installed
bash scripts/setup_protegrity.sh --check

# Install missing components automatically
bash scripts/setup_protegrity.sh
```

**What it does:**

| Component | How it's installed |
|---|---|
| Protegrity Docker containers | Clones [protegrity-developer-edition](https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition), runs `docker compose up -d` |
| Python SDK | `pip install protegrity-developer-python` (falls back to cloning [protegrity-developer-python](https://github.com/Protegrity-Developer-Edition/protegrity-developer-python) and building from source) |

**Manual installation** (if you prefer):

```bash
# 1. Docker containers
git clone https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition.git
cd protegrity-developer-edition
docker compose up -d
cd ..

# 2. Python SDK
pip install protegrity-developer-python
```

After installation, the following services should be running:

| Service | Container | Port | Purpose |
|---|---|---|---|
| Data Discovery | `classification_service` | 8580 | PII classification & tokenization |
| Semantic Guardrail | `semantic_guardrail` | 8581 | Malicious prompt detection & risk scoring |
| Pattern Provider | `pattern_provider` | — | Classification patterns |
| Context Provider | `context_provider` | — | Classification context |

### Step 2 — Install Python dependencies

```bash
# (optional) Create a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Install all dependencies
pip install -r config/requirements.txt
```

### Protegrity Python SDK

Included in `config/requirements.txt` (`protegrity-developer-python>=1.1.0`):
- `find_and_protect()` — PII discovery + tokenization (Gate 1)
- `find_and_unprotect()` — detokenization (Gate 2)

---

## Configuration

### Environment Variables (`.env`)

```env
# Protegrity Developer Edition
DEV_EDITION_EMAIL=your-email@company.com
DEV_EDITION_PASSWORD=your-password
DEV_EDITION_API_KEY=your-api-key

# LLM API Keys (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...

# Protegrity service URLs (defaults)
CLASSIFY_URL=http://localhost:8580/pty/data-discovery/v1.1/classify
SGR_URL=http://localhost:8581/pty/semantic-guardrail/v1.1/conversations/messages/scan
SGR_PROCESSOR=financial

# App ports (defaults)
TECH_PORT=5002
BUSINESS_PORT=5003
```

### TechnicalApp Runtime Settings (UI)

| Setting | Options | Default |
|---|---|---|
| Orchestrator | direct, langgraph, crewai, llamaindex | direct |
| LLM Provider | openai, anthropic, groq | openai |
| Data Sources | KB, RAG, KG | KB only |
| Semantic Guardrail | on / off | on |
| Data Discovery | on / off | on |
| Protegrity User | superuser, Marketing, Finance, Support | superuser |
| Show Trace | on / off | on |

---

## Running the Apps

```bash
# Start individually
python3 TechnicalApp/run.py        # → http://localhost:5002
python3 BusinessCustomerApp/run.py # → http://localhost:5003
```

**Full URLs:**

| App | Login URL | Dashboard URL |
|---|---|---|
| **TechnicalApp** | `http://localhost:5002/tech/login` | `http://localhost:5002/tech/dashboard` |
| **BusinessCustomerApp** | `http://localhost:5003/bank/login` | `http://localhost:5003/bank/dashboard` |

> **Tip:** If ports are already in use from a previous run, kill them first:  
> `fuser -k 5002/tcp 5003/tcp`

---

## Running Tests

### Unit Tests (pytest)

```bash
# Run all 68 unit tests
python3 -m pytest tests/ -v

# Individual test files
python3 -m pytest tests/test_orchestration.py -v   # orchestration layer
python3 -m pytest tests/test_orchestrators.py -v   # config & gates
python3 -m pytest tests/test_banking_service.py -v # data service
python3 -m pytest tests/test_pii_tags.py -v        # PII tag format
python3 -m pytest tests/test_conversation_history.py -v
```

**68 unit tests** across 5 files — all run without live Protegrity services or LLM APIs.

### TechnicalApp Integration Tests

```bash
# App must be running on port 5002
python3 tests/test_app_integration.py --suite quick       # smoke (1 customer)
python3 tests/test_app_integration.py --suite prompts     # all 7 pre-prompts
python3 tests/test_app_integration.py --suite matrix      # all orchestrator×LLM combos
python3 tests/test_app_integration.py --suite customers   # all 15 customers
python3 tests/test_app_integration.py --suite datasources # data source variations
python3 tests/test_app_integration.py --suite roles       # Protegrity user roles
python3 tests/test_app_integration.py --suite full        # 252 tests (7×3×12)
python3 tests/test_app_integration.py --suite all         # all except full
```

### BusinessCustomerApp Integration Tests

```bash
# App must be running on port 5003
python3 tests/test_business_app_integration.py --suite quick   # smoke (auth, summary, chat)
python3 tests/test_business_app_integration.py --suite login   # all 15 customers login+PII check
python3 tests/test_business_app_integration.py --suite chat    # pre-prompts × 3 customers
python3 tests/test_business_app_integration.py --suite full    # all of the above
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Shared Orchestration Layer                       │
│                                                                     │
│   User Query ──▶ GATE 1 ──▶ Orchestrator ──▶ GATE 2 ──▶ Response   │
│                    │              │              │                   │
│                    ├─ Guardrail   ├─ KB lookup   └─ Unprotect /     │
│                    ├─ Discover    ├─ RAG search      Redact         │
│                    └─ Protect     ├─ KG query                       │
│                                  └─ LLM call                       │
├─────────────────────────────────────────────────────────────────────┤
│  TechnicalApp (5002)          │  BusinessCustomerApp (5003)         │
│  Engineers / Demos            │  End Customers                      │
│  Configurable orchestrators   │  LangGraph + Protegrity fixed        │
│  All Protegrity roles         │  Dashboard + protected data          │
└─────────────────────────────────────────────────────────────────────┘

Protegrity Services:
  ├─ Data Discovery     (port 8580) — PII classification
  ├─ Semantic Guardrail (port 8581) — malicious prompt detection
  └─ Developer Edition  (cloud)     — tokenize / detokenize PII
```

### Dual-Gate Data Flow

```
customers_protected.json  ──▶  KB files (pre-tokenized)
         │                              │
         ▼                              ▼
    [PERSON]Xk9[/PERSON]    ┌─────────────────────┐
    [EMAIL]abc@x[/EMAIL]    │   Gate 1 (Input)     │  user query → protect PII
    [CREDIT_CARD]...[/]     │   Gate 2 (Output)    │  LLM answer → unprotect
                            └─────────────────────┘
                                       │
                        LLM never sees real PII — only tokens
```

1. **Data at rest**: `customers_protected.json` stores all PII as Protegrity tokens
2. **Gate 1**: Guardrail scan + tokenize any PII in the user's message
3. **Orchestrator**: Works entirely with tokens — KB, RAG, KG, LLM all see only tokens
4. **Gate 2**: Final response detokenized by the Protegrity SDK before reaching the user

---

## Project Structure

```
BankingPortalChatbot/
├── TechnicalApp/
│   ├── app.py                  # Flask app — configurable orchestrator demo
│   └── run.py                  # Launcher (port 5002)
├── BusinessCustomerApp/
│   ├── app.py                  # Flask app — customer portal + AI chat
│   ├── run.py                  # Launcher (port 5003)
│   ├── templates/              # Jinja2 HTML templates
│   └── static/                 # CSS, JS, assets
├── orchestrators/
│   ├── base.py                 # BaseOrchestrator + PipelineResult
│   ├── factory.py              # Orchestrator factory
│   ├── direct_orch.py          # Direct LLM call
│   ├── langgraph_orch.py       # LangGraph state machine
│   ├── crewai_orch.py          # CrewAI multi-agent
│   └── llamaindex_orch.py      # LlamaIndex query engine
├── services/
│   ├── protegrity_guard.py     # Gate 1 & Gate 2 implementation
│   ├── banking_service.py      # Customer data access (protected data)
│   ├── conversation_history.py # Chat history persistence
│   └── protegrity_dev_edition_helper.py  # SDK session management
├── config/
│   ├── orchestration_config.py # LLM, orchestrator, gate settings
│   ├── protegrity_config.py    # Entity mappings, API URLs
│   ├── requirements.txt        # Python dependencies
│   ├── users.json              # TechnicalApp engineer accounts
│   └── customer_users.json     # BusinessCustomerApp customer accounts
├── common/
│   ├── protegrity_gates.py     # Gate 1 / Gate 2 wrappers
│   ├── knowledge_graph.py      # NetworkX graph queries
│   └── rag_retriever.py        # ChromaDB vector search
├── llm_providers/
│   └── factory.py              # OpenAI / Anthropic / Groq factory
├── banking_data/
│   ├── customers.json          # Raw (unprotected) customer data
│   ├── customers_protected.json # Protegrity-tokenized data (used at runtime)
│   ├── knowledge_base/         # Pre-tokenized per-customer KB files
│   ├── knowledge_graph.json    # Serialised NetworkX graph
│   └── knowledge_prep/         # Data protection pipeline scripts
├── chroma_db/                  # ChromaDB vector store (auto-generated)
├── tests/
│   ├── smoke_test.py                        # Quick offline smoke test
│   ├── test_orchestration.py               # Orchestration layer unit tests
│   ├── test_orchestrators.py               # Config & gate unit tests
│   ├── test_banking_service.py             # Banking service unit tests
│   ├── test_pii_tags.py                    # PII token format tests
│   ├── test_conversation_history.py        # History persistence tests
│   ├── test_app_integration.py             # TechnicalApp integration (252 tests)
│   └── test_business_app_integration.py    # BusinessCustomerApp integration
├── readme/
│   ├── README.md                    # This file
│   ├── readme_TechnicalApp.md       # TechnicalApp deep-dive
│   ├── readme_BusinessCustomerApp.md # BusinessCustomerApp deep-dive
│   ├── business_readme.md           # Business value overview
│   ├── readme_for_Orchestrators.md  # Orchestrator architecture
│   ├── readme_for_Protegrity.md     # Protegrity SDK integration
│   ├── readme_for_Claude.md         # AI assistant reference
│   ├── readme_Direct.md             # Direct orchestrator
│   ├── readme_LangGraph.md          # LangGraph orchestrator
│   ├── readme_CrewAI.md             # CrewAI orchestrator
│   └── readme_LlamaIndex.md         # LlamaIndex orchestrator
├── scripts/
│   ├── setup_protegrity.sh        # Auto-install Protegrity containers + SDK
│   ├── start_apps.sh              # Start both apps
│   └── bump_version.sh            # Version bump helper
├── .env                        # Environment variables (not in git)
├── pyproject.toml              # Pytest configuration
└── VERSION                     # 1.0
```

---

## Orchestrators & Data Sources

| Orchestrator | KB | RAG | KG | Description |
|---|---|---|---|---|
| **direct** | ✅ | ❌ | ❌ | Single LLM call with KB context |
| **langgraph** | ✅ | ✅ | ✅ | State machine — all data sources |
| **crewai** | ✅ | ❌ | ✅ | Multi-agent: Retriever + Responder |
| **llamaindex** | ✅ | ✅ | ❌ | Query engine with vector search |

All orchestrators receive and return **tokenized data only** — PII protection is
handled exclusively by the two gates, not inside the orchestrator.

---

## Users & Roles

### TechnicalApp (`config/users.json`)

| Username | Password | Role |
|---|---|---|
| `admin` | `Adm!n@S3cure2026` | Technical Administrator |
| `engineer` | `Eng#Pr0tegrity!` | Integration Engineer |
| `langgraph` | `LangGraph#2026` | LangGraph Engineer |
| `crewai` | `CrewAI#2026` | CrewAI Engineer |
| `llamaindex` | `LlamaIndex#2026` | LlamaIndex Engineer |

### BusinessCustomerApp (`config/customer_users.json`)

15 demo customers: `allison100`/`pass100` through `tanya114`/`pass114`.  
A clickable credentials panel is shown on the login page.

---

## Further Reading

| File | Description |
|---|---|
| [readme_TechnicalApp.md](readme_TechnicalApp.md) | Goals, architecture, and features of the TechnicalApp |
| [readme_BusinessCustomerApp.md](readme_BusinessCustomerApp.md) | Goals, architecture, and features of the BusinessCustomerApp |
| [readme_for_Orchestrators.md](readme_for_Orchestrators.md) | Orchestrator internals and data flow |
| [readme_for_Protegrity.md](readme_for_Protegrity.md) | Protegrity SDK integration and entity mappings |
| [readme_for_Claude.md](readme_for_Claude.md) | Comprehensive technical reference for AI assistants |
| [readme_Direct.md](readme_Direct.md) | Direct orchestrator |
| [readme_LangGraph.md](readme_LangGraph.md) | LangGraph orchestrator |
| [readme_CrewAI.md](readme_CrewAI.md) | CrewAI orchestrator |
| [readme_LlamaIndex.md](readme_LlamaIndex.md) | LlamaIndex orchestrator |

---

*Protegrity Developer Edition is free for development and demonstration purposes.*  
*See [protegrity.com/developer-edition](https://www.protegrity.com/developer-edition) for terms.*
