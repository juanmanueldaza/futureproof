"""Blackboard Scheduler — decides which specialist contributes next.

The scheduler implements the control logic for:
- Which specialist should contribute in the current iteration
- When to stop iterating (all specialists satisfied, or max iterations reached)
- How to handle specialist failures gracefully

Inspired by HEARSAY-II, the scheduler can use simple linear ordering (coach → learning
→ code → jobs → founder) or more sophisticated logic based on blackboard state.
"""

import logging

from fu7ur3pr00f.agents.blackboard.blackboard import CareerBlackboard

logger = logging.getLogger(__name__)


class BlackboardScheduler:
    """Controls specialist execution order and iteration stopping logic.

    Strategies:
    1. Linear: Each specialist runs in fixed order (coach → learning → ...)
    2. Conditional: Specialists only run if their area is relevant
    3. Iterative: Repeat until all specialists converge or max iterations reached

    Default is linear + iterative, suitable for "comprehensive query" flows.
    """

    # Order in which specialists should ideally contribute
    # Coach sets direction, then others build on it
    DEFAULT_ORDER = ["coach", "learning", "code", "jobs", "founder"]

    # Keywords that trigger specific specialists
    SPECIALIST_TRIGGERS = {
        "coach": {"promotion", "leadership", "career path", "growth", "next step"},
        "learning": {"learn", "skill", "training", "course", "improve"},
        "code": {"project", "portfolio", "github", "build", "technical"},
        "jobs": {"job", "opportunity", "role", "interview", "salary", "freelance"},
        "founder": {"startup", "saas", "founder", "business", "revenue"},
    }

    def __init__(
        self,
        strategy: str = "linear",
        max_iterations: int = 1,
        execution_order: list[str] | None = None,
    ):
        """Initialize the scheduler.

        Args:
            strategy: How to select next specialist. Options:
                - "linear": Fixed order, one pass
                - "linear_iterative": Linear order, repeat until max iterations
                - "conditional": Only activate specialists whose keywords match
                - "smart": Use blackboard state to decide what's needed next
            max_iterations: Maximum iterations before stopping (default 1)
            execution_order: Custom specialist order. If provided, overrides
                DEFAULT_ORDER. The router determines which specialists run.
        """
        self.strategy = strategy
        self.max_iterations = max_iterations
        if execution_order is not None:
            self._execution_order = execution_order
        else:
            self._execution_order = list(self.DEFAULT_ORDER)

    @property
    def execution_order(self) -> list[str]:
        """The specialist execution order for this scheduler."""
        return self._execution_order

    def get_next_specialist(
        self,
        blackboard: CareerBlackboard,
        current_specialist: str | None = None,
    ) -> str | None:
        """Determine which specialist should contribute next.

        Args:
            blackboard: Current shared blackboard state
            current_specialist: The specialist that just finished (or None for first)

        Returns:
            Name of next specialist to run, or None if done
        """
        if self.strategy == "linear":
            return self._get_next_linear(current_specialist)
        elif self.strategy == "linear_iterative":
            return self._get_next_linear_iterative(blackboard, current_specialist)
        elif self.strategy == "conditional":
            return self._get_next_conditional(blackboard, current_specialist)
        elif self.strategy == "smart":
            return self._get_next_smart(blackboard, current_specialist)
        elif self.strategy == "convergent":
            return self._get_next_convergent(blackboard, current_specialist)
        else:
            logger.warning("Unknown strategy %r, falling back to linear", self.strategy)
            return self._get_next_linear(current_specialist)

    def _get_next_linear(self, current_specialist: str | None = None) -> str | None:
        """Linear: Fixed order, one pass through all specialists."""
        if current_specialist is None:
            return self._execution_order[0]

        try:
            idx = self._execution_order.index(current_specialist)
            if idx + 1 < len(self._execution_order):
                return self._execution_order[idx + 1]
        except ValueError:
            pass

        return None

    def _get_next_linear_iterative(
        self,
        blackboard: CareerBlackboard,
        current_specialist: str | None = None,
    ) -> str | None:
        """Linear iterative: Fixed order, loop until max iterations."""
        iteration = blackboard.get("iteration", 0)
        max_iter = blackboard.get("max_iterations", self.max_iterations)

        # Stop if we've hit max iterations
        if iteration >= max_iter:
            logger.debug("Scheduler stopping: reached max iterations (%d)", max_iter)
            return None

        # First specialist is coach
        if current_specialist is None:
            return self._execution_order[0]

        # Try to move to next in order
        try:
            idx = self._execution_order.index(current_specialist)
            if idx + 1 < len(self._execution_order):
                return self._execution_order[idx + 1]
            else:
                # Completed one full iteration, loop back to coach for next iteration
                # (This enables iterative refinement)
                logger.debug(
                    "Scheduler completed iteration %d/%d, looping back to coach",
                    iteration + 1,
                    max_iter,
                )
                return self._execution_order[0]
        except ValueError:
            pass

        return None

    def _get_next_conditional(
        self,
        blackboard: CareerBlackboard,
        current_specialist: str | None = None,
    ) -> str | None:
        """Conditional: Only run specialists whose keywords match the query."""
        if current_specialist is None:
            # First specialist is always coach
            return self._execution_order[0]

        query = blackboard.get("query", "").lower()
        findings = blackboard.get("findings", {})

        # Try the next specialist in order
        try:
            idx = self._execution_order.index(current_specialist)
            for next_idx in range(idx + 1, len(self._execution_order)):
                next_specialist = self._execution_order[next_idx]
                triggers = self.SPECIALIST_TRIGGERS.get(next_specialist, set())

                # Check if query mentions this specialist's domain
                if any(kw in query for kw in triggers):
                    return next_specialist

                # Or if no previous findings yet (always run in linear order once)
                if next_specialist not in findings:
                    return next_specialist

        except ValueError:
            pass

        return None

    def _get_next_smart(
        self,
        blackboard: CareerBlackboard,
        current_specialist: str | None = None,
    ) -> str | None:
        """Smart: Use blackboard state to decide what's most needed next.

        For example:
        - If coach found gaps, route to learning to address them
        - If learning identified timeline, route to jobs for opportunities
        - If jobs found constraints, revisit code portfolio strategy
        """
        iteration = blackboard.get("iteration", 0)
        max_iter = blackboard.get("max_iterations", self.max_iterations)

        # Stop if max iterations reached
        if iteration >= max_iter:
            return None

        if current_specialist is None:
            # Always start with coach
            return "coach"

        findings = blackboard.get("findings", {})

        # Logic: each specialist enables the next
        if current_specialist == "coach":
            # Coach identifies gaps → learning addresses them
            coach_findings = findings.get("coach", {})
            if coach_findings.get("gaps"):
                return "learning"
            return None

        elif current_specialist == "learning":
            # Learning identifies skills → code validates with projects
            learning_findings = findings.get("learning", {})
            if learning_findings.get("skills") or learning_findings.get("projects"):
                return "code"
            return None

        elif current_specialist == "code":
            # Code validates portfolio → jobs finds opportunities
            code_findings = findings.get("code", {})
            if code_findings.get("portfolio_items"):
                return "jobs"
            return None

        elif current_specialist == "jobs":
            # Jobs identifies opportunities → founder stages the path
            jobs_findings = findings.get("jobs", {})
            if jobs_findings.get("opportunities") or jobs_findings.get("roles"):
                return "founder"
            return None

        elif current_specialist == "founder":
            # Founder completes the 5-year plan
            # Loop back to coach for iterative refinement if not at max iterations
            if iteration + 1 < max_iter:
                logger.debug(
                    "Scheduler starting iteration %d/%d",
                    iteration + 1,
                    max_iter,
                )
                return "coach"
            return None

        return None

    def should_continue(
        self,
        blackboard: CareerBlackboard,
        last_specialist: str | None = None,
    ) -> bool:
        """Check if the scheduler should continue (next specialist exists).

        Args:
            blackboard: Current shared blackboard state
            last_specialist: The specialist that just finished

        Returns:
            True if there's a next specialist to run, False if done
        """
        next_specialist = self.get_next_specialist(blackboard, last_specialist)
        return next_specialist is not None

    def get_execution_plan(self, blackboard: CareerBlackboard) -> list[str]:
        """Get the full execution plan (which specialists will run, in order).

        Useful for displaying progress: "Iteration 1/5: COACH analyzing..."

        Args:
            blackboard: Current shared blackboard state

        Returns:
            List of specialist names in execution order
        """
        plan = []
        current = None
        # Make a copy of the blackboard to simulate iteration advancement
        sim_blackboard: CareerBlackboard = {**blackboard}  # type: ignore

        for _ in range(self.max_iterations * len(self._execution_order)):
            next_specialist = self.get_next_specialist(sim_blackboard, current)
            if next_specialist is None:
                break
            plan.append(next_specialist)
            current = next_specialist

            # Simulate iteration increment when wrapping back to first specialist
            if next_specialist == self._execution_order[0] and current is not None:
                iter_val = sim_blackboard.get("iteration", 0)
                if isinstance(iter_val, int):
                    sim_blackboard["iteration"] = iter_val + 1

        return plan

    def _get_next_convergent(
        self,
        blackboard: CareerBlackboard,
        current_specialist: str | None = None,
    ) -> str | None:
        """Convergent: run until findings stabilize or max iterations reached.

        After each full pass, compare findings to previous iteration.
        If <20% new content, declare convergence.
        """
        iteration = blackboard.get("iteration", 0)
        max_iter = blackboard.get("max_iterations", self.max_iterations)

        # Stop if max iterations reached
        if iteration >= max_iter:
            logger.debug("Scheduler stopping: reached max iterations (%d)", max_iter)
            return None

        # First specialist is coach
        if current_specialist is None:
            return self._execution_order[0]

        # Try to move to next in order
        try:
            idx = self._execution_order.index(current_specialist)
            if idx + 1 < len(self._execution_order):
                return self._execution_order[idx + 1]
            else:
                # Completed one full iteration
                if iteration > 0 and self._has_converged(blackboard):
                    logger.debug(
                        "Scheduler stopping: findings converged at iteration %d",
                        iteration,
                    )
                    return None

                # Loop back for next iteration
                logger.debug(
                    "Scheduler checking iteration %d/%d, looping back to coach",
                    iteration + 1,
                    max_iter,
                )
                return self._execution_order[0]
        except ValueError:
            pass

        return None

    def _has_converged(self, blackboard: CareerBlackboard) -> bool:
        """Check if findings have stabilized between iterations.

        Compares the set of findings items (gaps+opportunities+skills+
        action_items) from current iteration vs previous. If <20% new items,
        convergence is declared.
        """
        findings = blackboard.get("findings", {})
        if not findings:
            return False

        # Collect all finding items
        all_items = set()
        for finding in findings.values():
            all_items.update(finding.get("gaps", []))
            all_items.update(finding.get("opportunities", []))
            all_items.update(finding.get("skills", []))
            all_items.update(finding.get("action_items", []))

        # If very few items, keep iterating
        if len(all_items) < 3:
            return False

        # If we're in iteration 1, can't compare to previous — keep going
        iteration = blackboard.get("iteration", 0)
        if iteration < 1:
            return False

        # NOTE: Full convergence check would require storing previous iteration
        # findings separately. For now, use a simple heuristic: if findings
        # dict has grown substantially, keep iterating.
        num_specialists_contributed = len(findings)
        if num_specialists_contributed < 2:
            return False

        # Convergence heuristic: if we have findings from most specialists
        # and iteration > 0, consider converged (will improve with full history)
        return num_specialists_contributed >= len(self._execution_order) - 1


__all__ = [
    "BlackboardScheduler",
]
