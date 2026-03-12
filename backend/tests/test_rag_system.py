import pytest
from unittest.mock import MagicMock, patch
from rag_system import RAGSystem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.ANTHROPIC_API_KEY = "test-key"
    config.ANTHROPIC_MODEL = "claude-test"
    config.CHROMA_PATH = "/tmp/test-chroma"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    return config


@pytest.fixture
def rag(mock_config):
    """RAGSystem with all heavy dependencies patched."""
    with patch("rag_system.VectorStore") as MockVectorStore, \
         patch("rag_system.AIGenerator") as MockAIGenerator, \
         patch("rag_system.DocumentProcessor"), \
         patch("rag_system.SessionManager") as MockSessionManager:

        mock_ai = MagicMock()
        MockAIGenerator.return_value = mock_ai

        mock_session_manager = MagicMock()
        MockSessionManager.return_value = mock_session_manager

        system = RAGSystem(mock_config)
        system._mock_ai = mock_ai
        system._mock_session_manager = mock_session_manager

        # Patch tool_manager methods so tests control source behavior
        system.tool_manager.get_last_sources = MagicMock(return_value=[])
        system.tool_manager.reset_sources = MagicMock()

        yield system


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def configure_rag(rag, answer="some answer", sources=None, history=None):
    rag._mock_ai.generate_response.return_value = answer
    rag.tool_manager.get_last_sources.return_value = sources or []
    rag._mock_session_manager.get_conversation_history.return_value = history


def get_generate_kwargs(rag):
    return rag._mock_ai.generate_response.call_args[1]


# ---------------------------------------------------------------------------
# query() — prompt wrapping
# ---------------------------------------------------------------------------

class TestQueryPromptWrapping:
    def test_wraps_query_with_course_materials_prefix(self, rag):
        configure_rag(rag)
        rag.query("What is supervised learning?")

        kwargs = get_generate_kwargs(rag)
        assert kwargs["query"] == (
            "Answer this question about course materials: What is supervised learning?"
        )

    def test_prompt_preserves_exact_user_query(self, rag):
        configure_rag(rag)
        user_query = "How does attention mechanism work in lesson 4?"
        rag.query(user_query)

        kwargs = get_generate_kwargs(rag)
        assert user_query in kwargs["query"]


# ---------------------------------------------------------------------------
# query() — tool forwarding
# ---------------------------------------------------------------------------

class TestQueryToolForwarding:
    def test_passes_tool_definitions_to_generate_response(self, rag):
        configure_rag(rag)
        rag.query("some question")

        kwargs = get_generate_kwargs(rag)
        # tools must be the list returned by tool_manager.get_tool_definitions()
        assert kwargs["tools"] == rag.tool_manager.get_tool_definitions()

    def test_passes_tool_manager_instance_to_generate_response(self, rag):
        configure_rag(rag)
        rag.query("some question")

        kwargs = get_generate_kwargs(rag)
        assert kwargs["tool_manager"] is rag.tool_manager


# ---------------------------------------------------------------------------
# query() — sources lifecycle
# ---------------------------------------------------------------------------

class TestQuerySources:
    def test_returns_sources_from_get_last_sources(self, rag):
        configure_rag(rag, sources=["Deep Learning - Lesson 1::http://example.com"])

        _, sources = rag.query("deep learning question")

        assert sources == ["Deep Learning - Lesson 1::http://example.com"]

    def test_reset_sources_called_after_get_last_sources(self, rag):
        configure_rag(rag)
        call_order = []
        rag.tool_manager.get_last_sources.side_effect = lambda: call_order.append("get") or []
        rag.tool_manager.reset_sources.side_effect = lambda: call_order.append("reset")

        rag.query("question")

        assert call_order == ["get", "reset"], (
            "reset_sources() must be called AFTER get_last_sources()"
        )

    def test_returns_empty_sources_when_no_tool_called(self, rag):
        configure_rag(rag, sources=[])

        _, sources = rag.query("what is the weather?")

        assert sources == []


# ---------------------------------------------------------------------------
# query() — session / history handling
# ---------------------------------------------------------------------------

class TestQuerySessionHandling:
    def test_without_session_id_passes_no_history(self, rag):
        configure_rag(rag)

        rag.query("question without session")

        kwargs = get_generate_kwargs(rag)
        assert kwargs.get("conversation_history") is None

    def test_with_session_id_passes_history_from_session_manager(self, rag):
        history_text = "User: prior question\nAssistant: prior answer"
        configure_rag(rag, history=history_text)

        rag.query("follow-up", session_id="session_1")

        kwargs = get_generate_kwargs(rag)
        assert kwargs["conversation_history"] == history_text

    def test_with_session_id_updates_session_after_response(self, rag):
        configure_rag(rag, answer="AI response")
        rag._mock_session_manager.get_conversation_history.return_value = None

        rag.query("user question", session_id="session_42")

        rag._mock_session_manager.add_exchange.assert_called_once_with(
            "session_42", "user question", "AI response"
        )

    def test_without_session_id_does_not_update_session(self, rag):
        configure_rag(rag)

        rag.query("question without session")

        rag._mock_session_manager.add_exchange.assert_not_called()


# ---------------------------------------------------------------------------
# query() — return value shape
# ---------------------------------------------------------------------------

class TestQueryReturnValue:
    def test_returns_tuple_of_response_and_sources(self, rag):
        configure_rag(rag, answer="the answer", sources=["src1"])

        result = rag.query("question")

        assert isinstance(result, tuple)
        assert len(result) == 2
        response, sources = result
        assert response == "the answer"
        assert sources == ["src1"]
