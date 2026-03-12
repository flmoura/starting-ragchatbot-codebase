import sys
import os

# Add backend/ to sys.path so all backend relative imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock
from vector_store import SearchResults


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.get_lesson_link.return_value = None
    return store


@pytest.fixture
def mock_search_results_with_data():
    return SearchResults(
        documents=["content about neural networks", "content about transformers"],
        metadata=[
            {"course_title": "Deep Learning", "lesson_number": 3},
            {"course_title": "Deep Learning", "lesson_number": None},
        ],
        distances=[0.1, 0.2],
    )


@pytest.fixture
def mock_search_results_empty():
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def mock_search_results_error():
    return SearchResults.empty("Search error: connection refused")
