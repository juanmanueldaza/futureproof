"""Blackboard factory — creates BlackboardExecutor instances for specialist execution.

Provides a factory for creating blackboard executors with the appropriate
specialists and scheduler configuration.

Usage:
    factory = get_blackboard_factory()
    executor = factory.create_executor(["coach", "jobs"])
    blackboard = executor.execute(query=..., user_profile=..., callbacks=...)
"""

import logging
from typing import Any

from fu7ur3pr00f.agents.blackboard.executor import BlackboardExecutor
from fu7ur3pr00f.agents.blackboard.scheduler import BlackboardScheduler
from fu7ur3pr00f.agents.specialists.base import BaseAgent

logger = logging.getLogger(__name__)


class BlackboardFactory:
    """Factory for creating BlackboardExecutor instances.

    Manages specialist agent registration and creates executors with
    appropriate scheduler configuration.

    Usage:
        factory = BlackboardFactory()
        factory.register_specialist("coach", coach_agent)
        executor = factory.create_executor(["coach", "jobs"])
    """

    def __init__(self) -> None:
        self._specialists: dict[str, BaseAgent] = {}

    def register_specialist(self, name: str, agent: BaseAgent) -> None:
        """Register a specialist agent.

        Args:
            name: Specialist identifier (e.g., "coach", "jobs")
            agent: Specialist agent instance
        """
        self._specialists[name] = agent
        logger.info("Registered specialist: %s", name)

    def create_executor(
        self,
        specialist_names: list[str] | None = None,
        max_iterations: int = 1,
        strategy: str = "linear",
    ) -> BlackboardExecutor:
        """Create a BlackboardExecutor with the requested specialists.

        Args:
            specialist_names: Which specialists to include.
                If None, includes all registered specialists.
            max_iterations: Maximum blackboard iterations (default 1)
            strategy: Scheduling strategy ("linear", "smart", etc.)

        Returns:
            Configured BlackboardExecutor ready to run

        Raises:
            ValueError: If no specialists are available
        """
        if specialist_names is None:
            selected = self._specialists.copy()
        else:
            selected = {
                name: self._specialists[name]
                for name in specialist_names
                if name in self._specialists
            }
            if not selected:
                logger.warning(
                    "No valid specialists found in %r, using all available",
                    specialist_names,
                )
                selected = self._specialists.copy()

        if not selected:
            raise ValueError("No specialists registered with BlackboardFactory")

        scheduler = BlackboardScheduler(
            strategy=strategy,
            max_iterations=max_iterations,
            execution_order=list(selected.keys()),
        )

        logger.info(
            "Created BlackboardExecutor with %d specialists: %s",
            len(selected),
            list(selected.keys()),
        )

        return BlackboardExecutor(
            specialists=selected,
            scheduler=scheduler,
        )

    def get_specialist(self, name: str) -> BaseAgent:
        """Get a registered specialist by name.

        Args:
            name: Specialist identifier

        Returns:
            Specialist agent instance

        Raises:
            KeyError: If specialist not found
        """
        if name not in self._specialists:
            raise KeyError(f"Specialist {name!r} not found")
        return self._specialists[name]

    def list_specialists(self) -> list[str]:
        """List all registered specialist names."""
        return list(self._specialists.keys())

    def clear(self) -> None:
        """Clear all registered specialists."""
        self._specialists.clear()
        logger.info("Cleared all registered specialists")


# ── Module-level factory with default specialists ─────────────────────────────

_default_factory: BlackboardFactory | None = None
_factory_lock = __import__("threading").Lock()


def get_blackboard_factory() -> BlackboardFactory:
    """Get or create the default blackboard factory with standard specialists.

    The default factory is pre-populated with the 5 standard specialists:
    coach, learning, jobs, code, founder

    Returns:
        BlackboardFactory instance with default specialists registered
    """
    global _default_factory
    if _default_factory is not None:
        return _default_factory

    with _factory_lock:
        if _default_factory is not None:
            return _default_factory

        _default_factory = BlackboardFactory()

        # Register default specialists
        from fu7ur3pr00f.agents.specialists.coach import CoachAgent
        from fu7ur3pr00f.agents.specialists.code import CodeAgent
        from fu7ur3pr00f.agents.specialists.founder import FounderAgent
        from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
        from fu7ur3pr00f.agents.specialists.learning import LearningAgent

        _default_factory.register_specialist("coach", CoachAgent())
        _default_factory.register_specialist("learning", LearningAgent())
        _default_factory.register_specialist("jobs", JobsAgent())
        _default_factory.register_specialist("code", CodeAgent())
        _default_factory.register_specialist("founder", FounderAgent())

        logger.info(
            "Default BlackboardFactory initialised with %d specialists",
            len(_default_factory._specialists),
        )

    return _default_factory


def reset_blackboard_factory() -> None:
    """Reset the default factory singleton."""
    global _default_factory
    with _factory_lock:
        _default_factory = None


def get_agent_config(
    thread_id: str = "main",
    user_id: str = "default",
) -> dict[str, Any]:
    """Build the LangGraph config dict for blackboard execution.

    Args:
        thread_id: Thread identifier for conversation tracking
        user_id: User identifier for personalization

    Returns:
        Config dict for LangGraph agent execution
    """
    return {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        }
    }


__all__ = [
    "BlackboardFactory",
    "get_blackboard_factory",
    "reset_blackboard_factory",
    "get_agent_config",
]
