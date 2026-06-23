# Protegrity Integration — Technical Reference

> **How Protegrity features are called and utilized in the Banking Portal Chatbot.**
>
> Version: 0.8.1 | Last updated: 2026-03-31

---

## 1. Architecture Overview

The chatbot implements a **Dual-Gate** security model where all user input and LLM output passes through Protegrity services:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RUNTIME PIPELINE                             │
│                                                                     │
│  User Message                                                       │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────┐                    │
│  │  GATE 1 — Input Protection                  │                    │
│  │                                             │                    │
│  │  Step 1: Semantic Guardrail (REST API)       │                    │
│  │    POST /pty/semantic-guardrail/v1.1/...    │                    │
│  │    → risk_score + outcome (accepted/rejected)│                    │
│  │    → BLOCK if risk > threshold              │                    │
│  │                                             │                    │
│  │  Step 2: PII Discovery & Tokenization (SDK) │                    │
│  │    sdk.find_and_protect(text)               │                    │
│  │    → "John Smith" → "[PERSON]xK9mQ[/PERSON]"│                    │
│  └─────────────────────────────────────────────┘                    │
│       │                                                             │
│       ▼  (tokenized message)                                        │
│  ┌──────────────────────┐                                           │
│  │  Pre-Protected KB     │  (already tokenized at build time)       │
│  │  RAG / Knowledge Graph│  (all contain tokenized PII)             │
│  └──────────────────────┘                                           │
│       │                                                             │
│       ▼  (tokenized context + tokenized query)                      │
│  ┌──────────────────────┐                                           │
│  │  LLM (OpenAI / etc.) │  ← never sees real PII                   │
│  └──────────────────────┘                                           │
│       │                                                             │
│       ▼  (tokenized response)                                       │
│  ┌─────────────────────────────────────────────┐                    │
│  │  GATE 2 — Output Unprotection               │                    │
│  │                                             │                    │
│  │  sdk.find_and_unprotect(text)               │                    │
│  │  → "[PERSON]xK9mQ[/PERSON]" → "John Smith" │                    │
│  │                                             │
│  │  Per-user policy: superuser sees all,       │                    │
│  │  Marketing/Finance/Support see redacted     │                    │
│  └─────────────────────────────────────────────┘                    │
│       │                                                             │
│       ▼                                                             │
│  Final Response (PII restored per user policy)                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Protegrity Services Used

| Service | Type | Endpoint | Purpose |
|---------|------|----------|---------|
| **Developer Edition Auth** | REST | `POST /pty/dev-edition/v1/sessions` | Session token for API access |
| **Semantic Guardrail** | REST | `POST /pty/semantic-guardrail/v1.1/conversations/messages/scan` | Risk scoring on user input |
| **Data Discovery** | SDK | `sdk.find_and_protect(text)` | PII classification & tokenization |
| **Data Protection** | SDK | `sdk.find_and_unprotect(text)` | Detokenization (restore PII) |
| **Protector** | SDK | `Protector().create_session(user).protect(value, de)` | Offline batch tokenization |

---

## 3. File Map — Where Protegrity Code Lives

```
services/
├── protegrity_guard.py              # Core dual-gate implementation (786 lines)
│   ├── ProtegrityGuard class        # Main guard — all gate operations
│   ├── GateResult dataclass         # Standardized return type
│   ├── register_tokens_from_context # Token map for Gate 2 resolution
│   └── get_guard()                  # Thread-safe singleton
│
├── protegrity_config.py             # Entity-to-data-element mappings
│   ├── ENTITY_TO_DATA_ELEMENT       # PERSON→string, EMAIL→email, etc.
│   ├── FIELD_PROTECTION_MAP         # JSON field→(tag, data_element) map
│   ├── COMBINED_ENTITY_MAPPINGS     # Multi-entity type handling
│   └── get_data_element()           # Lookup function
│
├── protegrity_dev_edition_helper.py # Session lifecycle management
│   ├── _login()                     # Authenticate with Dev Edition
│   ├── get_session_credentials()    # Token + headers (auto-refresh)
│   └── protegrity_request()         # HTTP wrapper with 401 retry
│
common/
├── protegrity_gates.py              # Clean wrapper API
│   ├── Gate1Result / Gate2Result    # Simplified dataclasses
│   ├── gate1_protect()             # Gate 1 entry point
│   ├── gate2_unprotect()           # Gate 2 entry point
│   └── register_context_tokens()   # Register KB tokens for Gate 2
│
banking_data/knowledge_prep/
└── protect_customer_data.py         # Offline batch protection script
    ├── protect_customer()           # Tokenize one customer record
    └── protect_address()            # Address component protection
```

