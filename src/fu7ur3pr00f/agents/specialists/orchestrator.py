"""Orchestrator — routes queries to the right specialist(s) via the blackboard.

All queries run through the blackboard pattern. The orchestrator uses
LLM-based semantic routing (with keyword fallback) to select which
specialists contribute, then delegates execution to BlackboardExecutor.

Routing strategy:
- Primary: LLM semantic routing via _route_with_llm() (purpose="summary")
- Fallback: keyword scoring via _route_with_keywords() (deterministic)
- Fast paths: factual queries → coach; follow-ups → reuse previous

Usage (from the chat client):
    orchestrator = get_orchestrator()
    specialist_names = orchestrator.route(user_input)  # always list[str]
    executor = orchestrator.get_blackboard_executor(specialist_names)
    blackboard = executor.execute(query=..., user_profile=..., callbacks=...)
"""

import logging
import threading
from typing import Any

from fu7ur3pr00f.agents.blackboard.executor import BlackboardExecutor
from fu7ur3pr00f.agents.blackboard.scheduler import BlackboardScheduler
from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.specialists.coach import CoachAgent
from fu7ur3pr00f.agents.specialists.code import CodeAgent
from fu7ur3pr00f.agents.specialists.founder import FounderAgent
from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
from fu7ur3pr00f.agents.specialists.learning import LearningAgent

logger = logging.getLogger(__name__)

# Keyword groups that indicate a comprehensive, multi-specialist query
_MULTI_SPECIALIST_KEYWORDS: list[str] = [
    "5 year",
    "future",
    "predict",
    "overall",
    "complete",
    "all agent",
    "make all",
    "comprehensive",
    "full picture",
    "career path",
    "trajectory",
    "opportunity",
    "option",
    "possibility",
    "alternative",
    "strategy",
    "plan",
    "roadmap",
    "leverage",
    "strengths",
    "earn more",
    "more money",
    "income",
    "grow",
    "advance",
    "transition",
    "next level",
    "improve",
    "how can i",
    "help me",
]


class OrchestratorAgent:
    """Routes user queries to specialist agents via the blackboard pattern.

    Primary routing uses LLM-based semantic understanding; keyword scoring
    is the deterministic fallback when the LLM is unavailable.
    route() always returns a list[str] of 1-4 specialist names.
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

    def route(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        turn_type: str | None = None,
    ) -> list[str]:
        """Route query to one or more specialists.

        Uses LLM-based semantic routing with keyword fallback.
        Returns a list of specialist names to involve (always a list, 1-4 items).

        Args:
            query: User's query
            conversation_history: Prior turns (optional, for context-aware routing)
            turn_type: Turn classification (optional, from turn_classifier)
        """
        # Context-aware routing: reuse previous specialists for follow-ups
        if (
            turn_type == "follow_up"
            and conversation_history
            and len(conversation_history) > 0
        ):
            last_turn = conversation_history[-1]
            prev_specialists = last_turn.get("specialist_names", [])
            if prev_specialists:
                logger.debug(
                    "route(%r) → %s (follow_up, reusing previous)",
                    query[:60],
                    prev_specialists,
                )
                return prev_specialists

        # Try LLM-based semantic routing first
        try:
            result = self._route_with_llm(query, conversation_history, turn_type)
            logger.debug("route_llm(%r) → %s", query[:60], result)
            return result
        except Exception as e:
            logger.debug(
                "LLM routing failed (%s), falling back to keywords", e
            )

        # Keyword fallback
        return self._route_with_keywords(query)

    def _route_with_keywords(self, query: str) -> list[str]:
        """Route using keyword matching (fallback path).

        Scores specialists by keyword match count and selects 1-4 specialists.
        """
        # Normalize hyphens so "5-year" matches "5 year"
        intent = query.lower().replace("-", " ")

        # Score all specialists by keyword match count
        scores: dict[str, int] = {}
        for name, agent in self._specialists.items():
            keywords: frozenset[str] = getattr(agent, "KEYWORDS", frozenset())
            scores[name] = sum(1 for kw in keywords if kw in intent)

        # Detect comprehensive / multi-specialist queries
        is_comprehensive = any(kw in intent for kw in _MULTI_SPECIALIST_KEYWORDS)

        if is_comprehensive:
            sorted_specs = sorted(
                scores.items(), key=lambda x: x[1], reverse=True
            )
            result = ["coach"]
            for name, _score in sorted_specs:
                if name != "coach" and len(result) < 4:
                    result.append(name)
            logger.debug("route_keywords_multi(%r) → %s", query[:60], result)
            return result

        # Single specialist: highest scorer, default coach
        best_name = max(scores, key=lambda n: scores[n], default="coach")
        if scores.get(best_name, 0) == 0:
            best_name = "coach"
        logger.debug(
            "route_keywords(%r) → [%s] (score=%d)",
            query[:60],
            best_name,
            scores.get(best_name, 0),
        )
        return [best_name]

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
            context_lines = [
                f"- {t.get('query', '')[:80]}" for t in recent
            ]
            context = "\n".join(context_lines)

        prompt_template = load_prompt("route_specialists")
        prompt = prompt_template.format(
            query=query,
            context=context,
        )

        model, _ = get_model_with_fallback(
            purpose="summary", temperature=0.0
        )
        router = model.with_structured_output(RoutingDecision)
        result = router.invoke([HumanMessage(content=prompt)])  # type: ignore

        # Validate names against known specialists
        valid = [
            name for name in result.specialists  # type: ignore
            if name in self._specialists
        ]
        return valid or ["coach"]

    # ── Blackboard execution ──────────────────────────────────────────────

    def get_blackboard_executor(
        self,
        specialist_names: list[str] | None = None,
    ) -> BlackboardExecutor:
        """Get a BlackboardExecutor with only the requested specialists.

        Args:
            specialist_names: Which specialists to include (from route()).
                If None, includes all specialists.

        Returns:
            Executor ready to run blackboard-based analysis
        """
        if specialist_names is None:
            selected = self._specialists
        else:
            selected = {
                name: self._specialists[name]
                for name in specialist_names
                if name in self._specialists
            }
            if not selected:
                selected = {"coach": self._specialists["coach"]}

        scheduler = BlackboardScheduler(
            strategy="linear",
            max_iterations=1,
            execution_order=list(selected.keys()),
        )

        return BlackboardExecutor(
            specialists=selected,
            scheduler=scheduler,
        )

    # ── Info ─────────────────────────────────────────────────────────────

    def get_specialist(self, name: str) -> BaseAgent:
        """Return the specialist agent object by name."""
        return self._specialists.get(name, self._specialists["coach"])

    def list_agents(self) -> list[dict[str, str]]:
        """List all available specialists."""
        return [
            {"name": a.name, "description": a.description}
            for a in self._specialists.values()
        ]

    def get_model_name(self, specialist_name: str | None = None) -> str | None:
        """Return the model description used by specialists."""
        try:
            from fu7ur3pr00f.llm.fallback import get_model_with_fallback

            _, config = get_model_with_fallback(purpose="agent")
            return config.description
        except Exception:
            return None

    def reset(self) -> None:
        """No-op: kept for API compatibility. No compiled agents to clear."""
        logger.debug("Orchestrator.reset() called (no-op in blackboard-only mode)")


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
    """Reset the orchestrator singleton."""
    global _orchestrator
    with _orchestrator_lock:
        _orchestrator = None


def get_agent_config(
    thread_id: str = "main",
    user_id: str = "default",
) -> dict[str, Any]:
    """Build the LangGraph config dict for blackboard execution."""
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
