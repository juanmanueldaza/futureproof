"""Orchestrator — routes queries to specialists via the blackboard pattern.

Thin wrapper that coordinates RoutingService and BlackboardFactory.
All queries run through the blackboard pattern.

Usage (from the chat client):
    orchestrator = get_orchestrator()
    result = orchestrator.route(user_input)  # RoutingResult
    executor = orchestrator.get_executor(result.specialists)
    blackboard = executor.execute(query=..., user_profile=..., callbacks=...)
"""

import logging

from fu7ur3pr00f.agents.blackboard.executor import BlackboardExecutor
from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.specialists.blackboard_factory import get_blackboard_factory
from fu7ur3pr00f.agents.specialists.routing import RoutingResult, get_routing_service

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Orchestrates query routing and blackboard execution.

    Delegates to RoutingService for specialist selection and
    BlackboardFactory for executor creation.

    Usage:
        orchestrator = get_orchestrator()
        result = orchestrator.route(query)
        executor = orchestrator.get_executor(result.specialists)
    """

    def __init__(self) -> None:
        self._routing = get_routing_service()
        self._factory = get_blackboard_factory()

    def route(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        turn_type: str | None = None,
    ) -> list[str]:
        """Route query to one or more specialists.

        Uses LLM-based semantic routing with keyword fallback.
        Returns a list of specialist names (backward-compatible API).

        Args:
            query: User's query
            conversation_history: Prior turns (optional, for context-aware routing)
            turn_type: Turn classification (optional, from turn_classifier)

        Returns:
            List of specialist names to handle the query
        """
        result = self._routing.route(query, conversation_history, turn_type)
        return result.specialists

    def route_with_result(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        turn_type: str | None = None,
    ) -> RoutingResult:
        """Route query and return full RoutingResult with metadata.

        Use this when you need routing method and confidence information.

        Args:
            query: User's query
            conversation_history: Prior turns (optional)
            turn_type: Turn classification (optional)

        Returns:
            RoutingResult with specialists, method, and confidence
        """
        return self._routing.route(query, conversation_history, turn_type)

    def get_executor(
        self,
        specialist_names: list[str] | None = None,
        max_iterations: int = 1,
        strategy: str = "linear",
    ) -> BlackboardExecutor:
        """Get a BlackboardExecutor with the requested specialists.

        Args:
            specialist_names: Which specialists to include (from route()).
                If None, includes all specialists.
            max_iterations: Maximum blackboard iterations (default 1)
            strategy: Scheduling strategy (default "linear")

        Returns:
            Executor ready to run blackboard-based analysis
        """
        return self._factory.create_executor(
            specialist_names=specialist_names,
            max_iterations=max_iterations,
            strategy=strategy,
        )

    def get_specialist(self, name: str) -> BaseAgent:
        """Return the specialist agent object by name."""
        return self._routing.get_specialist(name)

    def list_agents(self) -> list[dict[str, str]]:
        """List all available specialists."""
        return self._routing.list_agents()

    def get_model_name(self, specialist_name: str | None = None) -> str | None:
        """Return the model description used by specialists."""
        try:
            from fu7ur3pr00f.llm.fallback import get_model_with_fallback

            _, config = get_model_with_fallback(purpose="agent")
            return config.description
        except Exception:
            logger.warning(
                "get_model_name() failed for %s",
                specialist_name,
                exc_info=True,
            )
            return None

    def reset(self) -> None:
        """Reset orchestrator state (delegates to routing and factory)."""
        self._routing.reset()
        logger.debug("Orchestrator.reset() called")


# ── Module-level singleton ────────────────────────────────────────────────────

_orchestrator: OrchestratorAgent | None = None
_orchestrator_lock = __import__("threading").Lock()


def get_orchestrator() -> OrchestratorAgent:
    """Get or create the global orchestrator singleton."""
    global _orchestrator
    if _orchestrator is not None:
        return _orchestrator
    with _orchestrator_lock:
        if _orchestrator is None:
            _orchestrator = OrchestratorAgent()
            logger.info(
                "Orchestrator initialised (routing + blackboard factory)",
            )
    return _orchestrator


def reset_orchestrator() -> None:
    """Reset the orchestrator and underlying services."""
    global _orchestrator
    with _orchestrator_lock:
        _orchestrator = None
    from fu7ur3pr00f.agents.specialists.blackboard_factory import (
        reset_blackboard_factory,
    )
    from fu7ur3pr00f.agents.specialists.routing import reset_routing_service

    reset_routing_service()
    reset_blackboard_factory()


__all__ = [
    "OrchestratorAgent",
    "get_orchestrator",
    "reset_orchestrator",
]
