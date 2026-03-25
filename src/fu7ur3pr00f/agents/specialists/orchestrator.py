"""Orchestrator Agent — Routes requests to specialist agents.

Uses keyword scoring for fast routing, then delegates to the appropriate
specialist agent which calls the LLM with its focused system prompt.
"""

import asyncio
import logging
from typing import Any

from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.specialists.coach import CoachAgent
from fu7ur3pr00f.agents.specialists.code import CodeAgent
from fu7ur3pr00f.agents.specialists.founder import FounderAgent
from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
from fu7ur3pr00f.agents.specialists.learning import LearningAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Routes queries to specialist agents and returns their LLM-powered responses.

    Routing is keyword-based (fast, no LLM call for routing).
    Each specialist handles its own LLM call with a focused system prompt.
    """

    specialists: dict[str, BaseAgent]

    def __init__(self) -> None:
        self.specialists = {}

    @property
    def name(self) -> str:
        return "orchestrator"

    @property
    def description(self) -> str:
        return "Routes requests to specialist agents"

    @property
    def system_prompt(self) -> str:
        return ""  # Orchestrator doesn't call LLM directly

    def can_handle(self, intent: str) -> bool:
        return True  # Routes everything

    async def initialize(self) -> None:
        """Initialize all specialist agents."""
        self.specialists = {
            "coach": CoachAgent(),
            "learning": LearningAgent(),
            "jobs": JobsAgent(),
            "code": CodeAgent(),
            "founder": FounderAgent(),
        }
        logger.info(
            "Orchestrator initialized with %d specialists: %s",
            len(self.specialists),
            ", ".join(self.specialists.keys()),
        )

    async def process(self, context: dict[str, Any]) -> str:
        """Route query to best specialist and return its LLM response."""
        query = context.get("query", "")
        specialist_name = self._route(query)
        specialist = self.specialists.get(specialist_name)

        if not specialist:
            return self._fallback_message()

        logger.info("Routing to %s agent: %s", specialist_name, query[:80])
        return await specialist.process(context)

    async def process_parallel(
        self,
        context: dict[str, Any],
        agent_names: list[str] | None = None,
    ) -> dict[str, str]:
        """Query multiple specialists in parallel.

        Returns dict mapping agent name → response.
        """
        if agent_names is None:
            agent_names = list(self.specialists.keys())

        async def _run(name: str) -> tuple[str, str]:
            agent = self.specialists.get(name)
            if agent:
                resp = await agent.process(context)
                return name, resp
            return name, ""

        results = await asyncio.gather(*[_run(n) for n in agent_names])
        return dict(results)

    def _route(self, query: str) -> str:
        """Score each specialist by keyword overlap and pick the best."""
        best_name = "coach"  # Default
        best_score = 0

        for name, agent in self.specialists.items():
            if agent.can_handle(query):
                # Count keyword matches for ranking
                intent_lower = query.lower()
                keywords: frozenset[str] = getattr(agent, "KEYWORDS", frozenset())
                score = sum(1 for kw in keywords if kw in intent_lower)
                if score > best_score:
                    best_score = score
                    best_name = name

        return best_name

    def _fallback_message(self) -> str:
        agents = "\n".join(
            f"- **{a.name}**: {a.description}" for a in self.specialists.values()
        )
        return (
            "I can help you with:\n\n"
            f"{agents}\n\n"
            "Which area would you like to explore?"
        )

    async def handle(self, query: str, context: dict[str, Any] | None = None) -> str:
        """Convenience: handle a query string."""
        if context is None:
            context = {}
        context["query"] = query
        return await self.process(context)

    def get_available_agents(self) -> list[dict[str, str]]:
        """List available specialist agents."""
        return [
            {"name": a.name, "description": a.description}
            for a in self.specialists.values()
        ]


__all__ = ["OrchestratorAgent"]
