import pytest
from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator


# ---------------------------------------------------------------------------
# Mock builders
# ---------------------------------------------------------------------------

def make_text_response(text="Hello, world!"):
    """Mock Anthropic response with a direct text block."""
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text

    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [content_block]
    return response


def make_tool_use_response(tool_name="search_course_content", tool_id="tool_123", tool_input=None):
    """Mock Anthropic response requesting a tool call."""
    if tool_input is None:
        tool_input = {"query": "what is backprop?"}

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.id = tool_id
    tool_block.input = tool_input

    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [tool_block]
    return response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    with patch("ai_generator.anthropic.Anthropic") as MockAnthropic:
        client_instance = MagicMock()
        MockAnthropic.return_value = client_instance
        yield client_instance


@pytest.fixture
def generator(mock_client):
    return AIGenerator(api_key="test-key", model="claude-test-model")


# ---------------------------------------------------------------------------
# generate_response() — direct text path
# ---------------------------------------------------------------------------

class TestGenerateResponseDirectText:
    def test_returns_text_when_stop_reason_is_end_turn(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response("Direct answer.")

        result = generator.generate_response(query="What is gradient descent?")

        assert result == "Direct answer."

    def test_calls_client_messages_create_with_user_query(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response()

        generator.generate_response(query="What is overfitting?")

        call_kwargs = mock_client.messages.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is overfitting?"

    def test_uses_bare_system_prompt_when_no_history(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response()

        generator.generate_response(query="test query")

        call_kwargs = mock_client.messages.create.call_args[1]
        system = call_kwargs["system"]
        assert "Previous conversation:" not in system

    def test_includes_conversation_history_in_system_when_provided(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response()

        generator.generate_response(
            query="follow-up question",
            conversation_history="User: prior question\nAssistant: prior answer",
        )

        call_kwargs = mock_client.messages.create.call_args[1]
        system = call_kwargs["system"]
        assert "Previous conversation:" in system
        assert "prior question" in system
        assert "prior answer" in system

    def test_does_not_add_tools_to_api_call_when_tools_is_none(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response()

        generator.generate_response(query="general question", tools=None)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" not in call_kwargs
        assert "tool_choice" not in call_kwargs

    def test_adds_tools_and_tool_choice_when_provided(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response()
        tool_defs = [{"name": "search_course_content", "description": "...", "input_schema": {}}]

        generator.generate_response(query="course question", tools=tool_defs)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == tool_defs
        assert call_kwargs["tool_choice"] == {"type": "auto"}


# ---------------------------------------------------------------------------
# generate_response() — tool use path
# ---------------------------------------------------------------------------

class TestGenerateResponseToolUse:
    def test_returns_synthesized_answer_after_tool_execution(self, generator, mock_client):
        tool_response = make_tool_use_response()
        final_response = make_text_response("Tool result synthesized.")
        mock_client.messages.create.side_effect = [tool_response, final_response]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "search results here"

        result = generator.generate_response(
            query="What is backprop?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        assert result == "Tool result synthesized."

    def test_without_tool_manager_makes_only_one_api_call(self, generator, mock_client):
        """If stop_reason==tool_use but no tool_manager, no second call is made."""
        tool_response = make_tool_use_response()
        mock_client.messages.create.return_value = tool_response

        generator.generate_response(
            query="What is backprop?",
            tools=[{"name": "search_course_content"}],
            tool_manager=None,
        )

        assert mock_client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# _handle_tool_execution()
# ---------------------------------------------------------------------------

class TestHandleToolExecution:
    def _setup(self, mock_client, tool_name="search_course_content",
               tool_id="tool_abc", tool_input=None, final_text="Final answer."):
        if tool_input is None:
            tool_input = {"query": "neural networks"}
        initial_response = make_tool_use_response(tool_name, tool_id, tool_input)
        final_response = make_text_response(final_text)
        mock_client.messages.create.side_effect = [initial_response, final_response]
        return initial_response

    def test_calls_tool_manager_with_correct_name_and_kwargs(self, generator, mock_client):
        self._setup(
            mock_client,
            tool_name="search_course_content",
            tool_input={"query": "backprop", "course_name": "Deep Learning"},
        )
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        generator.generate_response(
            query="Tell me about backprop",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="backprop",
            course_name="Deep Learning",
        )

    def test_makes_exactly_two_api_calls(self, generator, mock_client):
        self._setup(mock_client)
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "some result"

        generator.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        assert mock_client.messages.create.call_count == 2

    def test_second_call_messages_contain_tool_result(self, generator, mock_client):
        self._setup(mock_client, tool_id="tool_xyz", tool_input={"query": "transformers"})
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "transformer explanation"

        generator.generate_response(
            query="What are transformers?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        tool_result_msgs = [
            m for m in messages
            if m["role"] == "user" and isinstance(m["content"], list)
        ]
        assert len(tool_result_msgs) == 1

        content = tool_result_msgs[0]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "tool_result"
        assert content[0]["tool_use_id"] == "tool_xyz"
        assert content[0]["content"] == "transformer explanation"

    def test_second_call_includes_tools_param(self, generator, mock_client):
        # Round 2 is still possible after round 1, so tools must be included
        self._setup(mock_client)
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        generator.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs

    def test_second_call_includes_tool_choice_param(self, generator, mock_client):
        # Round 2 is still possible after round 1, so tool_choice must be included
        self._setup(mock_client)
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        generator.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        assert "tool_choice" in second_call_kwargs

    def test_second_call_includes_assistant_message_with_initial_content(
        self, generator, mock_client
    ):
        initial = self._setup(mock_client)
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        generator.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1
        assert assistant_msgs[0]["content"] == initial.content

    def test_returns_final_response_text(self, generator, mock_client):
        self._setup(mock_client, final_text="Synthesized answer here.")
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "raw result"

        result = generator.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        assert result == "Synthesized answer here."


# ---------------------------------------------------------------------------
# Sequential tool calling (multi-round)
# ---------------------------------------------------------------------------

class TestSequentialToolCalling:
    def test_two_sequential_rounds(self, generator, mock_client):
        """Two tool-use responses followed by end_turn → 3 total API calls, 2 tool executions."""
        tool_1 = make_tool_use_response(tool_id="t1", tool_input={"query": "q1"})
        tool_2 = make_tool_use_response(tool_id="t2", tool_input={"query": "q2"})
        end = make_text_response("Final two-round answer.")
        mock_client.messages.create.side_effect = [tool_1, tool_2, end]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        result = generator.generate_response(
            query="complex question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2
        assert result == "Final two-round answer."

    def test_max_rounds_cap_forces_synthesis_on_third_call(self, generator, mock_client):
        """Even if Claude keeps requesting tools, stop after 2 rounds (3 total calls)."""
        tool_1 = make_tool_use_response(tool_id="t1", tool_input={"query": "q1"})
        tool_2 = make_tool_use_response(tool_id="t2", tool_input={"query": "q2"})
        # Third call would be tool_use but we force synthesis — return text
        forced_synthesis = make_text_response("Forced synthesis.")
        mock_client.messages.create.side_effect = [tool_1, tool_2, forced_synthesis]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        result = generator.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        assert mock_client.messages.create.call_count == 3
        assert result == "Forced synthesis."

    def test_final_synthesis_call_has_no_tools(self, generator, mock_client):
        """The third (synthesis) call must not include tools or tool_choice."""
        tool_1 = make_tool_use_response(tool_id="t1", tool_input={"query": "q1"})
        tool_2 = make_tool_use_response(tool_id="t2", tool_input={"query": "q2"})
        end = make_text_response("Done.")
        mock_client.messages.create.side_effect = [tool_1, tool_2, end]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        generator.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs
        assert "tool_choice" not in third_call_kwargs

    def test_messages_accumulate_across_rounds(self, generator, mock_client):
        """After two rounds the final call's messages list contains all intermediate messages."""
        tool_1 = make_tool_use_response(tool_id="t1", tool_input={"query": "q1"})
        tool_2 = make_tool_use_response(tool_id="t2", tool_input={"query": "q2"})
        end = make_text_response("Done.")
        mock_client.messages.create.side_effect = [tool_1, tool_2, end]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        generator.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Final (3rd) call messages: user, asst_tool1, user_results1, asst_tool2, user_results2
        third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        messages = third_call_kwargs["messages"]

        roles = [m["role"] for m in messages]
        assert roles == ["user", "assistant", "user", "assistant", "user"]

    def test_tool_execution_error_injected_as_tool_result(self, generator, mock_client):
        """If execute_tool raises, the error is injected as the tool result and processing continues."""
        tool_resp = make_tool_use_response(tool_id="t_err", tool_input={"query": "q"})
        end = make_text_response("Recovered.")
        mock_client.messages.create.side_effect = [tool_resp, end]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = Exception("DB error")

        result = generator.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Method must not re-raise — returns the synthesized answer
        assert isinstance(result, str)

        # The error message must appear in the tool_result content sent to Claude
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]
        tool_result_msgs = [
            m for m in messages
            if m["role"] == "user" and isinstance(m["content"], list)
        ]
        content = tool_result_msgs[0]["content"]
        assert "DB error" in content[0]["content"]

    def test_early_termination_after_round_1(self, generator, mock_client):
        """If Claude returns end_turn after round 1, only 2 total API calls are made."""
        tool_resp = make_tool_use_response(tool_id="t1", tool_input={"query": "q1"})
        end = make_text_response("Early finish.")
        mock_client.messages.create.side_effect = [tool_resp, end]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        result = generator.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        assert mock_client.messages.create.call_count == 2
        assert result == "Early finish."
