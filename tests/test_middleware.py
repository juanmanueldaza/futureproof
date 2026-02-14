"""Tests for agent middleware."""

from typing import Any, cast
from unittest.mock import MagicMock

from langchain.agents.middleware.types import AgentState
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from futureproof.agents.middleware import ToolCallRepairMiddleware


def _make_state(messages: list[Any]) -> AgentState[Any]:
    """Build a minimal AgentState dict."""
    return cast(AgentState[Any], {"messages": messages})


def _make_runtime():
    """Build a mock Runtime."""
    return MagicMock()


class TestToolCallRepairMiddleware:
    """Tests for ToolCallRepairMiddleware."""

    def setup_method(self):
        self.middleware = ToolCallRepairMiddleware()
        self.runtime = _make_runtime()

    def test_no_messages(self):
        result = self.middleware.before_model(_make_state([]), self.runtime)
        assert result is None

    def test_no_tool_calls(self):
        state = _make_state(
            [
                HumanMessage(content="hello"),
                AIMessage(content="hi there"),
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is None

    def test_all_tool_calls_matched(self):
        state = _make_state(
            [
                HumanMessage(content="analyze"),
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "tool_a", "args": {}}],
                ),
                ToolMessage(content="result", tool_call_id="call_1"),
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is None

    def test_single_orphaned_tool_call(self):
        state = _make_state(
            [
                HumanMessage(content="analyze"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "call_1", "name": "tool_a", "args": {}},
                        {"id": "call_2", "name": "tool_b", "args": {}},
                    ],
                ),
                ToolMessage(content="result", tool_call_id="call_1"),
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is not None
        assert len(result["messages"]) == 1
        msg = result["messages"][0]
        assert isinstance(msg, ToolMessage)
        assert msg.tool_call_id == "call_2"
        assert "state synchronization error" in msg.content

    def test_all_tool_calls_orphaned(self):
        state = _make_state(
            [
                HumanMessage(content="analyze"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "call_1", "name": "tool_a", "args": {}},
                        {"id": "call_2", "name": "tool_b", "args": {}},
                        {"id": "call_3", "name": "tool_c", "args": {}},
                    ],
                ),
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is not None
        assert len(result["messages"]) == 3
        repair_ids = {m.tool_call_id for m in result["messages"]}
        assert repair_ids == {"call_1", "call_2", "call_3"}

    def test_only_checks_last_ai_message(self):
        """Earlier AIMessage with orphaned tool_calls should be ignored."""
        state = _make_state(
            [
                HumanMessage(content="first"),
                AIMessage(
                    content="",
                    tool_calls=[{"id": "old_call", "name": "tool_a", "args": {}}],
                ),
                # No ToolMessage for old_call — but it's not the last AIMessage
                HumanMessage(content="second"),
                AIMessage(content="plain response"),
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is None

    def test_last_ai_with_tool_calls_has_orphans(self):
        """The last AIMessage with tool_calls has orphans, even if not the very last message."""
        state = _make_state(
            [
                HumanMessage(content="first"),
                AIMessage(content="earlier response"),
                HumanMessage(content="analyze"),
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "tool_a", "args": {}}],
                ),
                # No ToolMessage for call_1
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is not None
        assert len(result["messages"]) == 1
        assert result["messages"][0].tool_call_id == "call_1"