---

## 4. Protegrity SDK — `protegrity_developer_python`

### 4.1 SDK Initialization

**File:** `services/protegrity_guard.py`, lines 85–150

```python
import protegrity_developer_python as sdk

sdk.configure(
    endpoint_url="http://localhost:8580",
    named_entity_map=ENTITY_TO_DATA_ELEMENT,      # from protegrity_config.py
    classification_score_threshold=0.5,             # PII discovery confidence
)
```

The SDK is initialized once via `_configure_sdk()` and cached. Thread-safe initialization uses `_sdk_lock` (threading.Lock).

### 4.2 Entity-to-Data-Element Mapping

The SDK requires a mapping from PII entity types to Protegrity data elements. This is defined in `services/protegrity_config.py`:

| Entity Type | Data Element | Example Value |
|------------|-------------|---------------|
| `PERSON` | `string` | John Smith |
| `EMAIL_ADDRESS` | `email` | john@example.com |
| `PHONE_NUMBER` | `phone` | 555-123-4567 |
| `SOCIAL_SECURITY_ID` | `ssn` | 123-45-6789 |
| `CREDIT_CARD` | `ccn` | 4111111111111111 |
| `LOCATION` | `address` | 123 Main St |
| `DATETIME` | `datetime` | 1990-01-01 |
| `BANK_ACCOUNT` | `number` | 9697354961 |
| `IP_ADDRESS` | `address` | 192.168.1.1 |
| `ORGANIZATION` | `string` | Acme Corp |
| `URL` | `address` | https://example.com |
| `TAX_ID` | `ssn` | 12-3456789 |
| `NATIONAL_ID` | `ssn` | AB123456 |

Combined entity types (when classifier returns multiple labels):

| Combined Entity | Resolved Data Element |
|----------------|----------------------|
| `URL\|EMAIL_ADDRESS` | `email` |
| `EMAIL_ADDRESS\|USERNAME` | `email` |
| `PERSON\|LOCATION` | `string` |
| `CREDIT_CARD\|PERSON` | `ccn` |
| `DATETIME\|SOCIAL_SECURITY_ID` | `ssn` |

---

## 5. Gate 1 — Input Protection (Detail)

**Entry point:** `ProtegrityGuard.gate1_input()` (line 554)

```python
def gate1_input(self, text, *, risk_threshold=0.7, classify_threshold=None) -> GateResult:
```

### Step 1: Semantic Guardrail Check

**Method:** `semantic_guardrail_check()` (line 332)

**API Call:**
```
POST http://localhost:8581/pty/semantic-guardrail/v1.1/conversations/messages/scan
```

**Request Body:**
```json
{
  "messages": [{
    "from": "user",
    "to": "ai",
    "content": "user's message text",
    "processors": ["financial"]
  }]
}
```

**Response:**
```json
{
  "messages": [{
    "score": 0.35,
    "outcome": "accepted",
    "processors": [{
      "name": "financial",
      "score": 0.35,
      "outcome": "accepted",
      "explanation": "Message appears to be a standard banking inquiry."
    }]
  }]
}
```

**Logic:**
- Extract `score` from response → compare against `risk_threshold` (default 0.7)
- If `score > risk_threshold` → set `risk_accepted = False` → message is **BLOCKED**
- The `explanation` from the processor is included in the pipeline trace

### Step 2: PII Discovery & Tokenization

**Method:** `find_and_protect()` (line 425)

**SDK Call:**
```python
sdk.configure(classification_score_threshold=classify_threshold)  # default 0.5
result = sdk.find_and_protect(text)
# "My SSN is 123-45-6789" → "My SSN is [SOCIAL_SECURITY_ID]aB3xQ9[/SOCIAL_SECURITY_ID]"
```

