"""Agent middleware for state repair."""

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)


class ToolCallRepairMiddleware(AgentMiddleware):
    """Detects and repairs orphaned tool_calls in message history.

    When parallel tool execution via the Send API fails to merge results
    back into the messages channel, this middleware injects synthetic error
    ToolMessages so the model can proceed instead of crashing with a 400
    "tool_call_ids did not have response messages" error.

    Must be placed before SummarizationMiddleware in the middleware list
    so repairs happen before any message summarization.
    """

    def before_model(self, state: AgentState[Any], runtime: Runtime) -> dict[str, Any] | None:
        messages = state["messages"]
        if not messages:
            return None

        # Find the last AIMessage (scan from end)
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if not isinstance(msg, AIMessage):
                continue

            if not msg.tool_calls:
                return None  # Last AIMessage has no tool_calls — nothing to repair

            # Collect tool_call_ids that have matching ToolMessages after this AIMessage
            expected_ids = {tc["id"] for tc in msg.tool_calls if tc.get("id")}
            found_ids: set[str] = set()
            for j in range(i + 1, len(messages)):
                tmsg = messages[j]
                if isinstance(tmsg, ToolMessage) and tmsg.tool_call_id:
                    found_ids.add(tmsg.tool_call_id)

            missing_ids = expected_ids - found_ids
            if not missing_ids:
                return None  # All tool_calls have matching responses

            logger.warning(
                "Repairing %d orphaned tool_call(s): %s",
                len(missing_ids),
                missing_ids,
            )
            return {
                "messages": [
                    ToolMessage(
                        content=(
                            "Tool execution failed — results were lost due to a "
                            "state synchronization error. Please retry if needed."
                        ),
                        tool_call_id=tid,
                    )
                    for tid in missing_ids
                ]
            }

        return None
