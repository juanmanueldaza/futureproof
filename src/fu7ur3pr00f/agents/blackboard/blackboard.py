"""Career Blackboard — shared state for multi-specialist collaboration.

The blackboard is a TypedDict that stores:
- Original query and user profile
- Findings from each specialist
- Confidence scores for findings
- Audit trail (who modified what, when)
- Iteration count

All specialists read/write to this shared state, enabling collaborative analysis.
"""

import time
from typing import Annotated, Any

from typing_extensions import TypedDict

_MAX_ITERATIONS = 5  # Hard cap on multi-specialist iteration loops


def _merge_change_log(
    left: list[dict[str, Any]], right: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reducer for merging change logs in parallel execution.

    Safely concatenates logs from concurrent specialist nodes.
    Used by LangGraph for parallel Send-based specialist execution.
    """
    return left + right


class SpecialistFinding(TypedDict, total=False):
    """A specialist's contribution to the blackboard."""

    gaps: list[str]
    opportunities: list[str]
    timeline: str
    skills: list[str]
    projects: list[str]
    roles: list[str]
    salary: str
    portfolio_items: list[str]
    reasoning: str
    confidence: float
    iteration_contributed: int
    trade_offs: list[str]
    action_items: list[str]
    open_questions: list[str]


class CareerBlackboard(TypedDict, total=False):
    """Shared blackboard state for multi-specialist analysis.

    All specialists read/write to this dict during their contribution phase.
    Enables iterative refinement where specialists see previous findings.
    """

    # Input context
    query: str
    """Original user query (e.g., "5-year prediction")"""

    user_profile: dict[str, Any]
    """User's career profile (role, skills, goals, etc.)"""

    # Findings from each specialist (populated as they contribute)
    findings: dict[str, SpecialistFinding]
    """
    findings[specialist_name] = {
        "gaps": [...],
        "opportunities": [...],
        "confidence": 0.85,
        ...
    }
    """

    # Iteration control
    iteration: int
    """Current iteration number (0-based)"""

    max_iterations: int
    """Maximum iterations before stopping"""

    # Audit trail (with LangGraph reducer for safe parallel merging)
    change_log: Annotated[list[dict[str, Any]], _merge_change_log]
    """
    Log of all changes:
    [
        {
            "iteration": 0,
            "specialist": "coach",
            "timestamp": 1234567890.0,
            "keys_modified": ["gaps", "target_role"],
            "confidence": 0.85,
        },
        ...
    ]
    """

    # Constraints and metadata
    constraints: list[str]
    """Any constraints that should guide the analysis"""

    synthesis: dict[str, Any]
    """Final synthesized advice from all findings"""

    errors: list[dict[str, Any]]
    """Any errors encountered during execution"""

    # LangGraph state management
    current_specialist: str | None
    """Current specialist contributing to the blackboard (for graph routing)"""

    # Turn-scoped tool result cache (reset each executor.execute() call)
    _tool_cache: dict[str, str]
    """Cache for idempotent tool results within a turn (key: "tool:json_args")"""


def make_initial_blackboard(
    query: str,
    user_profile: dict[str, Any],
    constraints: list[str] | None = None,
    max_iterations: int = 1,
) -> CareerBlackboard:
    """Create an initial blackboard state for a multi-specialist analysis.

    Args:
        query: The user's question (e.g., "5-year prediction")
        user_profile: User's career data (role, skills, goals, etc.)
        constraints: Optional list of constraints for the analysis
        max_iterations: Maximum iterations before stopping (default 1, capped at 3)

    Returns:
        Initialized CareerBlackboard ready for specialist contributions
    """
    clamped = max(1, min(max_iterations, _MAX_ITERATIONS))
    return {
        "query": query,
        "user_profile": user_profile,
        "findings": {},
        "iteration": 0,
        "max_iterations": clamped,
        "change_log": [],
        "constraints": constraints or [],
        "synthesis": {},
        "errors": [],
        "current_specialist": None,
        "_tool_cache": {},
    }


def record_specialist_contribution(
    blackboard: CareerBlackboard,
    specialist_name: str,
    finding: SpecialistFinding,
    confidence: float = 0.80,
) -> None:
    """Record a specialist's contribution to the blackboard.

    Args:
        blackboard: The shared blackboard state
        specialist_name: Name of the specialist (e.g., "coach")
        finding: The specialist's findings
        confidence: Confidence score (0.0-1.0), clamped to valid range
    """
    # Clamp confidence to valid range
    clamped_confidence = max(0.0, min(float(confidence), 1.0))

    # Add to findings
    finding["confidence"] = clamped_confidence
    finding["iteration_contributed"] = blackboard.get("iteration", 0)
    findings = blackboard.get("findings", {})
    findings[specialist_name] = finding
    blackboard["findings"] = findings

    # Record in change log
    change_log = blackboard.get("change_log", [])
    change_log.append(
        {
            "iteration": blackboard.get("iteration", 0),
            "specialist": specialist_name,
            "timestamp": time.time(),
            "keys_modified": list(finding.keys()),
            "confidence": clamped_confidence,
        }
    )
    blackboard["change_log"] = change_log


def get_specialist_finding(
    blackboard: CareerBlackboard,
    specialist_name: str,
) -> SpecialistFinding | None:
    """Retrieve a specialist's findings from the blackboard.

    Args:
        blackboard: The shared blackboard state
        specialist_name: Name of the specialist to retrieve

    Returns:
        The specialist's findings, or None if not yet contributed
    """
    return blackboard.get("findings", {}).get(specialist_name)


def get_previous_findings(
    blackboard: CareerBlackboard,
    exclude_specialist: str | None = None,
) -> dict[str, SpecialistFinding]:
    """Get all findings from previous specialists (useful for context).

    Args:
        blackboard: The shared blackboard state
        exclude_specialist: Specialist to exclude from results

    Returns:
        Dict of {specialist_name: findings}
    """
    return {
        name: finding
        for name, finding in blackboard.get("findings", {}).items()
        if exclude_specialist is None or name != exclude_specialist
    }


__all__ = [
    "CareerBlackboard",
    "SpecialistFinding",
    "make_initial_blackboard",
    "record_specialist_contribution",
    "get_specialist_finding",
    "get_previous_findings",
]
