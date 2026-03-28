"""Blackboard executor — runs multi-specialist analysis using the blackboard pattern.

This is the orchestration engine that:
1. Creates initial blackboard state
2. Schedules specialists in order
3. Each specialist contributes to the blackboard
4. Loops until all specialists are satisfied or max iterations reached
5. Synthesizes final advice from all findings
"""

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from langgraph.errors import GraphInterrupt as _GraphInterrupt

from fu7ur3pr00f.agents.blackboard.blackboard import (
    CareerBlackboard,
    SpecialistFinding,
    make_initial_blackboard,
)
from fu7ur3pr00f.agents.blackboard.scheduler import BlackboardScheduler

logger = logging.getLogger(__name__)


class BlackboardExecutor:
    """Executes multi-specialist analysis using the blackboard pattern."""

    def __init__(
        self,
        specialists: dict[str, Any],
        scheduler: BlackboardScheduler | None = None,
    ):
        """Initialize the executor.

        Args:
            specialists: Dict mapping specialist names to agent objects
            scheduler: Optional custom scheduler (default: linear, 1 iteration)
        """
        self.specialists = specialists
        self.scheduler = scheduler or BlackboardScheduler(
            strategy="linear",
            max_iterations=1,
            execution_order=list(specialists.keys()),
        )

    def execute(
        self,
        query: str,
        user_profile: dict[str, Any],
        constraints: list[str] | None = None,
        on_specialist_start: Callable[[str], None] | None = None,
        on_specialist_complete: Callable[[str, SpecialistFinding], None] | None = None,
        on_tool_start: Callable[[str, str, dict], None] | None = None,
        on_tool_result: Callable[[str, str, str], None] | None = None,
        confirm_fn: Callable[[str, str], bool] | None = None,
    ) -> CareerBlackboard:
        """Execute blackboard-based multi-specialist analysis via LangGraph.

        Args:
            query: User's question (e.g., "5-year prediction")
            user_profile: User's career data
            constraints: Optional constraints for the analysis
            on_specialist_start: Called when specialist starts
            on_specialist_complete: Called when specialist completes
            on_tool_start: Called when tool is invoked
            on_tool_result: Called when tool completes
            confirm_fn: Optional callable for human-in-the-loop confirmations.
                Called with (question, details) -> bool when a tool raises
                GraphInterrupt. If None, interrupts propagate as exceptions.

        Returns:
            Final blackboard state with all findings
        """
        from fu7ur3pr00f.agents.blackboard.graph import build_blackboard_graph
        from fu7ur3pr00f.memory.checkpointer import get_checkpointer

        # Initialize blackboard
        initial = make_initial_blackboard(
            query=query,
            user_profile=user_profile,
            constraints=constraints,
            max_iterations=self.scheduler.max_iterations,
        )

        logger.warning(
            "Starting blackboard execution: query=%r, "
            "specialists=%s, max_iterations=%d",
            query[:80],
            list(self.specialists.keys()),
            self.scheduler.max_iterations,
        )

        execution_start = time.time()

        # Build and run the StateGraph
        checkpointer = get_checkpointer()
        graph = build_blackboard_graph(self.specialists, self.scheduler, checkpointer)

        config = {"configurable": {"thread_id": f"bb_{uuid.uuid4().hex[:12]}"}}

        # Stream updates from the graph with custom events for real-time progress
        # NOTE: In LangGraph 1.x, interrupt() is suppressed at root level and
        # yielded as a stream chunk {"__interrupt__": (...,)} in "updates" mode —
        # it is NEVER raised as a Python exception to the caller of graph.stream().
        final_state: CareerBlackboard = initial
        started_specialists: set[str] = set()

        stream_input: Any = initial
        while True:
            pending_interrupt: Any = None
            for chunk in graph.stream(
                stream_input, config, stream_mode=["updates", "custom"]
            ):
                mode, data = chunk  # Unpack tuple (always a 2-tuple)
                # Detect interrupt chunk — LangGraph yields it, never raises it
                if (
                    mode == "updates"
                    and isinstance(data, dict)
                    and "__interrupt__" in data
                ):
                    pending_interrupt = data["__interrupt__"]
                else:
                    self._process_stream_event(
                        mode,
                        data,
                        on_specialist_start,
                        on_specialist_complete,
                        on_tool_start,
                        on_tool_result,
                        started_specialists,
                    )

            if pending_interrupt is None:
                break  # Stream completed with no interrupt

            if confirm_fn is None:
                # No handler — raise so caller knows confirmation was required
                raise _GraphInterrupt(pending_interrupt)

            # Extract the first Interrupt object's value
            interrupts = (
                pending_interrupt
                if isinstance(pending_interrupt, (list, tuple))
                else (pending_interrupt,)
            )
            first = interrupts[0] if interrupts else None
            if first is None:
                break

            val = first.value if hasattr(first, "value") else first
            question = (
                val.get("question", "Confirm?") if isinstance(val, dict) else str(val)
            )
            details = val.get("details", "") if isinstance(val, dict) else ""
            approved = confirm_fn(question, details)
            from langgraph.types import Command

            stream_input = Command(resume=approved)

        # Get final state from graph (checkpointer is authoritative)
        snap = graph.get_state(config)
        if snap:
            final_state = dict(snap.values)  # type: ignore

        execution_time = time.time() - execution_start

        findings = final_state.get("findings", {})
        logger.warning(
            "Blackboard execution complete: "
            "%d specialists, %d iterations, %.2fs — "
            "findings_keys=%s, errors=%s",
            len(findings),
            final_state.get("iteration", 0) + 1,
            execution_time,
            list(findings.keys()),
            final_state.get("errors", []),
        )
        for spec_name, finding in findings.items():
            logger.warning(
                "  [%s] confidence=%.2f, " "reasoning=%r",
                spec_name,
                finding.get("confidence", 0),
                finding.get("reasoning", "")[:200],
            )

        return final_state

    def _process_stream_event(
        self,
        mode: str,
        data: Any,
        on_specialist_start: Callable[[str], None] | None,
        on_specialist_complete: Callable[[str, SpecialistFinding], None] | None,
        on_tool_start: Callable[[str, str, dict], None] | None,
        on_tool_result: Callable[[str, str, str], None] | None,
        started_specialists: set[str],
    ) -> None:
        """Process a single stream event from the blackboard graph."""
        if mode == "updates":
            for node_name, node_output in data.items():
                if not isinstance(node_output, dict):
                    continue
                if node_name in self.specialists:
                    finding = node_output.get("findings", {}).get(node_name)
                    if finding and on_specialist_complete:
                        on_specialist_complete(node_name, finding)
        elif mode == "custom" and isinstance(data, dict):
            event_type = data.get("type")
            specialist = data.get("specialist")
            if event_type == "specialist_start" and specialist in self.specialists:
                if specialist not in started_specialists:
                    started_specialists.add(specialist)
                    if on_specialist_start:
                        on_specialist_start(specialist)
            elif event_type == "tool_start" and on_tool_start:
                on_tool_start(
                    specialist or "", data.get("tool", ""), data.get("args", {})
                )
            elif event_type == "tool_result" and on_tool_result:
                on_tool_result(
                    specialist or "", data.get("tool", ""), data.get("result", "")
                )


__all__ = [
    "BlackboardExecutor",
]
