"""Action to result key mapping.

Centralizes the mapping between action names and state result keys.
Eliminates duplication between orchestrator nodes and service layer.
"""

# Centralized mapping of actions to their result keys
ACTION_RESULT_KEYS: dict[str, str] = {
    # Career analysis actions
    "analyze_goals": "goals",
    "analyze_reality": "reality",
    "analyze_gaps": "gaps",
    "analyze_full": "analysis",
    # Market analysis actions
    "analyze_market_fit": "market_fit",
    "analyze_skill_gaps": "skill_gaps",
    "analyze_trends": "trending_skills",
    "analyze_market": "analysis",
    "analyze_skills": "skill_gaps",
}


def get_result_key(action: str, default: str = "analysis") -> str:
    """Get the result key for an action.

    Args:
        action: The action being performed (e.g., "analyze_goals")
        default: Default key if action not found in mapping

    Returns:
        Result key for storing LLM response in state
    """
    return ACTION_RESULT_KEYS.get(action, default)
