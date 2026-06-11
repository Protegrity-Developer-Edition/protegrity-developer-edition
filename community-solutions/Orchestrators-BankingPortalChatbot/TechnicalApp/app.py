"""TechnicalApp – Admin/Technical portal for orchestration, LLM, and Protegrity configuration."""
from __future__ import annotations
import os, json, logging, time, hashlib
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from services.banking_service import get_banking_service
from services.protegrity_guard import get_guard, register_tokens_from_context, _strip_pii_tags
from services.conversation_history import ConversationHistory

app = Flask(__name__, template_folder=str(Path(__file__).resolve().parent / "templates"))
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "technical-portal-demo-secret-key-2026")

_config = {
    "orchestrator": os.environ.get("ORCHESTRATOR", "direct"),
    "llm_provider": os.environ.get("LLM_PROVIDER", "openai"),
    "llm_model": os.environ.get("LLM_MODEL", ""),
    "risk_threshold": float(os.environ.get("RISK_THRESHOLD", "0.7")),
    "guardrail_enabled": os.environ.get("GUARDRAIL_ENABLED", "true").lower() not in ("false", "0", "no", "off"),
    "protegrity_user": os.environ.get("PROTEGRITY_USER", "superuser"),
    "discovery_enabled": os.environ.get("DISCOVERY_ENABLED", "true").lower() not in ("false", "0", "no", "off"),
    "classify_threshold": float(os.environ.get("CLASSIFY_THRESHOLD", "0.5")),
    "show_trace": True,
    "kb_enabled": True,
    "rag_enabled": False,
    "kg_enabled": False,
}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "groq": "llama-3.1-70b-versatile",
}

service = get_banking_service()
guard = get_guard()
chat_histories: dict[str, ConversationHistory] = {}

CHAT_HISTORY_DIR = Path(__file__).resolve().parent / "chat_history_tech"
CHAT_HISTORY_DIR.mkdir(exist_ok=True)
KB_DIR = Path(__file__).resolve().parent.parent / "banking_data" / "knowledge_base"

SYSTEM_PROMPT = (
    "You are a helpful banking assistant for SecureBank. "
    "You help customers check their account balances, review transactions, "
    "manage credit cards, and answer questions about their banking products. "
    "Be concise, professional, and accurate. "
    "IMPORTANT: The customer data contains tokenized values wrapped in tags like "
    "[PERSON]value[/PERSON], [EMAIL_ADDRESS]value[/EMAIL_ADDRESS], "
    "[PHONE_NUMBER]value[/PHONE_NUMBER], [SOCIAL_SECURITY_ID]value[/SOCIAL_SECURITY_ID], "
    "[CREDIT_CARD]value[/CREDIT_CARD], [LOCATION]value[/LOCATION], "
    "[DATETIME]value[/DATETIME], [BANK_ACCOUNT]value[/BANK_ACCOUNT], "
    "[ACCOUNT_NUMBER]value[/ACCOUNT_NUMBER], "
    "[HEALTH_CARE_ID]value[/HEALTH_CARE_ID]. "
    "When displaying customer data in your response, you MUST preserve these tags exactly "
    "as they appear. Do NOT strip, remove, or alter the square bracket tags. "
    "Do NOT redact, mask, or refuse to show any information. "
    "Example: if the data says Name: [PERSON]xYz123[/PERSON], your response must include "
    "[PERSON]xYz123[/PERSON], not just xYz123."
)

USERS_FILE = Path(__file__).resolve().parent.parent / "config" / "users.json"
with open(USERS_FILE) as _uf:
    TECH_USERS = json.load(_uf)

