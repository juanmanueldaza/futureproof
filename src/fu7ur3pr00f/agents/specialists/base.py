"""Base class for specialist agents.

Each specialist agent is a compiled LangGraph agent (via create_agent())
with a curated tool subset and a focused system prompt.

The base class handles:
- Compiling and caching the per-specialist LangGraph graph
- Keyword-based intent routing
- Shared plumbing (model, checkpointer, middleware)
"""

import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Module-level cache: specialist class name → compiled agent graph
_compiled_agents: dict[str, Any] = {}
_agents_lock = threading.Lock()


@dataclass
class KnowledgeResult:
    """A search result from the career knowledge base."""

    content: str
    metadata: dict[str, Any]
    score: float | None = None


@dataclass
class MemoryResult:
    """A recalled episodic memory."""

    content: str
    event_type: str
    timestamp: float | None = None
    score: float | None = None


class BaseAgent(ABC):
    """Abstract base for specialist agents.

    Subclasses must implement:
    - name           : str — agent identifier
    - description    : str — human-readable description
    - system_prompt  : str — specialist persona and instructions
    - tools          : list — curated subset of the 41 career tools
    - can_handle()   : bool — keyword-based intent matching
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier (e.g., 'coach')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Specialist persona and focused instructions.

        Appended to the base system prompt (which already contains the
        user profile and live knowledge base stats) via make_specialist_prompt().
        """
        ...

    @property
    @abstractmethod
    def tools(self) -> list:
        """Curated tool subset for this specialist."""
        ...

    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """Keyword-based intent matching for routing."""
        ...

    # ── Compiled agent ───────────────────────────────────────────────────

    def get_compiled_agent(self) -> Any:
        """Get the compiled LangGraph agent for this specialist (cached).

        Builds on first call using:
        - create_agent() from LangChain
        - This specialist's tools and system_prompt
        - The standard middleware stack (dynamic prompt, tool repair,
          analysis synthesis, summarization)
        - Shared SqliteSaver checkpointer

        Returns:
            Compiled CompiledStateGraph ready for .stream() / .invoke()
        """
        key = type(self).__name__

        if key in _compiled_agents:
            return _compiled_agents[key]

        with _agents_lock:
            if key in _compiled_agents:
                return _compiled_agents[key]

            agent = self._build_agent()
            _compiled_agents[key] = agent
            logger.info(
                "Compiled %s specialist agent (%d tools)", self.name, len(self.tools)
            )
            return agent

    def _build_agent(self) -> Any:
        """Build the compiled LangGraph agent."""
        from langchain.agents import create_agent
        from langchain.agents.middleware.summarization import SummarizationMiddleware

        from fu7ur3pr00f.agents.middleware import (
            AnalysisSynthesisMiddleware,
            ToolCallRepairMiddleware,
            make_specialist_prompt,
        )
        from fu7ur3pr00f.llm.fallback import get_model_with_fallback
        from fu7ur3pr00f.memory.checkpointer import get_checkpointer

        model, config = get_model_with_fallback(purpose="agent")
        logger.info("%s agent using: %s", self.name, config.description)

        summary_model, _ = get_model_with_fallback(purpose="summary")

        return create_agent(
            model=model,
            tools=self.tools,
            middleware=[
                make_specialist_prompt(self.system_prompt),
                ToolCallRepairMiddleware(),
                AnalysisSynthesisMiddleware(),
                SummarizationMiddleware(
                    model=summary_model,
                    trigger=("tokens", 16000),
                    keep=("messages", 20),
                ),
            ],
            checkpointer=get_checkpointer(),
        )


def reset_all_specialists() -> None:
    """Clear all cached compiled specialist agents.

    Call after a model fallback or provider change to force recompilation
    with the new model on the next invocation.
    """
    with _agents_lock:
        _compiled_agents.clear()
    logger.info("All specialist agent caches cleared")
