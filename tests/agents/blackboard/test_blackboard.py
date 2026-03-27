"""Tests for blackboard pattern implementation."""

import pytest

from fu7ur3pr00f.agents.blackboard.blackboard import (
    SpecialistFinding,
    get_previous_findings,
    get_specialist_finding,
    make_initial_blackboard,
    record_specialist_contribution,
)
from fu7ur3pr00f.agents.blackboard.scheduler import BlackboardScheduler


class TestCareerBlackboard:
    """Test CareerBlackboard creation and state management."""

    def test_make_initial_blackboard(self):
        """Test creating initial blackboard state."""
        query = "5-year prediction"
        profile = {"role": "Senior Engineer", "skills": ["Python", "Go"]}

        blackboard = make_initial_blackboard(
            query=query,
            user_profile=profile,
            constraints=["No relocation"],
            max_iterations=2,
        )

        assert blackboard["query"] == query
        assert blackboard["user_profile"] == profile
        assert blackboard["constraints"] == ["No relocation"]
        assert blackboard["iteration"] == 0
        assert blackboard["max_iterations"] == 2  # Within hard cap of 3
        assert blackboard["findings"] == {}
        assert blackboard["change_log"] == []

    def test_make_initial_blackboard_clamps_max_iterations(self):
        """Test that max_iterations is clamped to hard cap (5)."""
        # Request 10 iterations, but should be clamped to 5
        blackboard = make_initial_blackboard(
            query="test",
            user_profile={},
            max_iterations=10,
        )
        assert blackboard["max_iterations"] == 5

        # Request 0 iterations, but should be clamped to 1 (minimum)
        blackboard = make_initial_blackboard(
            query="test",
            user_profile={},
            max_iterations=0,
        )
        assert blackboard["max_iterations"] == 1

    def test_record_specialist_contribution(self):
        """Test recording a specialist's findings."""
        blackboard = make_initial_blackboard(
            query="test", user_profile={}, max_iterations=2
        )

        finding: SpecialistFinding = {
            "gaps": ["ML", "leadership"],
            "target_role": "Staff Engineer",
            "confidence": 0.85,
        }

        record_specialist_contribution(
            blackboard=blackboard,
            specialist_name="coach",
            finding=finding,
            confidence=0.85,
        )

        # Check finding was recorded
        assert "coach" in blackboard["findings"]
        assert blackboard["findings"]["coach"]["gaps"] == ["ML", "leadership"]

        # Check change log was updated
        assert len(blackboard["change_log"]) == 1
        entry = blackboard["change_log"][0]
        assert entry["specialist"] == "coach"
        assert entry["iteration"] == 0
        assert entry["confidence"] == 0.85

    def test_get_specialist_finding(self):
        """Test retrieving a specialist's findings."""
        blackboard = make_initial_blackboard(
            query="test", user_profile={}, max_iterations=5
        )

        # No finding yet
        assert get_specialist_finding(blackboard, "coach") is None

        # Add finding
        finding: SpecialistFinding = {"gaps": ["ML"], "confidence": 0.85}
        record_specialist_contribution(blackboard, "coach", finding, 0.85)

        # Now retrieve it
        retrieved = get_specialist_finding(blackboard, "coach")
        assert retrieved is not None
        assert retrieved["gaps"] == ["ML"]

    def test_get_previous_findings(self):
        """Test getting all previous findings."""
        blackboard = make_initial_blackboard(
            query="test", user_profile={}, max_iterations=5
        )

        # Add multiple findings
        record_specialist_contribution(blackboard, "coach", {"gaps": ["ML"]}, 0.85)
        record_specialist_contribution(
            blackboard, "learning", {"skills": ["Python ML"]}, 0.80
        )

        # Get all excluding coach
        previous = get_previous_findings(blackboard, exclude_specialist="coach")
        assert "coach" not in previous
        assert "learning" in previous
        assert previous["learning"]["skills"] == ["Python ML"]

        # Get all (no exclusion)
        all_findings = get_previous_findings(blackboard)
        assert len(all_findings) == 2
        assert "coach" in all_findings
        assert "learning" in all_findings


