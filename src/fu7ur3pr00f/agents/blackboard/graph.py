"""LangGraph StateGraph for blackboard-based multi-specialist orchestration.

Graph topology:
    START → [specialist nodes] → route_fn
                                   ├→ next specialist
                                   ├→ increment_iteration → first specialist
                                   └→ synthesize → END

Each specialist node passes stream_writer into contribute() for real-time
tool progress events. The synthesis node generates a coherent narrative
via LLM for multi-specialist results.
"""

import logging
import time
from typing import Any

from langgraph.errors import GraphInterrupt as _GraphInterrupt
from langgraph.graph import StateGraph

from fu7ur3pr00f.agents.blackboard.blackboard import CareerBlackboard
from fu7ur3pr00f.agents.blackboard.scheduler import BlackboardScheduler
from fu7ur3pr00f.prompts import load_prompt
from fu7ur3pr00f.utils.security import sanitize_error, sanitize_for_prompt

logger = logging.getLogger(__name__)


def _make_specialist_node(specialist: Any):
    """Factory to create a specialist node function."""

    def specialist_node(state: CareerBlackboard) -> dict[str, Any]:
        """Execute specialist contribution with real tools via stream_writer."""
        specialist_name = specialist.name
        logger.debug("Specialist %r contributing...", specialist_name)

        # Get stream writer for real-time progress (optional, safe if None)
        try:
            from langgraph.config import get_stream_writer

            stream_writer = get_stream_writer()
        except (ImportError, RuntimeError):
            logger.warning(
                "Stream writer unavailable for %s",
                specialist_name,
                exc_info=True,
            )
            stream_writer = None

        # Emit start event
        if stream_writer:
            stream_writer(
                {
                    "type": "specialist_start",
                    "specialist": specialist_name,
                    "iteration": state.get("iteration", 0),
                    "timestamp": time.time(),
                }
            )

        try:
            contrib_start = time.time()
            # Pass stream_writer so tool events surface in real time
            finding = specialist.contribute(state, stream_writer=stream_writer)
            contrib_time = time.time() - contrib_start

            finding["confidence"] = finding.get("confidence", 0.75)
            finding["iteration_contributed"] = state.get("iteration", 0)

            change_entry = {
                "iteration": state.get("iteration", 0),
                "specialist": specialist_name,
                "timestamp": time.time(),
                "keys_modified": list(finding.keys()),
                "confidence": finding["confidence"],
            }

            logger.info(
                "Specialist %r contributed in %.2fs (confidence=%.2f)",
                specialist_name,
                contrib_time,
                finding["confidence"],
            )

            if stream_writer:
                stream_writer(
                    {
                        "type": "specialist_complete",
                        "specialist": specialist_name,
                        "elapsed": contrib_time,
                        "confidence": finding["confidence"],
                        "reasoning": finding.get("reasoning", ""),
                    }
                )

            return {
                "findings": state.get("findings", {}) | {specialist_name: finding},
                "change_log": [change_entry],
                "current_specialist": specialist_name,
                "_tool_cache": state.get("_tool_cache", {}),
            }

        except _GraphInterrupt:
            raise  # Let LangGraph handle the interrupt for human-in-the-loop
        except Exception as e:
            logger.exception("Error in specialist %r", specialist_name)
            sanitized_error = sanitize_error(str(e))

            if stream_writer:
                stream_writer(
                    {
                        "type": "specialist_error",
                        "specialist": specialist_name,
                        "error": sanitized_error,
                    }
                )

            return {
                "errors": [
                    *state.get("errors", []),
                    {
                        "specialist": specialist_name,
                        "error": sanitized_error,
                        "iteration": state.get("iteration", 0),
                    },
                ],
                "current_specialist": specialist_name,
            }

    return specialist_node


def _make_route_fn(scheduler: BlackboardScheduler):
    """Factory to create the routing function for conditional edges."""

    def route_fn(state: CareerBlackboard) -> str:
        """Determine next node based on scheduler."""
        current = state.get("current_specialist")
        next_specialist = scheduler.get_next_specialist(state, current)

        if not next_specialist:
            return "synthesize"

        if current is not None and next_specialist == scheduler.execution_order[0]:
            return "increment_iteration"

        return next_specialist

    return route_fn


def _increment_iteration_node(state: CareerBlackboard) -> dict[str, Any]:
    """Increment iteration counter."""
    new_iteration = state.get("iteration", 0) + 1
    logger.debug("Iteration %d starting", new_iteration)
    return {"iteration": new_iteration}


