"""
Orchestration & LLM configuration.

Set ORCHESTRATOR and LLM_PROVIDER via environment variables or change defaults here.

Supported orchestrators: langgraph, crewai, llamaindex
Supported LLM providers: openai, anthropic, groq
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Orchestrator selection ───────────────────────────────────────────
ORCHESTRATOR = os.getenv("ORCHESTRATOR", "langgraph").lower()
assert ORCHESTRATOR in ("langgraph", "crewai", "llamaindex"), \
    f"Unknown orchestrator: {ORCHESTRATOR}"

# ── LLM provider selection ──────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
assert LLM_PROVIDER in ("openai", "anthropic", "groq"), \
    f"Unknown LLM provider: {LLM_PROVIDER}"

# ── LLM model defaults per provider ─────────────────────────────────
LLM_MODEL = os.getenv("LLM_MODEL", None)

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "groq": "llama-3.1-70b-versatile",
}

def get_model_name() -> str:
    return LLM_MODEL or DEFAULT_MODELS[LLM_PROVIDER]

# ── API keys (each provider reads its own) ───────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ── RAG / Knowledge Graph settings ──────────────────────────────────
USE_KNOWLEDGE_GRAPH = os.getenv("USE_KNOWLEDGE_GRAPH", "true").lower() == "true"
USE_CHROMADB = os.getenv("USE_CHROMADB", "true").lower() == "true"
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

# ── Protegrity gate settings ────────────────────────────────────────
SKIP_PROTEGRITY_GATES = os.getenv("SKIP_PROTEGRITY_GATES", "false").lower() == "true"
SKIP_SEMANTIC_GUARDRAIL = os.getenv("SKIP_SEMANTIC_GUARDRAIL", "true").lower() == "true"
PII_DISCOVERY_THRESHOLD = float(os.getenv("PII_DISCOVERY_THRESHOLD", "0.4"))
GUARDRAIL_RISK_THRESHOLD = float(os.getenv("GUARDRAIL_RISK_THRESHOLD", "0.7"))


# ── Aliases for backward compatibility ──────────────────────────────
get_model = get_model_name
RISK_THRESHOLD = GUARDRAIL_RISK_THRESHOLD
PROTEGRITY_USER = os.getenv("PROTEGRITY_USER", "default_user")
KB_ENABLED = USE_KNOWLEDGE_GRAPH