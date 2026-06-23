"""
Unit tests for the orchestration layer.

Runs WITHOUT live Protegrity services, LLM APIs, or ChromaDB.
All external dependencies are mocked.

Usage:
    cd /home/azure_usr/protegrity_ai_integrations/protegrity_demo/orchestration/BankingPortalChatbot
    pip install pytest networkx
    python -m pytest tests/test_orchestration.py -v
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Check optional deps
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


# ═══════════════════════════════════════════════════════════════════════
# 1. orchestration_config tests
# ═══════════════════════════════════════════════════════════════════════

class TestOrchestrationConfig:

    def test_default_orchestrator(self):
        import config.orchestration_config as cfg
        assert cfg.ORCHESTRATOR in ("langgraph", "crewai", "llamaindex")

    def test_default_llm_provider(self):
        import config.orchestration_config as cfg
        assert cfg.LLM_PROVIDER in ("openai", "anthropic", "groq")

    def test_get_model_name_default(self):
        import config.orchestration_config as cfg
        model = cfg.get_model_name()
        assert isinstance(model, str) and len(model) > 0

    def test_default_models_all_providers(self):
        import config.orchestration_config as cfg
        for provider in ("openai", "anthropic", "groq"):
            assert provider in cfg.DEFAULT_MODELS

    def test_gate_settings_types(self):
        import config.orchestration_config as cfg
        assert isinstance(cfg.SKIP_PROTEGRITY_GATES, bool)
        assert isinstance(cfg.SKIP_SEMANTIC_GUARDRAIL, bool)
        assert 0.0 <= cfg.PII_DISCOVERY_THRESHOLD <= 1.0
        assert 0.0 <= cfg.GUARDRAIL_RISK_THRESHOLD <= 1.0

    def test_rag_settings(self):
        import config.orchestration_config as cfg
        assert isinstance(cfg.USE_KNOWLEDGE_GRAPH, bool)
        assert isinstance(cfg.USE_CHROMADB, bool)
        assert cfg.RAG_TOP_K > 0


# ═══════════════════════════════════════════════════════════════════════
# 2. Base orchestrator tests
# ═══════════════════════════════════════════════════════════════════════

class TestBaseOrchestrator:

    def test_pipeline_result_dataclass(self):
        from orchestrators.base import PipelineResult
        result = PipelineResult(answer="Hello")
        assert result.answer == "Hello"
        assert result.blocked is False
        assert result.rag_context == []
        assert result.kg_context == {}

    def test_pipeline_result_blocked(self):
        from orchestrators.base import PipelineResult
        result = PipelineResult(answer="Blocked", blocked=True, block_reason="injection")
        assert result.blocked is True
        assert "injection" in result.block_reason

    def test_base_orchestrator_is_abstract(self):
        from orchestrators.base import BaseOrchestrator
        with pytest.raises(TypeError):
            BaseOrchestrator()


# ═══════════════════════════════════════════════════════════════════════
# 3. Knowledge Graph tests
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")
class TestKnowledgeGraph:

    def test_query_customer_empty_graph(self):
        import common.knowledge_graph as kg
        kg._GRAPH = nx.DiGraph()
        result = kg.query_customer("CUST-999999")
        assert result == {}
        kg._GRAPH = None

    def test_query_customer_found(self):
        import common.knowledge_graph as kg

        G = nx.DiGraph()
        G.add_node("CUST-100000", node_type="Customer", name="[PERSON]Xk9[/PERSON]")
        G.add_node("ACC-001", node_type="Account", balance=5000)
        G.add_edge("CUST-100000", "ACC-001", relation="HAS_ACCOUNT")
        kg._GRAPH = G

        result = kg.query_customer("CUST-100000")
        assert result["customer_id"] == "CUST-100000"
        assert "[PERSON]" in result["name"]
        assert "HAS_ACCOUNT" in result["relations"]
        assert len(result["relations"]["HAS_ACCOUNT"]) == 1
        kg._GRAPH = None

    def test_search_nodes_with_type(self):
        import common.knowledge_graph as kg

        G = nx.DiGraph()
        G.add_node("CUST-100000", node_type="Customer", name="[PERSON]Xk9[/PERSON]")
        G.add_node("CUST-100001", node_type="Customer", name="[PERSON]Ab3[/PERSON]")
        G.add_node("ACC-001", node_type="Account", balance=5000)
        kg._GRAPH = G

        results = kg.search_nodes("Xk9", node_type="Customer")
        assert len(results) == 1
        assert results[0]["id"] == "CUST-100000"
        kg._GRAPH = None

    def test_search_nodes_no_type_filter(self):
        import common.knowledge_graph as kg

        G = nx.DiGraph()
        G.add_node("CUST-100000", node_type="Customer", name="test")
        G.add_node("ACC-001", node_type="Account", balance=5000, note="test")
        kg._GRAPH = G

        results = kg.search_nodes("test")
        assert len(results) == 2
        kg._GRAPH = None


# ═══════════════════════════════════════════════════════════════════════
# 4. RAG retriever tests (mocked ChromaDB)
# ═══════════════════════════════════════════════════════════════════════

class TestRAGRetriever:

    def test_retrieve_with_mock(self):
        import common.rag_retriever as rag

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["Doc about CUST-100000", "Doc about CUST-100001"]],
            "metadatas": [[{"customer_id": "CUST-100000"}, {"customer_id": "CUST-100001"}]],
            "distances": [[0.1, 0.5]],
        }
        rag._COLLECTION = mock_collection

        results = rag.retrieve("billing question", top_k=2)
        assert len(results) == 2
        assert results[0]["text"] == "Doc about CUST-100000"
        assert results[0]["distance"] == 0.1
        rag._COLLECTION = None

    def test_retrieve_empty(self):
        import common.rag_retriever as rag

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        rag._COLLECTION = mock_collection

        results = rag.retrieve("nonexistent")
        assert results == []
        rag._COLLECTION = None


# ═══════════════════════════════════════════════════════════════════════
# 5. LLM provider factory tests (mocked)
# ═══════════════════════════════════════════════════════════════════════

class TestLLMProviderFactory:

    def test_openai_factory(self):
        import llm_providers.factory as fac

        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Hello!"))]
        )

        original = fac.openai
        try:
            fac.openai = mock_openai
            llm = fac._openai_llm("gpt-4o-mini")
            result = llm([{"role": "user", "content": "Hi"}])
            assert result == "Hello!"
        finally:
            fac.openai = original

    def test_anthropic_separates_system(self):
        import llm_providers.factory as fac

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Bonjour!")]
        )

        original = fac.anthropic
        try:
            fac.anthropic = mock_anthropic
            llm = fac._anthropic_llm("claude-test")
            result = llm([
                {"role": "system", "content": "Be helpful"},
                {"role": "user", "content": "Hi"},
            ])
            assert result == "Bonjour!"
            call_kwargs = mock_client.messages.create.call_args
            assert "Be helpful" in call_kwargs.kwargs["system"]
            assert call_kwargs.kwargs["messages"] == [{"role": "user", "content": "Hi"}]
        finally:
            fac.anthropic = original

    def test_groq_factory(self):
        import llm_providers.factory as fac

        mock_groq_cls = MagicMock()
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Fast!"))]
        )

        original = fac.Groq
        try:
            fac.Groq = mock_groq_cls
            llm = fac._groq_llm("llama-3.1-70b-versatile")
            result = llm([{"role": "user", "content": "Hi"}])
            assert result == "Fast!"
        finally:
            fac.Groq = original

    def test_openai_missing_raises(self):
        import llm_providers.factory as fac
        original = fac.openai
        try:
            fac.openai = None
            with pytest.raises(ImportError, match="pip install openai"):
                fac._openai_llm("gpt-4o-mini")
        finally:
            fac.openai = original

    def test_anthropic_missing_raises(self):
        import llm_providers.factory as fac
        original = fac.anthropic
        try:
            fac.anthropic = None
            with pytest.raises(ImportError, match="pip install anthropic"):
                fac._anthropic_llm("claude-test")
        finally:
            fac.anthropic = original

    def test_groq_missing_raises(self):
        import llm_providers.factory as fac
        original = fac.Groq
        try:
            fac.Groq = None
            with pytest.raises(ImportError, match="pip install groq"):
                fac._groq_llm("llama-test")
        finally:
            fac.Groq = original


# ═══════════════════════════════════════════════════════════════════════
# 6. Orchestrator factory test
# ═══════════════════════════════════════════════════════════════════════

class TestOrchestratorFactory:

    def test_factory_invalid(self):
        from orchestrators import factory as orch_factory
        original = orch_factory.ORCHESTRATOR
        try:
            orch_factory.ORCHESTRATOR = "invalid"
            with pytest.raises(ValueError, match="Unknown orchestrator"):
                orch_factory.get_orchestrator()
        finally:
            orch_factory.ORCHESTRATOR = original


# ═══════════════════════════════════════════════════════════════════════
# 7. Gate skip-mode tests (no Protegrity needed)
# ═══════════════════════════════════════════════════════════════════════

class TestGateSkipMode:

    def test_gate1_skip_passthrough(self):
        mock_guard_module = MagicMock()
        with patch.dict(sys.modules, {"services": MagicMock(), "services.protegrity_guard": mock_guard_module}):
            if "common.protegrity_gates" in sys.modules:
                del sys.modules["common.protegrity_gates"]
            from common.protegrity_gates import gate1_protect
            g1 = gate1_protect("Hello John Smith", skip_gates=True)
            assert g1.protected_text == "Hello John Smith"
            assert g1.blocked is False
            assert g1.risk_score == 0.0

    def test_gate2_skip_passthrough(self):
        mock_guard_module = MagicMock()
        with patch.dict(sys.modules, {"services": MagicMock(), "services.protegrity_guard": mock_guard_module}):
            if "common.protegrity_gates" in sys.modules:
                del sys.modules["common.protegrity_gates"]
            from common.protegrity_gates import gate2_unprotect
            g2 = gate2_unprotect("Hello [PERSON]Xk9[/PERSON]", skip_gates=True)
            assert g2.restored_text == "Hello [PERSON]Xk9[/PERSON]"


# ═══════════════════════════════════════════════════════════════════════
# 8. Structural import tests
# ═══════════════════════════════════════════════════════════════════════

class TestStructuralImports:

    def test_import_config(self):
        import config.orchestration_config as orchestration_config
        assert hasattr(orchestration_config, "ORCHESTRATOR")
        assert hasattr(orchestration_config, "LLM_PROVIDER")

    def test_import_base(self):
        from orchestrators.base import BaseOrchestrator, PipelineResult
        assert PipelineResult is not None

    def test_import_rag(self):
        from common.rag_retriever import retrieve, rebuild_index
        assert callable(retrieve)

    @pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")
    def test_import_kg(self):
        from common.knowledge_graph import get_graph, query_customer, search_nodes
        assert callable(query_customer)

    def test_import_llm_factory(self):
        from llm_providers.factory import get_llm, get_llm_for_langchain
        assert callable(get_llm)

    def test_import_orch_factory(self):
        from orchestrators.factory import get_orchestrator
        assert callable(get_orchestrator)