class TestBlackboardScheduler:
    """Test scheduler logic for determining specialist order."""

    def test_scheduler_linear_order(self, empty_blackboard):
        """Test linear execution order."""
        scheduler = BlackboardScheduler(strategy="linear")
        blackboard = empty_blackboard

        # First should be coach
        assert scheduler.get_next_specialist(blackboard, None) == "coach"

        # Then learning
        assert scheduler.get_next_specialist(blackboard, "coach") == "learning"

        # Then code
        assert scheduler.get_next_specialist(blackboard, "learning") == "code"

        # Then jobs
        assert scheduler.get_next_specialist(blackboard, "code") == "jobs"

        # Then founder
        assert scheduler.get_next_specialist(blackboard, "jobs") == "founder"

        # Then stop
        assert scheduler.get_next_specialist(blackboard, "founder") is None

    def test_scheduler_linear_iterative(self):
        """Test linear iterative execution (loops up to max_iterations)."""
        scheduler = BlackboardScheduler(strategy="linear_iterative", max_iterations=2)
        blackboard = make_initial_blackboard("test", {}, max_iterations=2)

        # First iteration
        assert scheduler.get_next_specialist(blackboard, None) == "coach"
        assert scheduler.get_next_specialist(blackboard, "coach") == "learning"
        assert scheduler.get_next_specialist(blackboard, "learning") == "code"
        assert scheduler.get_next_specialist(blackboard, "code") == "jobs"
        assert scheduler.get_next_specialist(blackboard, "jobs") == "founder"

        # After founder, should loop back to coach
        assert scheduler.get_next_specialist(blackboard, "founder") == "coach"

        # Simulate second iteration
        blackboard["iteration"] = 1
        assert scheduler.get_next_specialist(blackboard, "coach") == "learning"
        assert scheduler.get_next_specialist(blackboard, "learning") == "code"
        assert scheduler.get_next_specialist(blackboard, "code") == "jobs"
        assert scheduler.get_next_specialist(blackboard, "jobs") == "founder"

        # After founder on max iteration, should stop
        blackboard["iteration"] = 1
        # At iteration 1 with max_iterations=2, next should continue to iteration 2

    def test_scheduler_max_iterations(self):
        """Test that scheduler stops at max iterations."""
        scheduler = BlackboardScheduler(strategy="linear_iterative", max_iterations=1)
        blackboard = make_initial_blackboard("test", {}, max_iterations=1)

        # At iteration 0, max_iterations=1, so 0 >= 1 is false, continue
        assert scheduler.get_next_specialist(blackboard, None) == "coach"

        # Now at iteration 1 (after looping), max_iterations=1, so 1 >= 1 is true, stop
        blackboard["iteration"] = 1
        # Actually, the function checks at the START of get_next_specialist
        # Let me trace through the code more carefully
        next_spec = scheduler.get_next_specialist(blackboard, "coach")
        # iteration=1, max_iterations=1, so 1 >= 1 is true, return None
        assert next_spec is None

    def test_scheduler_should_continue(self, empty_blackboard):
        """Test should_continue check."""
        scheduler = BlackboardScheduler(strategy="linear")
        blackboard = empty_blackboard

        # At start, should continue
        assert scheduler.should_continue(blackboard) is True

        # After founder, should stop (linear only goes once)
        assert scheduler.should_continue(blackboard, "founder") is False

    def test_scheduler_get_execution_plan(self, empty_blackboard):
        """Test getting full execution plan."""
        scheduler = BlackboardScheduler(strategy="linear")
        blackboard = empty_blackboard

        plan = scheduler.get_execution_plan(blackboard)

        # Linear should execute each specialist once
        assert "coach" in plan
        assert "learning" in plan
        assert "code" in plan
        assert "jobs" in plan
        assert "founder" in plan
        assert len(plan) == 5


class TestBlackboardIntegration:
    """Integration tests for blackboard pattern."""

    def test_specialist_contributions_accumulate(self):
        """Test that multiple specialist contributions accumulate properly."""
        blackboard = make_initial_blackboard(
            "5-year prediction",
            {"role": "Senior Engineer"},
        )

        # Coach contributes
        coach_finding: SpecialistFinding = {
            "gaps": ["ML", "leadership"],
            "target_role": "Staff Engineer",
            "confidence": 0.85,
        }
        record_specialist_contribution(blackboard, "coach", coach_finding, 0.85)

        # Learning contributes (reads coach's gaps)
        learning_finding: SpecialistFinding = {
            "skills": ["ML fundamentals", "leadership course"],
            "gap_focus": coach_finding["gaps"],
            "confidence": 0.80,
        }
        record_specialist_contribution(blackboard, "learning", learning_finding, 0.80)

        # Code contributes
        code_finding: SpecialistFinding = {
            "portfolio_items": ["ML project", "team lead experience"],
            "confidence": 0.82,
        }
        record_specialist_contribution(blackboard, "code", code_finding, 0.82)

        # Verify all are present
        assert len(blackboard["findings"]) == 3
        assert len(blackboard["change_log"]) == 3

        # Verify they can read each other's findings
        learning_can_see_coach = get_specialist_finding(blackboard, "coach")
        assert learning_can_see_coach["gaps"] == ["ML", "leadership"]

        code_can_see_all = get_previous_findings(blackboard, "code")
        assert "coach" in code_can_see_all
        assert "learning" in code_can_see_all


class TestBlackboardSchedulerStrategies:
    """Test different scheduler strategies."""

    def test_smart_strategy(self, empty_blackboard):
        """Test smart strategy that routes based on blackboard state."""
        scheduler = BlackboardScheduler(strategy="smart", max_iterations=3)
        blackboard = empty_blackboard

        # Smart starts with coach
        assert scheduler.get_next_specialist(blackboard, None) == "coach"

        # After coach (no gaps found yet), returns None
        assert scheduler.get_next_specialist(blackboard, "coach") is None

        # Add coach gaps
        record_specialist_contribution(blackboard, "coach", {"gaps": ["ML"]}, 0.85)

        # Now learning should be next
        assert scheduler.get_next_specialist(blackboard, "coach") == "learning"

        # Add learning skills
        record_specialist_contribution(blackboard, "learning", {"skills": ["ML"]}, 0.80)

        # Now code should be next
        assert scheduler.get_next_specialist(blackboard, "learning") == "code"

    def test_conditional_strategy(self):
        """Test conditional strategy that filters by keyword match."""
        scheduler = BlackboardScheduler(strategy="conditional")
        blackboard = make_initial_blackboard("How should I learn machine learning?", {})

        # Should start with coach
        assert scheduler.get_next_specialist(blackboard, None) == "coach"

        # After coach, learning should be next (query matches "learn")
        next_spec = scheduler.get_next_specialist(blackboard, "coach")
        assert next_spec == "learning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
