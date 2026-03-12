"""Shared fixtures for the RAG chatbot test suite."""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure backend/ is on the path so imports work when running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Lightweight mock factories
# ---------------------------------------------------------------------------

def make_mock_rag_system(
    query_return=("Test answer", ["Source A"]),
    analytics_return=None,
):
    """Return a MagicMock that behaves like RAGSystem."""
    if analytics_return is None:
        analytics_return = {"total_courses": 2, "course_titles": ["Course A", "Course B"]}

    mock = MagicMock()
    mock.query.return_value = query_return
    mock.get_course_analytics.return_value = analytics_return
    mock.session_manager.create_session.return_value = "session_1"
    mock.session_manager.clear_session.return_value = None
    return mock


# ---------------------------------------------------------------------------
# App-level fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_rag():
    """A pre-configured mock RAGSystem instance."""
    return make_mock_rag_system()


@pytest.fixture()
def test_client(mock_rag):
    """
    TestClient built from a minimal FastAPI app that mirrors the real endpoints
    but avoids the static-file mount (which requires an on-disk frontend/).
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id or mock_rag.session_manager.create_session()
            answer, sources = mock_rag.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.delete("/api/session/{session_id}")
    async def delete_session(session_id: str):
        mock_rag.session_manager.clear_session(session_id)
        return {"status": "ok"}

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return TestClient(test_app)


# ---------------------------------------------------------------------------
# Data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_query_payload():
    return {"query": "What is machine learning?"}


@pytest.fixture()
def sample_query_payload_with_session():
    return {"query": "What is machine learning?", "session_id": "session_42"}
