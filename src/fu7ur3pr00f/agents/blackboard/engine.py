"""Conversation engine — high-level interface to the session graph.

Wraps the outer conversation graph and provides a simple invoke_turn()
method for the chat client.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fu7ur3pr00f.memory.checkpointer import get_checkpointer

logger = logging.getLogger(__name__)


@dataclass
class TurnResult:
    """Result of a single conversation turn."""

    synthesis: dict[str, Any]
    """The synthesis narrative returned to user"""

    specialists: list[str]
    """Specialists that ran"""

    elapsed: float
    """Execution time in seconds"""

    suggested_next: list[str]
    """Suggested follow-ups"""

    cumulative_findings: dict[str, Any]
    """Accumulated findings across conversation"""


class ConversationEngine:
    """High-level interface to conversational blackboard.

    Manages turn-by-turn execution via the outer graph, persisting
    session state across turns via LangGraph checkpointer.

    Callbacks wired here are passed through to the inner blackboard
    executor for real-time progress display.
    """

    def __init__(self) -> None:
        """Initialize the engine with checkpointer-backed graph."""
        # Import here to avoid circular dependency at module load
        from fu7ur3pr00f.agents.blackboard.conversation_graph import (
            build_conversation_graph,
        )

        checkpointer = get_checkpointer()
        # Graph is compiled without callbacks — they are passed per-turn
        # to allow different UIs to use the same engine
        self._checkpointer = checkpointer
        self._build_graph = build_conversation_graph

    def invoke_turn(
        self,
        query: str,
        thread_id: str = "main",
        user_profile: dict[str, Any] | None = None,
        on_specialist_start: Callable[[str], None] | None = None,
        on_specialist_complete: Callable[[str, dict], None] | None = None,
        on_tool_start: Callable[[str, str, dict], None] | None = None,
        on_tool_result: Callable[[str, str, str], None] | None = None,
        confirm_fn: Callable[[str, str], bool] | None = None,
    ) -> TurnResult:
        """Execute a single conversation turn.

        Args:
            query: User's question
            thread_id: Conversation thread identifier (determines session)
            user_profile: User's career profile (loaded from disk if not provided)
            on_specialist_start: Called when specialist starts working
            on_specialist_complete: Called when specialist completes
            on_tool_start: Called when a tool is invoked
            on_tool_result: Called when a tool returns a result
            confirm_fn: Human-in-the-loop confirmation for tool interrupts

        Returns:
            TurnResult with synthesis, specialists, elapsed time, suggestions
        """
        if user_profile is None:
            from fu7ur3pr00f.memory.profile import load_profile

            profile = load_profile()
            user_profile = {
                "name": profile.name,
                "current_role": profile.current_role,
                "years_experience": profile.years_experience,
                "technical_skills": profile.technical_skills or [],
                "target_roles": profile.target_roles or [],
                "goals": [g.description for g in (profile.goals or [])],
                "github_username": profile.github_username or "",
                "gitlab_username": profile.gitlab_username or "",
            }

        # Build graph with callbacks closed-over for this turn
        graph = self._build_graph(
            checkpointer=self._checkpointer,
            on_specialist_start=on_specialist_start,
            on_specialist_complete=on_specialist_complete,
            on_tool_start=on_tool_start,
            on_tool_result=on_tool_result,
            confirm_fn=confirm_fn,
        )

        config = {"configurable": {"thread_id": thread_id}}
        start = time.monotonic()

        # Load existing session or start fresh
        from fu7ur3pr00f.agents.blackboard.session import make_initial_session

        snap = graph.get_state(config)  # type: ignore[arg-type]
        if snap and snap.values:
            session_state = dict(snap.values)  # type: ignore
        else:
            session_state = make_initial_session(  # type: ignore[assignment]
                user_profile
            )

        # Update for this turn
        session_state["current_query"] = query
        session_state["user_profile"] = user_profile

        logger.debug("Turn: %r (thread=%s)", query[:60], thread_id)
        result_state = graph.invoke(session_state, config)  # type: ignore[arg-type]

        elapsed = time.monotonic() - start

        return TurnResult(
            synthesis=result_state.get("synthesis", {}),
            specialists=result_state.get("routed_specialists", []),
            elapsed=elapsed,
            suggested_next=result_state.get("suggested_next", []),
            cumulative_findings=result_state.get("cumulative_findings", {}),
        )


# Module-level singleton
_engine: ConversationEngine | None = None


def get_conversation_engine() -> ConversationEngine:
    """Get or create the global conversation engine."""
    global _engine
    if _engine is None:
        _engine = ConversationEngine()
    return _engine


def reset_conversation_engine() -> None:
    """Reset the engine singleton (e.g. after provider/model change)."""
    global _engine
    _engine = None


__all__ = [
    "ConversationEngine",
    "TurnResult",
    "get_conversation_engine",
    "reset_conversation_engine",
]
