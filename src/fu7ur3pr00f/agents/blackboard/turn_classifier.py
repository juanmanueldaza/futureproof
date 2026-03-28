"""Turn classifier — categorizes incoming queries for context-aware routing.

Classifies queries into: factual, follow_up, steer, new_query, workflow_step.
Uses LLM-based classification via the classify_turn prompt.
"""

import logging
from typing import Literal

from fu7ur3pr00f.prompts import load_prompt

logger = logging.getLogger(__name__)

TurnType = Literal["factual", "follow_up", "steer", "new_query", "workflow_step"]
_VALID_TYPES: frozenset[str] = frozenset(
    {"factual", "follow_up", "steer", "new_query", "workflow_step"}
)


def classify(
    query: str,
    conversation_history: list[dict] | None = None,
    active_goals: list[dict] | None = None,
) -> TurnType:
    """Classify the turn type using LLM-based understanding.

    Args:
        query: The user's input query
        conversation_history: Previous turns (if any)
        active_goals: Currently tracked goals

    Returns:
        Turn type: factual, follow_up, steer, new_query, or workflow_step
    """
    from langchain_core.messages import HumanMessage

    from fu7ur3pr00f.llm.fallback import get_model_with_fallback

    # No history → always a new query, no LLM needed
    if not conversation_history:
        logger.debug("classify: %r → new_query (no history)", query[:60])
        return "new_query"

    # Build conversation summary (last 3 turns) — include agent responses so the
    # LLM can see e.g. "Agent asked 'Would you like to proceed?'" before "yes"
    recent = conversation_history[-3:]
    if recent:
        summary_lines = []
        for t in recent:
            summary_lines.append(f"- User: {t.get('query', '')[:80]}")
            narrative = t.get("narrative", "").strip()
            if narrative:
                # Trim to the first 120 chars to keep the prompt concise
                summary_lines.append(f"  Agent: {narrative[:120]}")
        conversation_summary = "\n".join(summary_lines)
    else:
        conversation_summary = "No prior turns."

    # Format active goals
    if active_goals:
        goals_text = ", ".join(
            g.get("description", "") for g in active_goals if g.get("description")
        )
        active_goals_str = goals_text or "None"
    else:
        active_goals_str = "None"

    prompt = load_prompt("classify_turn").format(
        conversation_summary=conversation_summary,
        query=query,
        active_goals=active_goals_str,
    )

    try:
        model, _ = get_model_with_fallback(purpose="summary", temperature=0.0)
        result = model.invoke([HumanMessage(content=prompt)])
        # First word of response is the turn type
        first_word = result.content.strip().split()[0].lower().rstrip(".")  # type: ignore
        if first_word in _VALID_TYPES:
            logger.debug("classify: %r → %s (llm)", query[:60], first_word)
            return first_word  # type: ignore
        logger.warning(
            "classify: LLM returned unknown type %r, defaulting to new_query",
            first_word,
        )
        return "new_query"
    except Exception:
        logger.warning(
            "classify: LLM failed for %r, defaulting to new_query",
            query[:60],
            exc_info=True,
        )
        return "new_query"


__all__ = ["classify", "TurnType"]
