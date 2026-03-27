"""Turn classifier — categorizes incoming queries for context-aware routing.

Classifies queries into: factual, follow_up, steer, new_query, workflow_step.
Uses regex/keyword heuristics first (fast), falls back to LLM only when needed.
"""

import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

TurnType = Literal["factual", "follow_up", "steer", "new_query", "workflow_step"]

# Regex patterns for fast classification
_FACTUAL_PATTERN = re.compile(
    r"^(what|who|where|when|how many|how much|is|are|was|were)\s+(is|are|was|were|do|does|did|have|has|had)\s+my",
    re.IGNORECASE,
)

_FOLLOW_UP_KEYWORDS = {
    "that",
    "more",
    "tell me more",
    "go deeper",
    "elaborate",
    "expand",
    "also",
    "what about",
    "furthermore",
    "additionally",
    "explain",
    "clarify",
}

_STEER_KEYWORDS = {
    "focus on",
    "focus more",
    "instead",
    "actually",
    "skip",
    "ignore",
    "change",
    "different",
    "shift",
    "pivot",
}


def classify(
    query: str,
    conversation_history: list[dict] | None = None,
    active_goals: list[dict] | None = None,
) -> TurnType:
    """Classify the turn type using fast heuristics.

    Args:
        query: The user's input query
        conversation_history: Previous turns (if any)
        active_goals: Currently tracked goals

    Returns:
        Turn type: factual, follow_up, steer, new_query, or workflow_step
    """
    query_lower = query.lower()

    # Fast path 1: Factual questions
    if _FACTUAL_PATTERN.match(query):
        logger.debug("classify: %r → factual (regex match)", query[:60])
        return "factual"

    # Fast path 2: No history → must be new_query
    if not conversation_history or len(conversation_history) == 0:
        logger.debug("classify: %r → new_query (no history)", query[:60])
        return "new_query"

    # Fast path 3: Steering indicators
    if any(kw in query_lower for kw in _STEER_KEYWORDS):
        logger.debug("classify: %r → steer (keyword)", query[:60])
        return "steer"

    # Fast path 4: Follow-up indicators
    if any(kw in query_lower for kw in _FOLLOW_UP_KEYWORDS) or _is_follow_up_heuristic(
        query_lower
    ):
        logger.debug("classify: %r → follow_up (heuristic)", query[:60])
        return "follow_up"

    # Fast path 5: Workflow step
    if active_goals and _references_active_goal(query, active_goals):
        logger.debug("classify: %r → workflow_step", query[:60])
        return "workflow_step"

    # Default
    logger.debug("classify: %r → new_query (default)", query[:60])
    return "new_query"


def _is_follow_up_heuristic(query_lower: str) -> bool:
    """Check if query looks like a follow-up using simple heuristics."""
    # Starts with pronoun or question word that implies prior context
    pronouns = ("it", "that", "them", "those", "this", "these", "he", "she", "they")
    if any(query_lower.startswith(p) for p in pronouns):
        return True

    # Very short query after longer history (often a follow-up)
    if len(query_lower) < 20 and query_lower.count(" ") < 3:
        return True

    return False


def _references_active_goal(query: str, active_goals: list[dict]) -> bool:
    """Check if query references any active goal."""
    if not active_goals:
        return False

    query_lower = query.lower()
    for goal in active_goals:
        goal_desc = goal.get("description", "").lower()
        if goal_desc and goal_desc in query_lower:
            return True

    return False


__all__ = ["classify", "TurnType"]