**Parameters:**
- `classify_threshold` (float, default 0.5): Minimum confidence for PII classification. Lower = detect more PII, higher = only high-confidence matches.

**Output format:** `[ENTITY_TAG]tokenized_value[/ENTITY_TAG]`

### Combined Flow in `gate1_input()`:

```
User message
    │
    ├─ guardrail_enabled? ──▶ semantic_guardrail_check()
    │                            │
    │                       risk > threshold? ──▶ BLOCKED (return immediately)
    │                            │
    │                       risk accepted ──▶ find_and_protect()
    │
    ├─ discovery_only? ──▶ find_and_protect() (skip guardrail)
    │
    └─ both disabled? ──▶ pass-through (no protection)
```

### Configurable Thresholds (UI Controls)

| Control | Config Key | Default | What It Controls |
|---------|-----------|---------|-----------------|
| Guardrail Risk Threshold | `risk_threshold` | 0.7 | Semantic Guardrail blocking sensitivity |
| PII Classification Confidence | `classify_threshold` | 0.5 | PII Discovery detection sensitivity |

---

## 6. Gate 2 — Output Unprotection (Detail)

**Entry point:** `ProtegrityGuard.gate2_output()` (line 566)

```python
def gate2_output(self, text, *, restore=True) -> GateResult:
    if restore:
        return self.find_and_unprotect(text)
    return self.find_and_redact(text)
```

### Token Registration

Before Gate 2 can detokenize the LLM response, it needs to know which tokens exist. The token map is built from the KB/RAG/KG context:

**Method:** `register_tokens_from_context()` (line 191)

```python
def register_tokens_from_context(text):
    """Extract all [TAG]value[/TAG] patterns and store in _token_map."""
    pattern = r'\[([A-Z_]+)\]([^\[]+?)\[/\1\]'
    for match in re.finditer(pattern, text):
        entity_type, token_value = match.group(1), match.group(2)
        _token_map[token_value] = entity_type
```

This is called in `app.py` after combining all context sources (KB + RAG + KG) and before calling the LLM. This ensures Gate 2 can recognize and detokenize any token the LLM echoes back.

### Detokenization

**Method:** `find_and_unprotect()` (line 478)

**SDK Call:**
```python
result = sdk.find_and_unprotect(tagged_text)
# "[PERSON]xK9mQ[/PERSON]" → "John Smith"
```

The method also handles smart token detection: it checks if a value inside tags is a likely token (not plain text that happens to be wrapped). Uses `_is_likely_token()` to validate before sending to the SDK.

### Per-User Policy (Role-Based Access)

**Method:** `_user_unprotect()` in `TechnicalApp/app.py` (line 145)

| User Role | Behavior |
|-----------|----------|
| `superuser` | Full detokenization — sees all real PII |
| `Marketing` | Limited — some fields remain tokenized |
| `Finance` | Limited — different field visibility |
| `Support` | Limited — restricted PII access |

```python
def _user_unprotect(text, protegrity_user):
    if protegrity_user == "superuser":
        return guard.gate2_output(text, restore=True).transformed_text
    else:
        # Per-user detokenization via role-based Protegrity policy
        from protegrity_user_gate import user_unprotect
        return user_unprotect(text, protegrity_user)
```

---

## 7. Offline Batch Protection

**Script:** `banking_data/knowledge_prep/protect_customer_data.py`

Used to pre-tokenize customer data before it enters the knowledge base. This is a **build-time** operation, not runtime.

### Protector SDK Usage

```python
from appython import Protector

protector = Protector()
session = protector.create_session("superuser")

# Protect individual fields
protected_name = session.protect("John Smith", "string")
protected_email = session.protect("john@example.com", "email")
protected_ssn = session.protect("123-45-6789", "ssn")
protected_card = session.protect("4111111111111111", "ccn")
```

### Fields Protected vs. Plain