def _synthesize_node(state: CareerBlackboard) -> dict[str, Any]:
    """Synthesize specialist findings into a coherent narrative.

    - 1 specialist: pass through its reasoning directly (no extra LLM call)
    - 2+ specialists: call synthesis model to produce an integrated narrative
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from fu7ur3pr00f.llm.fallback import get_model_with_fallback

    findings = state.get("findings", {})
    query = state.get("query", "")
    specialists_ran = list(findings.keys())

    synthesis: dict[str, Any] = {
        "query": query,
        "specialists_contributed": specialists_ran,
        "num_iterations": state.get("iteration", 0) + 1,
        "all_findings": findings,
    }

    # Single specialist — use its reasoning directly, no extra LLM call
    if len(findings) == 1:
        only_finding = next(iter(findings.values()))
        reasoning = only_finding.get("reasoning", "") or ""
        if not reasoning.strip():
            # Fallback: build narrative from structured fields
            parts = []
            for field in (
                "gaps",
                "strengths",
                "opportunities",
                "skills",
                "action_items",
            ):
                raw = only_finding.get(field, [])  # type: ignore[attr-defined]
                if raw:
                    label = field.replace("_", " ").title()
                    vals: list[object] = list(raw)  # type: ignore[call-overload]
                    joined = ", ".join(str(i) for i in vals)
                    parts.append(f"**{label}:** {joined}")
            reasoning = "\n".join(parts) if parts else "Analysis complete."
        synthesis["narrative"] = sanitize_for_prompt(reasoning)
        logger.info("Synthesis (single specialist): pass-through")
        return {"synthesis": synthesis}

    # Multi-specialist — synthesize via LLM
    # Include all specialist findings (structured data + reasoning)
    findings_text_parts = []
    for specialist_name, finding in findings.items():
        parts = [f"### {specialist_name.upper()}"]

        # Add reasoning first (high-level summary)
        reasoning = finding.get("reasoning")  # type: ignore[assignment]
        if reasoning:
            parts.append(f"**Summary:** {sanitize_for_prompt(reasoning)}")

        # Add structured details from each specialist
        detail_fields = [
            ("gaps", "Key gaps"),
            ("strengths", "Strengths"),
            ("skills", "Skills to develop"),
            ("target_role", "Target role"),
            ("timeline", "Timeline"),
            ("opportunities", "Opportunities"),
            ("salary", "Salary insights"),
            ("portfolio_items", "Portfolio highlights"),
            ("projects", "Notable projects"),
            ("recommendations", "Recommendations"),
        ]

        for field, label in detail_fields:
            value = finding.get(field)
            if value:
                if isinstance(value, (list, tuple)):
                    items = ", ".join(sanitize_for_prompt(str(v)) for v in value)
                    parts.append(f"**{label}:** {items}")
                elif isinstance(value, dict):
                    items = "; ".join(
                        f"{k}: {sanitize_for_prompt(str(v))}" for k, v in value.items()
                    )
                    parts.append(f"**{label}:** {items}")
                else:
                    parts.append(f"**{label}:** {sanitize_for_prompt(str(value))}")

        if len(parts) > 1:  # Only add if there's more than just the header
            findings_text_parts.append("\n".join(parts))

    findings_text = (
        "\n\n".join(findings_text_parts)
        if findings_text_parts
        else "No specialist findings available."
    )

    try:
        model, _ = get_model_with_fallback(purpose="synthesis")
        result = model.invoke(
            [
                SystemMessage(content=load_prompt("blackboard_synthesis_system")),
                HumanMessage(
                    content=load_prompt("blackboard_synthesis_human").format(
                        query=query,
                        findings_text=findings_text,
                    )
                ),
            ]
        )
        synthesis["narrative"] = str(getattr(result, "content", result))
        logger.info("Synthesis complete: %d specialists → narrative", len(findings))

    except Exception as e:
        logger.error(
            "Synthesis LLM call failed: %s — " "findings_text=%r",
            e,
            findings_text[:500],
            exc_info=True,
        )
        # Fall back to concatenated reasoning
        synthesis["narrative"] = (
            "\n\n".join(
                f"**{name.upper()}:** " f"{sanitize_for_prompt(f.get('reasoning', ''))}"
                for name, f in findings.items()
                if f.get("reasoning")
            )
            or "Analysis complete."
        )

    return {"synthesis": synthesis}


def build_blackboard_graph(
    specialists: dict[str, Any],
    scheduler: BlackboardScheduler | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Build a compiled LangGraph StateGraph for blackboard orchestration.

    Args:
        specialists: Dict mapping specialist names to agent objects (already filtered
            to only the routed subset)
        scheduler: Optional custom scheduler (default: linear, 1 iteration)
        checkpointer: Optional SqliteSaver checkpointer for persistence

    Returns:
        Compiled CompiledStateGraph ready for .stream() / .invoke()
    """
    if scheduler is None:
        scheduler = BlackboardScheduler(
            strategy="linear",
            max_iterations=1,
            execution_order=list(specialists.keys()),
        )

    graph = StateGraph(CareerBlackboard)

    for spec_name, specialist in specialists.items():
        graph.add_node(spec_name, _make_specialist_node(specialist))

    graph.add_node("increment_iteration", _increment_iteration_node)
    graph.add_node("synthesize", _synthesize_node)

    route_fn = _make_route_fn(scheduler)
    for spec_name in specialists:
        graph.add_conditional_edges(
            spec_name,
            route_fn,
            {
                "synthesize": "synthesize",
                "increment_iteration": "increment_iteration",
                **{name: name for name in specialists},
            },
        )

    first_specialist = scheduler.execution_order[0]
    graph.add_edge("increment_iteration", first_specialist)
    graph.add_edge("__start__", first_specialist)

    compiled = graph.compile(checkpointer=checkpointer)
    logger.info(
        "Built blackboard graph: %d specialists, order=%s",
        len(specialists),
        scheduler.execution_order,
    )
    return compiled


__all__ = [
    "build_blackboard_graph",
]