ORCHESTRATOR_INFO = {
    "direct": {
        "title": "Direct LLM — Baseline Pipeline",
        "points": [
            "Fastest path — single LLM call, minimal latency, no orchestration overhead.",
            "Protegrity Gate 1 tokenizes all PII before the prompt ever reaches the LLM.",
            "Gate 2 applies per-user detokenization policies — only authorized roles see real data.",
            "Proves Protegrity's dual-gate works transparently with any LLM provider.",
            "Data sources: KB files only — pre-tokenized customer profiles.",
        ],
        "data_sources": {"kb": True, "rag": False, "kg": False},
    },
    "langgraph": {
        "title": "LangGraph — Composable DAG Pipeline",
        "points": [
            "StateGraph with modular nodes — retrieval steps are composable, reorderable graph nodes.",
            "Combines all three data sources (KB + RAG + KG) into a single pipeline.",
            "Protegrity tokens flow through every node — the graph never materializes raw PII.",
            "Shows how DAG orchestration scales with Protegrity: add nodes without weakening protection.",
            "Best for complex multi-source workflows where each step handles pre-protected data.",
        ],
        "data_sources": {"kb": True, "rag": True, "kg": True},
    },
    "crewai": {
        "title": "CrewAI — Multi-Agent Reasoning",
        "points": [
            "Specialized agents (Research + Response) collaborate over tokenized data only.",
            "Research Agent navigates the Knowledge Graph for cross-entity financial relationships.",
            "Agents never see real PII — Protegrity tokens are opaque across the entire agent crew.",
            "Demonstrates separation-of-duties: agents operate on protected data, Gate 2 reveals on exit.",
            "Best for relationship-heavy queries: account links, transaction patterns, loan cross-refs.",
        ],
        "data_sources": {"kb": True, "rag": False, "kg": True},
    },
    "llamaindex": {
        "title": "LlamaIndex — Native Semantic Retrieval",
        "points": [
            "Purpose-built for RAG — ChromaDB vector search over pre-tokenized documents.",
            "Semantic similarity finds relevant customer data even across tokenized fields.",
            "Protegrity tokens in the vector index guarantee zero PII exposure at the embedding layer.",
            "Native LLM adapters (OpenAI, Anthropic, Groq) with clean Protegrity integration.",
            "Best when semantic search quality matters — retrieval over protected document collections.",
        ],
        "data_sources": {"kb": True, "rag": True, "kg": False},
    },
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("TechnicalApp")


def _get_model() -> str:
    if _config["llm_model"]:
        return _config["llm_model"]
    return DEFAULT_MODELS.get(_config["llm_provider"], "gpt-4o-mini")


def _history_filepath(session_key: str) -> Path:
    return CHAT_HISTORY_DIR / f"{session_key}.json"


def _get_or_create_history(session_key: str) -> ConversationHistory:
    if session_key not in chat_histories:
        filepath = _history_filepath(session_key)
        loaded = ConversationHistory.load_from_file(filepath)
        if loaded:
            loaded.system_prompt = SYSTEM_PROMPT
            if not loaded.messages or loaded.messages[0]["role"] != "system":
                loaded.messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
            chat_histories[session_key] = loaded
        else:
            chat_histories[session_key] = ConversationHistory(system_prompt=SYSTEM_PROMPT, max_turns=20)
    return chat_histories[session_key]


def _save_history(session_key: str):
    if session_key in chat_histories:
        chat_histories[session_key].save_to_file(_history_filepath(session_key))


def _user_unprotect(text: str, protegrity_user: str) -> str:
    if protegrity_user == "superuser":
        gate2_result = guard.gate2_output(text, restore=True)
        return gate2_result.transformed_text
    try:
        import sys
        cs_app_dir = str(Path(__file__).resolve().parent.parent / "InternalCustomerServiceApp")
        if cs_app_dir not in sys.path:
            sys.path.insert(0, cs_app_dir)
        from protegrity_user_gate import user_unprotect
        return user_unprotect(text, protegrity_user)
    except Exception as e:
        log.warning("Per-user unprotect failed for '%s': %s. Falling back.", protegrity_user, e)
        gate2_result = guard.gate2_output(text, restore=True)
        return gate2_result.transformed_text



def _call_orchestrated(user_message: str, customer_id: str, protected_context: str,
                       conversation_history: list | None = None) -> dict:
    orchestrator_type = _config["orchestrator"]
    provider = _config["llm_provider"]
    model = _get_model()
    try:
        os.environ["ORCHESTRATOR"] = orchestrator_type
        os.environ["LLM_PROVIDER"] = provider
        if model:
            os.environ["LLM_MODEL"] = model
        from orchestrators import ask
        result = ask(user_message, customer_id=customer_id, protected_context=protected_context,
                     conversation_history=conversation_history)
        return {"answer": result.answer, "trace": getattr(result, "trace", []), "orchestrator": orchestrator_type}
    except ImportError:
        return {"answer": f"Orchestrator '{orchestrator_type}' not available.", "trace": [], "orchestrator": orchestrator_type}
    except Exception as e:
        return {"answer": f"Orchestration error: {e}", "trace": [], "orchestrator": orchestrator_type}


def get_llm_response(user_message: str, customer_id: str) -> dict:
    trace = []
    t0 = time.time()

    # Gate 1
    t_gate1 = time.time()
    if _config["guardrail_enabled"]:
        gate1_result = guard.gate1_input(user_message, risk_threshold=_config["risk_threshold"],
                                         classify_threshold=_config["classify_threshold"])
        trace.append({
            "step": "Gate 1 (Guardrail + Protect)", "duration_ms": round((time.time() - t_gate1) * 1000),
            "risk_score": gate1_result.risk_score, "guardrail_threshold": _config["risk_threshold"],
            "accepted": gate1_result.risk_accepted,
            "outcome": gate1_result.metadata.get("outcome", "accepted"),
            "explanation": gate1_result.metadata.get("explanation", ""),
            "pii_elements": len(gate1_result.elements_found),
            "elements_found": [e.get("entity_type", "unknown") for e in gate1_result.elements_found],
            "original": user_message[:200], "protected": gate1_result.transformed_text[:200],
        })
    elif _config["discovery_enabled"]:
        gate1_result = guard.find_and_protect(user_message, classify_threshold=_config["classify_threshold"])
        gate1_result.risk_score = 0.0
        gate1_result.risk_accepted = True
        trace.append({
            "step": "Gate 1 (Discovery Only)", "duration_ms": round((time.time() - t_gate1) * 1000),
            "risk_score": 0.0, "accepted": True,
            "pii_elements": len(gate1_result.elements_found),
            "elements_found": [e.get("entity_type", "unknown") for e in gate1_result.elements_found],
            "original": user_message[:200], "protected": gate1_result.transformed_text[:200],
        })
    else:
        class _PassThrough:
            risk_score = 0.0; risk_accepted = True; transformed_text = user_message
            original_text = user_message; elements_found = []; metadata = {}
        gate1_result = _PassThrough()
        trace.append({"step": "Gate 1 (Bypassed)", "duration_ms": 0, "risk_score": 0.0, "accepted": True, "pii_elements": 0})

    if not gate1_result.risk_accepted:
        blocked_msg = (
            f"⚠️ Message blocked by security guardrail. "
            f"Risk score: {gate1_result.risk_score} (guardrail threshold: {_config['risk_threshold']}). "
            f"Please rephrase your question."
        )
        return {"response": blocked_msg, "trace": trace, "config": _get_safe_config(), "total_ms": round((time.time() - t0) * 1000)}

    protected_message = gate1_result.transformed_text

    # KB file
    t_kb = time.time()
    protected_context = ""
    if _config["kb_enabled"]:
        kb_file = KB_DIR / f"{customer_id}.txt"
        if kb_file.exists():
            protected_context = kb_file.read_text().strip()
            trace.append({"step": "KB File Retrieval", "duration_ms": round((time.time() - t_kb) * 1000), "file": kb_file.name, "chars": len(protected_context)})
        else:
            trace.append({"step": "KB File Retrieval", "duration_ms": round((time.time() - t_kb) * 1000), "error": f"Not found: {customer_id}.txt"})
    else:
        trace.append({"step": "KB File (Disabled)", "duration_ms": 0})

    # RAG
    rag_context = ""
    if _config["rag_enabled"]:
        t_rag = time.time()
        try:
            from common.rag_retriever import retrieve
            rag_results = retrieve(protected_message, top_k=3, customer_id=customer_id)
            rag_chunks = [f"[RAG hit: {r['metadata'].get('customer_id','?')}, dist={r.get('distance',0):.3f}]\n{r['text'][:500]}" for r in rag_results]
            rag_context = "\n\n".join(rag_chunks)
            trace.append({"step": "RAG (ChromaDB)", "duration_ms": round((time.time() - t_rag) * 1000), "results": len(rag_results), "context_chars": len(rag_context)})
        except Exception as e:
            log.warning("RAG failed: %s", e)
            trace.append({"step": "RAG (ChromaDB)", "duration_ms": round((time.time() - t_rag) * 1000), "error": str(e)})
    else:
        trace.append({"step": "RAG (Disabled)", "duration_ms": 0})

    # Knowledge Graph
    kg_context = ""
    if _config["kg_enabled"]:
        t_kg = time.time()
        try:
            from common.knowledge_graph import query_customer, get_graph
            G = get_graph()
            kg_data = query_customer(customer_id)
            if kg_data:
                kg_parts = [f"Knowledge Graph for {customer_id}:"]
                kg_parts.append(f"  Name: {kg_data.get('name', 'N/A')}")
                kg_parts.append(f"  Email: {kg_data.get('email', 'N/A')}")
                kg_parts.append(f"  Phone: {kg_data.get('phone', 'N/A')}")
                for relation, items in kg_data.get("relations", {}).items():
                    kg_parts.append(f"  {relation}: {len(items)} items")
                    for item in items[:5]:
                        ntype = item.get("node_type", "")
                        iid = item.get("id", "")
                        if ntype == "Account":
                            kg_parts.append(f"    {iid} | {item.get('acct_type','')} | bal=${item.get('balance','')}")
                        elif ntype == "CreditCard":
                            kg_parts.append(f"    {iid} | {item.get('card_type','')} {item.get('card_tier','')} | bal=${item.get('current_balance','')}")
                        elif ntype == "Loan":
                            kg_parts.append(f"    {iid} | {item.get('loan_type','')} | remaining=${item.get('remaining_balance','')}")
                        elif ntype == "Transaction":
                            kg_parts.append(f"    {iid} | {item.get('category','')} | ${item.get('amount','')} | {item.get('merchant','')}")
                kg_context = "\n".join(kg_parts)
                trace.append({"step": "Knowledge Graph", "duration_ms": round((time.time() - t_kg) * 1000), "graph_nodes": G.number_of_nodes(), "graph_edges": G.number_of_edges(), "context_chars": len(kg_context)})
            else:
                trace.append({"step": "Knowledge Graph", "duration_ms": round((time.time() - t_kg) * 1000), "error": f"{customer_id} not in graph"})
        except Exception as e:
            log.warning("KG failed: %s", e)
            trace.append({"step": "Knowledge Graph", "duration_ms": round((time.time() - t_kg) * 1000), "error": str(e)})
    else:
        trace.append({"step": "Knowledge Graph (Disabled)", "duration_ms": 0})

    # Combine context
    context_parts = []
    if protected_context:
        context_parts.append(protected_context)
    if rag_context:
        context_parts.append(f"\n--- RAG Search Results ---\n{rag_context}")
    if kg_context:
        context_parts.append(f"\n--- Knowledge Graph ---\n{kg_context}")
    if not context_parts:
        context_parts.append(f"No customer data available for {customer_id}.")
    combined_context = "\n\n".join(context_parts)
    register_tokens_from_context(combined_context)

    # LLM Call — all orchestrators go through the same path
    t_orch = time.time()
    history = _get_or_create_history(f"{session.get('username', 'anon')}_{customer_id}")
    history.add_user_message(protected_message)
    orch_result = _call_orchestrated(
        protected_message, customer_id, combined_context,
        conversation_history=history.get_messages()[:-1],  # exclude the just-added user msg
    )
    raw_response = orch_result["answer"]
    trace.append({
        "step": f"Orchestrator ({_config['orchestrator']})", "duration_ms": round((time.time() - t_orch) * 1000),
        "orchestrator": _config["orchestrator"], "provider": _config["llm_provider"], "model": _get_model(),
        "context_sources": [s for s in ["KB" if protected_context else None, "RAG" if rag_context else None, "KG" if kg_context else None] if s],
        "sub_trace": orch_result.get("trace", []), "response_preview": raw_response[:300],
    })
    history.add_assistant_message(raw_response)
    _save_history(f"{session.get('username', 'anon')}_{customer_id}")

    # Gate 2
    t_gate2 = time.time()
    protegrity_user = _config["protegrity_user"]
    final_response = _user_unprotect(raw_response, protegrity_user)
    trace.append({
        "step": f"Gate 2 (Unprotect as '{protegrity_user}')", "duration_ms": round((time.time() - t_gate2) * 1000),
        "protegrity_user": protegrity_user, "raw_preview": raw_response[:200], "final_preview": final_response[:200],
    })

    return {"response": final_response, "trace": trace, "config": _get_safe_config(), "total_ms": round((time.time() - t0) * 1000)}


def _get_safe_config() -> dict:
    return {
        "orchestrator": _config["orchestrator"], "llm_provider": _config["llm_provider"],
        "llm_model": _get_model(), "risk_threshold": _config["risk_threshold"],
        "guardrail_enabled": _config["guardrail_enabled"], "discovery_enabled": _config["discovery_enabled"],
        "classify_threshold": _config["classify_threshold"],
        "protegrity_user": _config["protegrity_user"], "show_trace": _config["show_trace"],
        "kb_enabled": _config["kb_enabled"], "rag_enabled": _config["rag_enabled"], "kg_enabled": _config["kg_enabled"],
    }


# ─── Routes ───────────────────────────────────────────────────────────

@app.route("/tech/")
def index():
    return redirect(url_for("dashboard")) if "username" in session else redirect(url_for("login"))


@app.route("/tech/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = TECH_USERS.get(username)
        if user and user["password_hash"] == hashlib.sha256(password.encode()).hexdigest():
            session["username"] = username
            session["role"] = user["role"]
            session["protegrity_user"] = user["protegrity_user"]
            session["locked_orchestrator"] = user.get("orchestrator")
            if user.get("orchestrator"):
                _config["orchestrator"] = user["orchestrator"]
            return redirect(url_for("dashboard"))
        error = "Invalid credentials."
    return render_template("login.html", error=error)


@app.route("/tech/logout")
def logout():
    username = session.get("username")
    if username:
        for k in [k for k in chat_histories if k.startswith(f"{username}_")]:
            chat_histories.pop(k, None)
    session.clear()
    return redirect(url_for("login"))


@app.route("/tech/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    customers = service.get_all_customers()
    customer_ids = [c.get("customer_id", c.get("account_id", "unknown")) for c in customers]
    locked_orch = session.get("locked_orchestrator")
    available_orchestrators = [locked_orch] if locked_orch else ["direct", "langgraph", "crewai", "llamaindex"]
    orch_info = ORCHESTRATOR_INFO.get(_config["orchestrator"], ORCHESTRATOR_INFO["direct"])
    return render_template("dashboard.html", username=session["username"], role=session["role"],
        config=_get_safe_config(), customer_ids=sorted(customer_ids), orchestrators=available_orchestrators,
        llm_providers=["openai", "anthropic", "groq"], protegrity_users=["superuser", "Marketing", "Finance", "Support"],
        locked_orchestrator=locked_orch, orch_info=orch_info)


@app.route("/tech/chat/<customer_id>")
def chat(customer_id):
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html", username=session["username"], customer_id=customer_id, config=_get_safe_config())


@app.route("/tech/api/config", methods=["GET"])
def api_get_config():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify(_get_safe_config())


@app.route("/tech/api/config", methods=["POST"])
def api_update_config():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json()
    updated = []
    locked_orch = session.get("locked_orchestrator")

    if "orchestrator" in data and data["orchestrator"] in ("direct", "langgraph", "crewai", "llamaindex"):
        if locked_orch is None or data["orchestrator"] == locked_orch:
            _config["orchestrator"] = data["orchestrator"]
            updated.append("orchestrator")
    if "llm_provider" in data and data["llm_provider"] in ("openai", "anthropic", "groq"):
        new_provider = data["llm_provider"]
        if new_provider != _config["llm_provider"]:
            # Clear model when provider changes so auto-default kicks in
            _config["llm_model"] = ""
        _config["llm_provider"] = new_provider; updated.append("llm_provider")
    if "llm_model" in data:
        _config["llm_model"] = data["llm_model"].strip(); updated.append("llm_model")
    if "risk_threshold" in data:
        try:
            val = float(data["risk_threshold"])
            if 0.0 <= val <= 1.0:
                _config["risk_threshold"] = val; updated.append("risk_threshold")
        except (ValueError, TypeError):
            pass
    if "classify_threshold" in data:
        try:
            val = float(data["classify_threshold"])
            if 0.0 <= val <= 1.0:
                _config["classify_threshold"] = val; updated.append("classify_threshold")
        except (ValueError, TypeError):
            pass
    for key in ("guardrail_enabled", "discovery_enabled", "show_trace", "kb_enabled", "rag_enabled", "kg_enabled"):
        if key in data:
            _config[key] = bool(data[key]); updated.append(key)

    # Enforce data source constraints per orchestrator
    orch = _config["orchestrator"]
    orch_ds = ORCHESTRATOR_INFO.get(orch, {}).get("data_sources")
    if orch_ds:
        if not orch_ds.get("rag"):
            _config["rag_enabled"] = False
        if not orch_ds.get("kg"):
            _config["kg_enabled"] = False
        if not orch_ds.get("kb"):
            _config["kb_enabled"] = False
    if "protegrity_user" in data:
        _config["protegrity_user"] = data["protegrity_user"].strip(); updated.append("protegrity_user")

    log.info("Config updated by %s: %s", session.get("username"), updated)
    return jsonify({"status": "ok", "updated": updated, "config": _get_safe_config()})


@app.route("/tech/api/chat", methods=["POST"])
def api_chat():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json()
    user_message = data.get("message", "").strip()
    customer_id = data.get("customer_id", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    if not customer_id:
        return jsonify({"error": "No customer_id specified"}), 400
    return jsonify(get_llm_response(user_message, customer_id))


@app.route("/tech/api/chat/clear", methods=["POST"])
def api_chat_clear():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json() or {}
    customer_id = data.get("customer_id", "")
    session_key = f"{session['username']}_{customer_id}"
    chat_histories.pop(session_key, None)
    filepath = _history_filepath(session_key)
    if filepath.exists():
        filepath.unlink()
    return jsonify({"status": "ok", "message": "Chat history cleared."})


if __name__ == "__main__":
    port = int(os.environ.get("TECH_PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)