| Field | Protected? | Tag | Data Element |
|-------|-----------|-----|-------------|
| `name` | ✅ Yes | `[PERSON]` | `string` |
| `email` | ✅ Yes | `[EMAIL_ADDRESS]` | `email` |
| `phone` | ✅ Yes | `[PHONE_NUMBER]` | `phone` |
| `ssn` | ✅ Yes | `[SOCIAL_SECURITY_ID]` | `ssn` |
| `dob` | ✅ Yes | `[DATETIME]` | `datetime` |
| `address` | ✅ Yes | `[LOCATION]` | `address` |
| `card_number` | ✅ Yes | `[CREDIT_CARD]` | `ccn` |
| `account_number` | ❌ No | — | — (kept as identifier) |
| `routing_number` | ❌ No | — | — |
| `balance` | ❌ No | — | — |
| `account_id` | ❌ No | — | — |
| `transaction dates` | ❌ No | — | — |
| `merchants` | ❌ No | — | — |
| `amounts` | ❌ No | — | — |

### Address Protection (Component-Level)

Addresses are parsed into components and each part is tokenized separately:

```
"123 Main St, Springfield, IL 62701"
    ↓
"[LOCATION]aB3x[/LOCATION] [LOCATION]Qm9K2[/LOCATION], [LOCATION]pL7nR[/LOCATION], [LOCATION]vW[/LOCATION] [LOCATION]dF8mY[/LOCATION]"
```

### Build Pipeline

```bash
# Step 1: Protect raw customer data
python banking_data/knowledge_prep/protect_customer_data.py

# Step 2: Generate knowledge base text files
python banking_data/knowledge_prep/generate_knowledge_base.py

# Step 3: Rebuild ChromaDB and Knowledge Graph (happens on app startup)
```

---

## 8. Token Format — PII Tag Specification

All tokenized PII follows this format:

```
[ENTITY_TAG]tokenized_value[/ENTITY_TAG]
```

### Examples from Live Data

```
Name:    [PERSON]C4idPSY LLxx[/PERSON]
Email:   [EMAIL_ADDRESS]gBlgez41oo3t@example.org[/EMAIL_ADDRESS]
Phone:   [PHONE_NUMBER]728.751.7930[/PHONE_NUMBER]
SSN:     [SOCIAL_SECURITY_ID]996-25-6169[/SOCIAL_SECURITY_ID]
Card:    [CREDIT_CARD]1158885255938243[/CREDIT_CARD]
Address: [LOCATION]yZiXS[/LOCATION] [LOCATION]z1efu Tcy14SDR[/LOCATION]
DOB:     [DATETIME]1749-05-23[/DATETIME]
```

The LLM is instructed via system prompt to **preserve these tags exactly** in its responses. Gate 2 then detokenizes them before display.

---

## 9. Session & Authentication Management

**File:** `services/protegrity_dev_edition_helper.py`

### Login Flow

```
POST {PROTEGRITY_HOST}/pty/dev-edition/v1/sessions
Headers: { "x-api-key": DEV_EDITION_API_KEY }
Body:    { "email": DEV_EDITION_EMAIL, "password": DEV_EDITION_PASSWORD }
Response: { "sessionToken": "..." }
```

### Session Lifecycle

| Parameter | Value |
|-----------|-------|
| Session lifetime | ~25 minutes |
| Refresh window | 5 minutes before expiry |
| Max retries on failure | 3 |
| Retry backoff | 2s, 4s, 6s (exponential) |

### Resilience Pattern

```
API call
    │
    ├─ 200 OK → return result
    │
    ├─ 401 Unauthorized → invalidate_session() → re-login → retry
    │
    ├─ Network error → retry with backoff (up to 3x)
    │
    └─ All retries exhausted → fallback to mock protection
```

The `_sdk_call_with_retry()` method in `protegrity_guard.py` wraps all SDK calls with this pattern, ensuring automatic session renewal and graceful degradation.

---

## 10. Environment Variables

```bash
# ── Developer Edition Authentication ──
DEV_EDITION_EMAIL=           # Login email for Developer Edition
DEV_EDITION_PASSWORD=        # Login password
DEV_EDITION_API_KEY=         # API key (x-api-key header)

# ── Protegrity Service Endpoints ──
CLASSIFY_URL=http://localhost:8580/pty/data-discovery/v1.1/classify
SGR_URL=http://localhost:8581/pty/semantic-guardrail/v1.1/conversations/messages/scan
PROTEGRITY_HOST=http://localhost:8580
DETOKENIZE_URL=http://localhost:8580/pty/data-protection/v1.1/detokenize
PROTEGRITY_API_TIMEOUT=30

# ── LLM Provider Keys ──
OPENAI_API_KEY=              # OpenAI API key
ANTHROPIC_API_KEY=           # Anthropic API key
GROQ_API_KEY=                # Groq API key
```

