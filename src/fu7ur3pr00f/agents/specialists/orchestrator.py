"""Orchestrator — routes queries to the right specialist and exposes their agent.

The orchestrator is the single entry point for all user messages.  It does
keyword-based routing (no LLM call, sub-millisecond) and then returns the
compiled specialist agent for the chat client to stream against directly.

Usage (from the chat client):
    orchestrator = get_orchestrator()

    # Route a query → get the compiled LangGraph agent for streaming
    specialist_name = orchestrator.route(user_input)
    agent = orchestrator.get_compiled_agent(specialist_name)
    agent.stream({"messages": [HumanMessage(content=user_input)]}, config, ...)
"""

import logging
import threading
from typing import Any

from fu7ur3pr00f.agents.specialists.base import BaseAgent, reset_all_specialists
from fu7ur3pr00f.agents.specialists.coach import CoachAgent
from fu7ur3pr00f.agents.specialists.code import CodeAgent
from fu7ur3pr00f.agents.specialists.founder import FounderAgent
from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
from fu7ur3pr00f.agents.specialists.learning import LearningAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Routes user queries to specialist agents.

    Routing is keyword-based — no LLM call, deterministic and fast.
    Each specialist is a compiled LangGraph agent (cached on first use).
    All specialists share the same SqliteSaver checkpointer so conversation
    history is continuous across specialist switches within a thread.
    """

    def __init__(self) -> None:
        self._specialists: dict[str, BaseAgent] = {
            "coach": CoachAgent(),
            "learning": LearningAgent(),
            "jobs": JobsAgent(),
            "code": CodeAgent(),
            "founder": FounderAgent(),
        }

    # ── Routing ──────────────────────────────────────────────────────────

    def route(self, query: str) -> str:
        """Pick the best specialist for this query.

        Scores each specialist by counting keyword matches.  Returns the
        specialist name with the highest score, defaulting to "coach" for
        ambiguous queries.
        """
        best_name = "coach"
        best_score = 0
        intent = query.lower()

        for name, agent in self._specialists.items():
            keywords: frozenset[str] = getattr(agent, "KEYWORDS", frozenset())
            score = sum(1 for kw in keywords if kw in intent)
            if score > best_score:
                best_score = score
                best_name = name

        logger.debug("route(%r) → %s (score=%d)", query[:60], best_name, best_score)
        return best_name

    # ── Agent access ─────────────────────────────────────────────────────

    def get_compiled_agent(self, specialist_name: str) -> Any:
        """Return the compiled LangGraph agent for the given specialist.

        Lazily compiled and cached on first call — subsequent calls return
        the same graph without re-building.
        """
        specialist = self._specialists.get(specialist_name)
        if specialist is None:
            logger.warning(
                "Unknown specialist %r, falling back to coach", specialist_name
            )
            specialist = self._specialists["coach"]
        return specialist.get_compiled_agent()

    def get_specialist(self, name: str) -> BaseAgent:
        """Return the specialist agent object by name."""
        return self._specialists.get(name, self._specialists["coach"])

    # ── Info ─────────────────────────────────────────────────────────────

    def list_agents(self) -> list[dict[str, str]]:
        """List all available specialists."""
        return [
            {"name": a.name, "description": a.description}
            for a in self._specialists.values()
        ]

    def get_model_name(self, specialist_name: str | None = None) -> str | None:
        """Return the model description used by the given specialist (or coach)."""
        try:
            from fu7ur3pr00f.llm.fallback import get_model_with_fallback

            _, config = get_model_with_fallback(purpose="agent")
            return config.description
        except Exception:
            return None

    def reset(self) -> None:
        """Clear all compiled specialist agent caches.

        Call after a model fallback or provider change so the next
        invocation recompiles with the new model.
        """
        reset_all_specialists()


# ── Module-level singleton ────────────────────────────────────────────────────

_orchestrator: OrchestratorAgent | None = None
_orchestrator_lock = threading.Lock()


def get_orchestrator() -> OrchestratorAgent:
    """Get or create the global orchestrator singleton."""
    global _orchestrator
    if _orchestrator is not None:
        return _orchestrator
    with _orchestrator_lock:
        if _orchestrator is None:
            _orchestrator = OrchestratorAgent()
            logger.info(
                "Orchestrator initialised with %d specialists",
                len(_orchestrator._specialists),
            )
    return _orchestrator


def reset_orchestrator() -> None:
    """Reset the orchestrator singleton and all compiled agent caches."""
    global _orchestrator
    with _orchestrator_lock:
        if _orchestrator is not None:
            _orchestrator.reset()
        _orchestrator = None


def get_agent_config(
    thread_id: str = "main",
    user_id: str = "default",
) -> dict[str, Any]:
    """Build the LangGraph config dict for invoking a specialist agent.

    Args:
        thread_id: Conversation thread identifier for checkpointing
        user_id: User identifier for profile/memory scoping

    Returns:
        Config dict to pass to agent.invoke() or agent.stream()
    """
    return {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        }
    }


__all__ = [
    "OrchestratorAgent",
    "get_orchestrator",
    "reset_orchestrator",
    "get_agent_config",
]
