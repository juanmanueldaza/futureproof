"""Outer conversation graph — persistent session-scoped orchestration.

Wraps the per-turn blackboard graph, managing conversation history,
cumulative findings, and proactive suggestions across turns.
"""

import logging
from typing import TYPE_CHECKING, Any

from langgraph.graph import StateGraph

if TYPE_CHECKING:
    from fu7ur3pr00f.agents.blackboard.session import SessionState
else:
    SessionState = dict  # type: ignore

logger = logging.getLogger(__name__)


def build_conversation_graph():  # type: ignore
    """Build the outer conversation StateGraph.

    This graph manages session-level state (turns, cumulative findings,
    active goals) and orchestrates per-turn blackboard executions.
    """
    # Import here to avoid circular dependency
    from fu7ur3pr00f.agents.blackboard.session import (
        format_cumulative_context,
        summarize_turn,
    )
    from fu7ur3pr00f.agents.blackboard.turn_classifier import classify
    from fu7ur3pr00f.agents.specialists.orchestrator import get_orchestrator

    graph = StateGraph(dict)  # SessionState is dict at runtime

    # ── Nodes ────────────────────────────────────────────────────────────

    def classify_turn_node(state: dict[str, Any]) -> dict[str, Any]:
        """Classify the current query's turn type."""
        query = state.get("current_query", "")
        turns = state.get("turns", [])
        active_goals = state.get("active_goals", [])

        turn_type = classify(query, turns, active_goals)
        logger.debug("Turn %d: classified as %r", len(turns) + 1, turn_type)

        return {"turn_type": turn_type}

    def route_turn_node(state: SessionState) -> dict[str, Any]:
        """Route the current query to appropriate specialists."""
        from fu7ur3pr00f.agents.blackboard.session import ConversationTurn

        query = state.get("current_query", "")
        turn_type = state.get("turn_type", "new_query")
        turns = state.get("turns", [])
        orchestrator = get_orchestrator()

        # Build conversation history for routing
        conversation_history: list[ConversationTurn] = turns[-3:] if turns else []

        # Route based on turn type
        if turn_type == "factual":
            routed = ["coach"]  # Fast path for factual
        elif turn_type == "follow_up" and turns:
            # Reuse previous turn's specialists
            routed = turns[-1].get("specialist_names", ["coach"])
        else:
            # new_query, steer, workflow_step → standard routing
            routed = orchestrator.route(query, conversation_history, turn_type)

        logger.debug("Routed to: %s", routed)
        return {"routed_specialists": routed}

    def execute_inner_node(state: SessionState) -> dict[str, Any]:
        """Execute the inner blackboard graph for this turn."""
        query = state.get("current_query", "")
        user_profile = state.get("user_profile", {})
        routed = state.get("routed_specialists", ["coach"])
        cumulative = state.get("cumulative_findings", {})
        turn_type = state.get("turn_type", "new_query")

        # Prepare constraints with cross-turn context
        constraints = []
        if turn_type in ("follow_up", "steer") and cumulative:
            turns = state.get("turns", [])
            context = format_cumulative_context(turns, cumulative)
            if context:
                constraints.append(context)

        # Get executor and run inner graph
        orchestrator = get_orchestrator()
        executor = orchestrator.get_blackboard_executor(routed)

        try:
            blackboard = executor.execute(
                query=query,
                user_profile=user_profile,
                constraints=constraints,
                on_specialist_start=None,  # Can add callbacks later
                on_specialist_complete=None,
                on_tool_start=None,
                on_tool_result=None,
                confirm_fn=None,
            )
            logger.debug("Inner blackboard completed")
        except Exception as e:
            logger.error("Inner blackboard failed: %s", e)
            blackboard = {
                "query": query,
                "findings": {},
                "synthesis": {"narrative": f"Analysis failed: {e}"},
                "errors": [{"error": str(e)}],
            }

        return {"current_blackboard": blackboard}

    def accumulate_node(state: SessionState) -> dict[str, Any]:
        """Merge current turn's findings into cumulative state."""
        blackboard = state.get("current_blackboard", {})
        cumulative = state.get("cumulative_findings", {})
        turns = state.get("turns", [])

        # Merge findings (latest per specialist overwrites)
        new_findings = blackboard.get("findings", {})
        for specialist, finding in new_findings.items():
            cumulative[specialist] = finding

        # Summarize and append turn
        turn_record = summarize_turn(blackboard)
        turn_record["query"] = state.get("current_query", "")
        turns.append(turn_record)

        logger.debug("Accumulated turn %d", len(turns))
        return {"cumulative_findings": cumulative, "turns": turns}

    def synthesize_turn_node(state: SessionState) -> dict[str, Any]:
        """Synthesize findings with cross-turn awareness."""
        blackboard = state.get("current_blackboard", {})
        synthesis = blackboard.get("synthesis", {})

        # If synthesis already done by inner graph, keep it
        if synthesis.get("narrative"):
            return {"synthesis": synthesis}

        # Fallback: synthesize from findings
        findings = blackboard.get("findings", {})
        if len(findings) == 1:
            # Single specialist: pass through reasoning
            specialist_name = list(findings.keys())[0]
            narrative = findings[specialist_name].get("reasoning", "No findings")
            synthesis["narrative"] = narrative
        else:
            # Multi-specialist: would need LLM synthesis
            # For now, concatenate
            parts = []
            for _name, finding in findings.items():
                reasoning = finding.get("reasoning", "")
                if reasoning:
                    parts.append(reasoning)
            synthesis["narrative"] = "\n\n".join(parts) if parts else "No findings"

        return {"synthesis": synthesis}

    def suggest_next_node(state: SessionState) -> dict[str, Any]:
        """Generate proactive suggestions for follow-ups."""
        turn_type = state.get("turn_type", "new_query")
        blackboard = state.get("current_blackboard", {})

        # Skip suggestions for factual queries
        if turn_type == "factual":
            return {"suggested_next": []}

        findings = blackboard.get("findings", {})
        if not findings:
            return {"suggested_next": []}

        # Extract gaps, action_items, open_questions
        gaps = []
        action_items = []
        open_questions = []
        for finding in findings.values():
            gaps.extend(finding.get("gaps", [])[:2])
            action_items.extend(finding.get("action_items", [])[:2])
            open_questions.extend(finding.get("open_questions", [])[:1])

        # For now, simple heuristic suggestions (LLM integration later)
        suggestions = []
        if action_items:
            suggestions.append(f"Start with: {action_items[0]}")
        if gaps:
            suggestions.append(f"Address the gap: {gaps[0]}")
        if open_questions:
            suggestions.append(f"Explore: {open_questions[0]}")

        return {"suggested_next": suggestions[:3]}

    # ── Graph construction ────────────────────────────────────────────────

    graph.add_node("classify_turn", classify_turn_node)
    graph.add_node("route_turn", route_turn_node)
    graph.add_node("execute_inner", execute_inner_node)
    graph.add_node("accumulate", accumulate_node)
    graph.add_node("synthesize_turn", synthesize_turn_node)
    graph.add_node("suggest_next", suggest_next_node)

    # Edges
    graph.add_edge("classify_turn", "route_turn")
    graph.add_edge("route_turn", "execute_inner")
    graph.add_edge("execute_inner", "accumulate")
    graph.add_edge("accumulate", "synthesize_turn")
    graph.add_edge("synthesize_turn", "suggest_next")
    graph.add_edge("suggest_next", "END")

    graph.set_entry_point("classify_turn")

    return graph.compile()


__all__ = ["build_conversation_graph"]