---

## 11. GateResult Dataclass

All Protegrity operations return a standardized `GateResult`:

```python
@dataclass
class GateResult:
    original_text: str = ""
    transformed_text: str = ""
    risk_score: float = 0.0
    risk_accepted: bool = True
    elements_found: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
```

| Field | Gate 1 Usage | Gate 2 Usage |
|-------|-------------|-------------|
| `original_text` | Raw user input | Tokenized LLM output |
| `transformed_text` | Tokenized user input | Detokenized response |
| `risk_score` | Guardrail risk score (0.0–1.0) | 0.0 |
| `risk_accepted` | `False` if blocked | `True` |
| `elements_found` | List of detected PII entities | List of resolved tokens |
| `metadata` | `outcome`, `explanation` from guardrail | Resolution details |

---

## 12. Thread Safety

| Resource | Lock | Location |
|----------|------|----------|
| `_token_map` (global token registry) | `_token_map_lock` | `protegrity_guard.py` |
| SDK initialization | `_sdk_lock` | `protegrity_guard.py` |
| Guard singleton | `_guard_lock` | `protegrity_guard.py` |
| Dev Edition session state | `_dev_edition_available` flag | `protegrity_dev_edition_helper.py` |

---

## 13. Fallback & Graceful Degradation

The system operates even when Protegrity services are unavailable:

| Scenario | Behavior |
|----------|----------|
| SDK not installed | Uses `_mock_find_and_protect()` — wraps values in tags without real tokenization |
| Dev Edition auth fails | Falls back to unauthenticated requests |
| Guardrail API down | Logs warning, accepts message with risk_score=0 |
| Detokenization fails | `_strip_pii_tags()` removes tag wrappers, shows tokenized values |
| Session expired (401) | Auto-invalidates session, re-authenticates, retries |

---

## 14. Pipeline Trace

Every chat request generates a full pipeline trace showing Protegrity operations:

```json
{
  "trace": [
    {
      "step": "Gate 1 (Guardrail + Protect)",
      "duration_ms": 245,
      "risk_score": 0.15,
      "guardrail_threshold": 0.7,
      "accepted": true,
      "outcome": "accepted",
      "explanation": "Standard banking inquiry",
      "pii_elements": 2,
      "elements_found": ["PERSON", "SOCIAL_SECURITY_ID"],
      "original": "What is John Smith's SSN?",
      "protected": "What is [PERSON]xK9mQ[/PERSON]'s [SOCIAL_SECURITY_ID]aB3xQ[/SOCIAL_SECURITY_ID]?"
    },
    {
      "step": "Gate 2 (Unprotect as 'superuser')",
      "duration_ms": 120,
      "protegrity_user": "superuser",
      "raw_preview": "The SSN for [PERSON]xK9mQ[/PERSON] is ...",
      "final_preview": "The SSN for John Smith is ..."
    }
  ]
}
```

This trace is visible in the TechnicalApp UI, providing full transparency into how Protegrity handles each request.

---

## 15. Quick Reference — API/SDK Call Matrix

| Operation | Layer | Call | When |
|-----------|-------|------|------|
| Authenticate | REST | `POST /pty/dev-edition/v1/sessions` | App startup + auto-refresh |
| Risk scoring | REST | `POST /pty/semantic-guardrail/v1.1/.../scan` | Every user message (if guardrail enabled) |
| Classify & tokenize | SDK | `sdk.find_and_protect(text)` | Every user message (Gate 1) |
| Detokenize | SDK | `sdk.find_and_unprotect(text)` | Every LLM response (Gate 2) |
| Batch protect | SDK | `Protector().create_session(user).protect(val, de)` | Offline data preparation |
| Configure threshold | SDK | `sdk.configure(classification_score_threshold=n)` | When classify_threshold changes |
