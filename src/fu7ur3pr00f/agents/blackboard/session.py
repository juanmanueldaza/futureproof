"""Session state for conversational blackboard — persistent across turns.

The session layer wraps per-turn blackboard executions, accumulating
findings, conversation history, and active goals across the entire
conversation thread.
"""

from typing import Annotated, Any

from typing_extensions import TypedDict

from fu7ur3pr00f.agents.blackboard.blackboard import SpecialistFinding


def _append_turns(left: list[dict], right: list[dict]) -> list[dict]:
    """Reducer for appending conversation turns (LangGraph pattern)."""
    return left + right


class ConversationTurn(TypedDict, total=False):
    """Record of one user turn and its analysis results."""

    query: str
    """The user's query for this turn"""

    specialist_names: list[str]
    """Which specialists ran in this turn"""

    narrative: str
    """The synthesis narrative returned to the user"""

    key_findings: list[str]
    """Distilled bullet points from this turn"""

    timestamp: float
    """When this turn completed (Unix timestamp)"""


class ActiveGoal(TypedDict, total=False):
    """A goal being worked on across multiple turns."""

    description: str
    """Goal description (e.g., 'Transition to Staff Engineer')"""

    steps: list[str]
    """Steps in the plan"""

    completed_steps: list[str]
    """Which steps are done"""

    status: str
    """'active', 'completed', or 'paused'"""


class SessionState(TypedDict, total=False):
    """Persistent state across the entire conversation session.

    This is the state of the outer LangGraph conversation graph.
    It persists via the SqliteSaver checkpointer (same thread_id).
    """

    # Conversation history (append-only via reducer)
    turns: Annotated[list[ConversationTurn], _append_turns]
    """List of completed turns, in order"""

    # Accumulated findings across all turns
    cumulative_findings: dict[str, SpecialistFinding]
    """Merged findings from all turns per specialist"""

    # Active workflow/goals for multi-turn sessions
    active_goals: list[ActiveGoal]
    """Goals being tracked across turns"""

    # Current turn's blackboard (ephemeral, overwritten)
    current_blackboard: dict[str, Any]
    """The blackboard state from the current turn"""

    # Current user query
    current_query: str
    """The query for the current turn"""

    # Routing decision for current turn
    routed_specialists: list[str]
    """Which specialists will/did run in current turn"""

    # Session-level user profile (loaded once, updated if changed)
    user_profile: dict[str, Any]
    """User's career profile"""

    # Proactive suggestions for follow-ups
    suggested_next: list[str]
    """Suggested follow-up questions/actions"""


def make_initial_session(user_profile: dict[str, Any]) -> SessionState:
    """Create an initial session state.

    Args:
        user_profile: User's career data

    Returns:
        Initialized SessionState ready for the first turn
    """
    return {
        "turns": [],
        "cumulative_findings": {},
        "active_goals": [],
        "current_blackboard": {},
        "current_query": "",
        "routed_specialists": [],
        "user_profile": user_profile,
        "suggested_next": [],
    }


def summarize_turn(blackboard: dict[str, Any]) -> ConversationTurn:
    """Distill a completed blackboard into a conversation turn record.

    Args:
        blackboard: Completed CareerBlackboard state

    Returns:
        CompactConversationTurn with key info
    """
    synthesis = blackboard.get("synthesis", {})
    findings = blackboard.get("findings", {})

    # Extract key findings as bullet points
    key_findings = []
    for specialist_name, finding in findings.items():
        reasoning = finding.get("reasoning", "")
        if reasoning:
            key_findings.append(f"{specialist_name}: {reasoning[:100]}")

    return {
        "query": blackboard.get("query", ""),
        "specialist_names": list(findings.keys()),
        "narrative": synthesis.get("narrative", ""),
        "key_findings": key_findings,
        "timestamp": __import__("time").time(),
    }


def format_cumulative_context(
    turns: list[ConversationTurn], cumulative_findings: dict
) -> str:
    """Format cross-turn context for specialist consumption.

    Args:
        turns: Conversation history
        cumulative_findings: Accumulated findings per specialist

    Returns:
        Formatted context string (max 2000 chars), tagged with PRIOR_TURNS:
    """
    if not turns:
        return ""

    parts = ["PRIOR_TURNS:"]
    parts.append("Previous conversation turns:")

    for i, turn in enumerate(turns[-3:], 1):  # Last 3 turns
        parts.append(f"  Turn {i}: {turn.get('query', '')[:60]}")
        for finding in turn.get("key_findings", [])[:2]:
            parts.append(f"    - {finding[:80]}")

    context = "\n".join(parts)
    return context[:2000]


__all__ = [
    "ConversationTurn",
    "ActiveGoal",
    "SessionState",
    "make_initial_session",
    "summarize_turn",
    "format_cumulative_context",
]
