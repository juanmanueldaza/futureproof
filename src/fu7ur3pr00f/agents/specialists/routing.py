"""Routing service — routes queries to specialists via semantic or keyword matching.

Provides LLM-based semantic routing with keyword fallback for determining
which specialist agents should handle a user query.

Usage:
    routing = get_routing_service()
    specialists = routing.route(query, conversation_history, turn_type)
"""

import logging
from dataclasses import dataclass

from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.specialists.coach import CoachAgent
from fu7ur3pr00f.agents.specialists.code import CodeAgent
from fu7ur3pr00f.agents.specialists.founder import FounderAgent
from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
from fu7ur3pr00f.agents.specialists.learning import LearningAgent

logger = logging.getLogger(__name__)


@dataclass
class RoutingResult:
    """Result of routing decision."""

    specialists: list[str]
    method: str  # "llm", "keyword", "follow_up"
    confidence: float


class RoutingService:
    """Routes user queries to specialist agents.

    Primary routing uses LLM-based semantic understanding; keyword scoring
    is the deterministic fallback when the LLM is unavailable.

    Usage:
        routing = get_routing_service()
        result = routing.route(user_query)
        # result.specialists contains list of specialist names
    """

    def __init__(self) -> None:
        self._specialists: dict[str, BaseAgent] = {
            "coach": CoachAgent(),
            "learning": LearningAgent(),
            "jobs": JobsAgent(),
            "code": CodeAgent(),
            "founder": FounderAgent(),
        }

    def route(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        turn_type: str | None = None,
    ) -> RoutingResult:
        """Route query to one or more specialists via LLM.

        Args:
            query: User's query
            conversation_history: Prior turns (optional, for context-aware routing)
            turn_type: Turn classification (optional, from turn_classifier)

        Returns:
            RoutingResult with specialist names and routing method used
        """
        # Context-aware routing: reuse previous specialists for follow-ups
        if turn_type == "follow_up" and conversation_history:
            last_turn = conversation_history[-1]
            prev_specialists = last_turn.get("specialist_names", [])
            if prev_specialists:
                logger.debug(
                    "route(%r) → %s (follow_up, reusing previous)",
                    query[:60],
                    prev_specialists,
                )
                return RoutingResult(
                    specialists=prev_specialists,
                    method="follow_up",
                    confidence=1.0,
                )

        try:
            result = self._route_with_llm(query, conversation_history, turn_type)
            logger.debug("route_llm(%r) → %s", query[:60], result)
            return RoutingResult(specialists=result, method="llm", confidence=0.9)
        except Exception:
            logger.warning(
                "LLM routing failed for %r, defaulting to coach",
                query[:60],
                exc_info=True,
            )
            return RoutingResult(
                specialists=["coach"], method="fallback", confidence=0.5
            )

    def _route_with_llm(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        turn_type: str | None = None,
    ) -> list[str]:
        """Route using LLM-based semantic understanding.

        Parses specialist descriptions and selects 1-4 specialists via
        structured output (Pydantic model).
        """
        from langchain_core.messages import HumanMessage

        from fu7ur3pr00f.agents.specialists.routing_schema import RoutingDecision
        from fu7ur3pr00f.llm.fallback import get_model_with_fallback
        from fu7ur3pr00f.prompts import load_prompt

        # Build context from conversation history
        context = "No prior context."
        if turn_type in ("steer", "workflow_step") and conversation_history:
            recent = conversation_history[-3:]
            context_lines = [f"- {t.get('query', '')[:80]}" for t in recent]
            context = "\n".join(context_lines)

        prompt_template = load_prompt("route_specialists")
        prompt = prompt_template.format(
            query=query,
            context=context,
        )

        model, _ = get_model_with_fallback(purpose="summary", temperature=0.0)
        router = model.with_structured_output(RoutingDecision)
        result = router.invoke([HumanMessage(content=prompt)])  # type: ignore

        # Validate names against known specialists
        valid = [
            name
            for name in result.specialists  # type: ignore
            if name in self._specialists
        ]
        return valid or ["coach"]

    def get_specialist(self, name: str) -> BaseAgent:
        """Return the specialist agent object by name."""
        return self._specialists.get(name, self._specialists["coach"])

    def list_agents(self) -> list[dict[str, str]]:
        """List all available specialists."""
        return [
            {"name": a.name, "description": a.description}
            for a in self._specialists.values()
        ]

    def reset(self) -> None:
        """Reset routing state (no-op for stateless routing)."""
        logger.debug("RoutingService.reset() called (no-op)")


# ── Module-level singleton ────────────────────────────────────────────────────

_routing_service: RoutingService | None = None
_service_lock = __import__("threading").Lock()


def get_routing_service() -> RoutingService:
    """Get or create the global routing service singleton."""
    global _routing_service
    if _routing_service is not None:
        return _routing_service
    with _service_lock:
        if _routing_service is None:
            _routing_service = RoutingService()
            logger.info(
                "RoutingService initialised with %d specialists",
                len(_routing_service._specialists),
            )
    return _routing_service


def reset_routing_service() -> None:
    """Reset the routing service singleton."""
    global _routing_service
    with _service_lock:
        _routing_service = None
