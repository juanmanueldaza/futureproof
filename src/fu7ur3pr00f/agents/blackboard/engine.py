"""Conversation engine — high-level interface to the session graph.

Wraps the outer conversation graph and provides a simple invoke_turn()
method for the chat client.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from fu7ur3pr00f.agents.blackboard.conversation_graph import build_conversation_graph
from fu7ur3pr00f.agents.blackboard.session import SessionState, make_initial_session
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
    """

    def __init__(self) -> None:
        """Initialize the engine."""
        self._graph = build_conversation_graph()
        self._checkpointer = get_checkpointer()

    def invoke_turn(
        self,
        query: str,
        thread_id: str = "main",
        user_profile: dict[str, Any] | None = None,
    ) -> TurnResult:
        """Execute a single conversation turn.

        Args:
            query: User's question
            thread_id: Conversation thread identifier
            user_profile: User's career profile (loaded fresh if not provided)

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
            }

        config = {"configurable": {"thread_id": thread_id}}
        start = time.monotonic()

        # Get or initialize session state
        snap = self._graph.get_state(config)
        if snap and snap.values:
            session_state = dict(snap.values)  # type: ignore
        else:
            session_state = make_initial_session(user_profile)

        # Update for this turn
        session_state["current_query"] = query
        session_state["user_profile"] = user_profile

        # Invoke graph for this turn
        logger.debug("Turn: %r (thread=%s)", query[:60], thread_id)
        result_state = self._graph.invoke(session_state, config)

        elapsed = time.monotonic() - start

        # Extract results
        synthesis = result_state.get("synthesis", {})
        specialists = result_state.get("routed_specialists", [])
        suggested = result_state.get("suggested_next", [])
        cumulative = result_state.get("cumulative_findings", {})

        return TurnResult(
            synthesis=synthesis,
            specialists=specialists,
            elapsed=elapsed,
            suggested_next=suggested,
            cumulative_findings=cumulative,
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
    """Reset the engine singleton (useful for testing/reloading)."""
    global _engine
    _engine = None


__all__ = [
    "ConversationEngine",
    "TurnResult",
    "get_conversation_engine",
    "reset_conversation_engine",
]
