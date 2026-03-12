"""API endpoint tests for the RAG chatbot FastAPI application."""
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    def test_returns_200_with_valid_payload(self, test_client, sample_query_payload):
        response = test_client.post("/api/query", json=sample_query_payload)
        assert response.status_code == 200

    def test_response_contains_required_fields(self, test_client, sample_query_payload):
        response = test_client.post("/api/query", json=sample_query_payload)
        body = response.json()
        assert "answer" in body
        assert "sources" in body
        assert "session_id" in body

    def test_answer_and_sources_match_mock(self, test_client, sample_query_payload):
        response = test_client.post("/api/query", json=sample_query_payload)
        body = response.json()
        assert body["answer"] == "Test answer"
        assert body["sources"] == ["Source A"]

    def test_auto_creates_session_when_none_provided(self, test_client, sample_query_payload, mock_rag):
        response = test_client.post("/api/query", json=sample_query_payload)
        body = response.json()
        # Session should come from session_manager.create_session()
        assert body["session_id"] == "session_1"
        mock_rag.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, test_client, sample_query_payload_with_session, mock_rag):
        response = test_client.post("/api/query", json=sample_query_payload_with_session)
        body = response.json()
        assert body["session_id"] == "session_42"
        # create_session should NOT be called when session_id is given
        mock_rag.session_manager.create_session.assert_not_called()

    def test_calls_rag_query_with_correct_args(self, test_client, mock_rag):
        test_client.post("/api/query", json={"query": "Tell me about Python", "session_id": "s1"})
        mock_rag.query.assert_called_once_with("Tell me about Python", "s1")

    def test_returns_422_when_query_missing(self, test_client):
        response = test_client.post("/api/query", json={})
        assert response.status_code == 422

    def test_returns_500_when_rag_raises(self, test_client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("database error")
        response = test_client.post("/api/query", json={"query": "crash", "session_id": "s1"})
        assert response.status_code == 500
        assert "database error" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    def test_returns_200(self, test_client):
        response = test_client.get("/api/courses")
        assert response.status_code == 200

    def test_response_shape(self, test_client):
        body = test_client.get("/api/courses").json()
        assert "total_courses" in body
        assert "course_titles" in body
        assert isinstance(body["course_titles"], list)

    def test_returns_mock_analytics(self, test_client):
        body = test_client.get("/api/courses").json()
        assert body["total_courses"] == 2
        assert body["course_titles"] == ["Course A", "Course B"]

    def test_returns_500_when_analytics_raises(self, test_client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("chroma down")
        response = test_client.get("/api/courses")
        assert response.status_code == 500
        assert "chroma down" in response.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE /api/session/{session_id}
# ---------------------------------------------------------------------------

class TestDeleteSessionEndpoint:
    def test_returns_200_and_ok_status(self, test_client):
        response = test_client.delete("/api/session/session_42")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_calls_clear_session_with_correct_id(self, test_client, mock_rag):
        test_client.delete("/api/session/session_99")
        mock_rag.session_manager.clear_session.assert_called_once_with("session_99")
