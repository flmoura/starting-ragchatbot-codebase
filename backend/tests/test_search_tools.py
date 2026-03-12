import pytest
from unittest.mock import MagicMock
from vector_store import SearchResults
from search_tools import CourseSearchTool, ToolManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tool(store=None):
    if store is None:
        store = MagicMock()
        store.get_lesson_link.return_value = None
    return CourseSearchTool(store)


def make_results(docs, metas, distances=None):
    distances = distances or [0.1] * len(docs)
    return SearchResults(documents=docs, metadata=metas, distances=distances)


# ---------------------------------------------------------------------------
# CourseSearchTool.execute() — happy path
# ---------------------------------------------------------------------------

class TestExecuteHappyPath:
    def test_returns_formatted_string_with_course_and_lesson(self, mock_vector_store):
        results = make_results(
            ["neural network content"],
            [{"course_title": "Deep Learning", "lesson_number": 2}],
        )
        mock_vector_store.search.return_value = results
        mock_vector_store.get_lesson_link.return_value = None

        tool = make_tool(mock_vector_store)
        output = tool.execute(query="What is a neural network?")

        assert "[Deep Learning - Lesson 2]" in output
        assert "neural network content" in output

    def test_formats_multiple_results_separated_by_double_newline(self, mock_vector_store):
        results = make_results(
            ["content A", "content B"],
            [
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
        )
        mock_vector_store.search.return_value = results
        mock_vector_store.get_lesson_link.return_value = None

        tool = make_tool(mock_vector_store)
        output = tool.execute(query="something")

        parts = output.split("\n\n")
        assert len(parts) == 2
        assert "[Course A - Lesson 1]" in parts[0]
        assert "[Course B - Lesson 2]" in parts[1]

    def test_result_without_lesson_number_omits_lesson_from_header(self, mock_vector_store):
        results = make_results(
            ["general course content"],
            [{"course_title": "Intro Course", "lesson_number": None}],
        )
        mock_vector_store.search.return_value = results

        tool = make_tool(mock_vector_store)
        output = tool.execute(query="course overview")

        assert "[Intro Course]" in output
        assert "Lesson" not in output


# ---------------------------------------------------------------------------
# CourseSearchTool.execute() — empty results
# ---------------------------------------------------------------------------

class TestExecuteEmptyResults:
    def test_returns_no_content_found_without_filters(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = make_tool(mock_vector_store)
        output = tool.execute(query="something obscure")

        assert output == "No relevant content found."

    def test_empty_results_with_course_name_includes_course_in_message(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = make_tool(mock_vector_store)
        output = tool.execute(query="something", course_name="MCP Course")

        assert "No relevant content found" in output
        assert "MCP Course" in output

    def test_empty_results_with_lesson_number_includes_lesson_in_message(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = make_tool(mock_vector_store)
        output = tool.execute(query="something", lesson_number=3)

        assert "No relevant content found" in output
        assert "lesson 3" in output

    def test_empty_results_with_both_filters_includes_both_in_message(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = make_tool(mock_vector_store)
        output = tool.execute(query="q", course_name="RAG Bootcamp", lesson_number=5)

        assert "RAG Bootcamp" in output
        assert "lesson 5" in output


# ---------------------------------------------------------------------------
# CourseSearchTool.execute() — error handling
# ---------------------------------------------------------------------------

class TestExecuteError:
    def test_returns_error_string_from_search_results(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults.empty(
            "Search error: connection refused"
        )
        tool = make_tool(mock_vector_store)
        output = tool.execute(query="any query")

        assert output == "Search error: connection refused"


# ---------------------------------------------------------------------------
# CourseSearchTool.execute() — passes correct args to store.search()
# ---------------------------------------------------------------------------

class TestExecutePassesArgsToStore:
    def test_passes_query_and_no_filters_by_default(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = make_tool(mock_vector_store)
        tool.execute(query="my query")

        mock_vector_store.search.assert_called_once_with(
            query="my query", course_name=None, lesson_number=None
        )

    def test_passes_course_name_to_store_search(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = make_tool(mock_vector_store)
        tool.execute(query="lesson content", course_name="Deep Learning 101")

        mock_vector_store.search.assert_called_once_with(
            query="lesson content", course_name="Deep Learning 101", lesson_number=None
        )

    def test_passes_lesson_number_to_store_search(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = make_tool(mock_vector_store)
        tool.execute(query="backprop", lesson_number=4)

        mock_vector_store.search.assert_called_once_with(
            query="backprop", course_name=None, lesson_number=4
        )


# ---------------------------------------------------------------------------
# CourseSearchTool — source tracking
# ---------------------------------------------------------------------------

class TestSourceTracking:
    def test_last_sources_populated_after_execute(self, mock_vector_store):
        results = make_results(
            ["doc content"],
            [{"course_title": "AI Fundamentals", "lesson_number": 1}],
        )
        mock_vector_store.search.return_value = results
        mock_vector_store.get_lesson_link.return_value = None

        tool = make_tool(mock_vector_store)
        tool.execute(query="gradient descent")

        assert len(tool.last_sources) == 1
        assert "AI Fundamentals" in tool.last_sources[0]
        assert "Lesson 1" in tool.last_sources[0]

    def test_source_includes_lesson_link_when_available(self, mock_vector_store):
        results = make_results(
            ["content"],
            [{"course_title": "NLP Course", "lesson_number": 2}],
        )
        mock_vector_store.search.return_value = results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson/2"

        tool = make_tool(mock_vector_store)
        tool.execute(query="tokenization")

        source = tool.last_sources[0]
        assert "::" in source
        assert "https://example.com/lesson/2" in source

    def test_source_without_lesson_link_has_no_separator(self, mock_vector_store):
        results = make_results(
            ["content"],
            [{"course_title": "NLP Course", "lesson_number": 2}],
        )
        mock_vector_store.search.return_value = results
        mock_vector_store.get_lesson_link.return_value = None

        tool = make_tool(mock_vector_store)
        tool.execute(query="tokenization")

        source = tool.last_sources[0]
        assert "::" not in source
        assert source == "NLP Course - Lesson 2"

    def test_source_without_lesson_number_has_just_course_title(self, mock_vector_store):
        results = make_results(
            ["content"],
            [{"course_title": "General Course", "lesson_number": None}],
        )
        mock_vector_store.search.return_value = results

        tool = make_tool(mock_vector_store)
        tool.execute(query="overview")

        assert tool.last_sources[0] == "General Course"

    def test_last_sources_empty_before_execute(self, mock_vector_store):
        tool = make_tool(mock_vector_store)
        assert tool.last_sources == []


# ---------------------------------------------------------------------------
# ToolManager
# ---------------------------------------------------------------------------

class TestToolManager:
    def test_register_and_execute_tool(self, mock_vector_store):
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search.return_value = empty_results

        result = manager.execute_tool("search_course_content", query="test")
        assert "No relevant content found" in result

    def test_execute_unknown_tool_returns_error_string(self):
        manager = ToolManager()
        result = manager.execute_tool("nonexistent_tool", query="x")
        assert "not found" in result.lower()

    def test_get_last_sources_returns_from_course_search_tool(self, mock_vector_store):
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        tool.last_sources = ["Course A - Lesson 1::http://example.com"]
        manager.register_tool(tool)

        sources = manager.get_last_sources()
        assert sources == ["Course A - Lesson 1::http://example.com"]

    def test_reset_sources_clears_all_tool_sources(self, mock_vector_store):
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        tool.last_sources = ["some source"]
        manager.register_tool(tool)

        manager.reset_sources()
        assert tool.last_sources == []
        assert manager.get_last_sources() == []
