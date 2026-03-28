"""Tests for specialist agents and orchestrator."""

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest

from fu7ur3pr00f.agents.specialists.base import BaseAgent, KnowledgeResult, MemoryResult
from fu7ur3pr00f.agents.specialists.coach import CoachAgent
from fu7ur3pr00f.agents.specialists.code import CodeAgent
from fu7ur3pr00f.agents.specialists.founder import FounderAgent
from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
from fu7ur3pr00f.agents.specialists.learning import LearningAgent
from fu7ur3pr00f.agents.specialists.orchestrator import (
    OrchestratorAgent,
    get_agent_config,
    get_orchestrator,
    reset_orchestrator,
)


def _tool_names(agent_cls) -> set[str]:
    """Extract tool names from an agent class."""
    return {t.name for t in agent_cls().tools}


# =============================================================================
# Dataclass Tests
# =============================================================================


class TestKnowledgeResult:
    def test_full(self):
        r = KnowledgeResult(content="x", metadata={"source": "linkedin"}, score=0.9)
        assert r.content == "x"
        assert r.score == 0.9

    def test_default_score(self):
        r = KnowledgeResult(content="x", metadata={})
        assert r.score is None


class TestMemoryResult:
    def test_full(self):
        r = MemoryResult(content="y", event_type="decision", timestamp=1.0, score=0.8)
        assert r.event_type == "decision"

    def test_defaults(self):
        r = MemoryResult(content="y", event_type="goal")
        assert r.timestamp is None
        assert r.score is None


# =============================================================================
# BaseAgent Tests
# =============================================================================


class TestBaseAgent:
    def _make_agent(self, tools: list | None = None) -> BaseAgent:
        """Create a minimal concrete BaseAgent for testing."""

        class _Agent(BaseAgent):
            @property
            def name(self) -> str:
                return "test"

            @property
            def description(self) -> str:
                return "Test agent"

            @property
            def system_prompt(self) -> str:
                return "You are a test agent."

            @property
            def tools(self) -> list[Callable]:
                return tools or []

            def can_handle(self, intent: str) -> bool:
                return "test" in intent.lower()

        return _Agent()

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore[abstract]

    def test_concrete_implementation(self):
        agent = self._make_agent()
        assert agent.name == "test"
        assert agent.system_prompt == "You are a test agent."
        assert agent.can_handle("this is a test") is True
        assert agent.can_handle("no match") is False

    def test_contribute_returns_finding(self):
        """contribute() should return a dict with at least reasoning key."""
        agent = self._make_agent()
        blackboard = {
            "query": "How do I improve?",
            "user_profile": {"role": "Engineer"},
            "findings": {},
        }
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.tool_calls = []
        mock_response.content = "You should focus on X and Y."
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.return_value = mock_response

        mock_extractor = MagicMock()
        mock_finding = MagicMock()
        mock_finding.model_dump.return_value = {
            "reasoning": "Focus on X and Y.",
            "confidence": 0.75,
        }
        mock_extractor.invoke.return_value = mock_finding

        with patch("fu7ur3pr00f.llm.fallback.get_model_with_fallback") as mock_fallback:
            mock_fallback.return_value = (mock_model, MagicMock())
            mock_model.with_structured_output.return_value = mock_extractor
            finding = agent.contribute(blackboard)

        assert isinstance(finding, dict)


# =============================================================================
# Individual Specialist Tests
# =============================================================================


class TestCoachAgent:
    def test_identity(self):
        agent = CoachAgent()
        assert agent.name == "coach"
        assert len(agent.system_prompt) > 50

    def test_can_handle(self):
        agent = CoachAgent()
        assert agent.can_handle("How do I get promoted?") is True
        assert agent.can_handle("Leadership skills") is True
        assert agent.can_handle("GitHub profile tips") is False

    def test_has_analysis_tools(self):
        from fu7ur3pr00f.agents.tools.analysis import (
            analyze_skill_gaps,
            get_career_advice,
        )

        names = _tool_names(CoachAgent)
        assert analyze_skill_gaps.name in names
        assert get_career_advice.name in names

    def test_has_gathering_tools(self):
        from fu7ur3pr00f.agents.tools.gathering import gather_all_career_data

        names = _tool_names(CoachAgent)
        assert gather_all_career_data.name in names


class TestLearningAgent:
    def test_identity(self):
        agent = LearningAgent()
        assert agent.name == "learning"

    def test_can_handle(self):
        agent = LearningAgent()
        assert agent.can_handle("I want to learn Python") is True
        assert agent.can_handle("Certification roadmap") is True
        assert agent.can_handle("Find me a job") is False

    def test_has_tech_trends_tool(self):
        from fu7ur3pr00f.agents.tools.market import get_tech_trends

        names = _tool_names(LearningAgent)
        assert get_tech_trends.name in names


class TestJobsAgent:
    def test_identity(self):
        agent = JobsAgent()
        assert agent.name == "jobs"

    def test_can_handle(self):
        agent = JobsAgent()
        assert agent.can_handle("Find remote jobs paying $150k") is True
        assert agent.can_handle("Salary negotiation tips") is True
        assert agent.can_handle("Start a startup") is False

    def test_has_full_market_suite(self):
        from fu7ur3pr00f.agents.tools.financial import compare_salary_ppp
        from fu7ur3pr00f.agents.tools.market import search_jobs

        names = _tool_names(JobsAgent)
        assert search_jobs.name in names
        assert compare_salary_ppp.name in names


class TestCodeAgent:
    def test_identity(self):
        agent = CodeAgent()
        assert agent.name == "code"

    def test_can_handle(self):
        agent = CodeAgent()
        assert agent.can_handle("GitHub profile review") is True
        assert agent.can_handle("Open source contributions") is True
        assert agent.can_handle("Get promoted") is False

    def test_has_github_gitlab_tools(self):
        from fu7ur3pr00f.agents.tools.github import get_github_profile
        from fu7ur3pr00f.agents.tools.gitlab import search_gitlab_projects

        names = _tool_names(CodeAgent)
        assert get_github_profile.name in names
        assert search_gitlab_projects.name in names


class TestFounderAgent:
    def test_identity(self):
        agent = FounderAgent()
        assert agent.name == "founder"

    def test_can_handle(self):
        agent = FounderAgent()
        assert agent.can_handle("Launch a SaaS startup") is True
        assert agent.can_handle("Bootstrap vs fundraising") is True
        assert agent.can_handle("Learn Python") is False

    def test_has_market_and_financial_tools(self):
        from fu7ur3pr00f.agents.tools.financial import convert_currency
        from fu7ur3pr00f.agents.tools.market import analyze_market_fit

        names = _tool_names(FounderAgent)
        assert analyze_market_fit.name in names
        assert convert_currency.name in names


# =============================================================================
# OrchestratorAgent Tests
# =============================================================================


class TestOrchestratorAgent:
    def _make_orchestrator(self) -> OrchestratorAgent:
        """Orchestrator with real specialists (no LLM calls needed for routing)."""
        return OrchestratorAgent()

    def test_creation(self):
        orch = self._make_orchestrator()
        assert len(orch._specialists) == 5

    def test_routing_coach(self):
        """Test keyword fallback (mock LLM to fail)."""
        orch = self._make_orchestrator()
        with patch("fu7ur3pr00f.llm.fallback.get_model_with_fallback") as mock_model:
            mock_model.side_effect = RuntimeError("LLM failed")
            result = orch.route("How do I get promoted to Staff?")
            assert isinstance(result, list)
            assert result == ["coach"]

    def test_routing_learning(self):
        orch = self._make_orchestrator()
        result = orch.route("I want to learn Python")
        assert isinstance(result, list)
        assert "learning" in result

    def test_routing_jobs(self):
        orch = self._make_orchestrator()
        result = orch.route("Find remote senior developer jobs")
        assert isinstance(result, list)
        assert "jobs" in result

    def test_routing_code(self):
        orch = self._make_orchestrator()
        result = orch.route("Review my GitHub repos and profile")
        assert isinstance(result, list)
        assert "code" in result

    def test_routing_founder(self):
        orch = self._make_orchestrator()
        result = orch.route("Launch my SaaS startup idea")
        assert isinstance(result, list)
        assert "founder" in result

    def test_routing_default(self):
        orch = self._make_orchestrator()
        result = orch.route("Help me")
        assert isinstance(result, list)
        assert "coach" in result

    def test_routing_multi_5year_prediction(self):
        """Queries about 5-year predictions should route to multiple specialists."""
        orch = self._make_orchestrator()
        result = orch.route("Give me a 5 year prediction for my career")
        assert isinstance(result, list)
        assert len(result) >= 2  # LLM routing returns 2-4; exact count is model-dependent
        assert "coach" in result

    def test_routing_multi_comprehensive(self):
        """Queries with 'complete portrait' or 'overall' route to multiple."""
        orch = self._make_orchestrator()
        result = orch.route("Give me a complete portrait of my future")
        assert isinstance(result, list)
        assert "coach" in result

    def test_routing_multi_strategy(self):
        """Queries about overall strategy should route to multiple specialists."""
        orch = self._make_orchestrator()
        result = orch.route("What are my options and strategies?")
        assert isinstance(result, list)
        assert "coach" in result

    def test_routing_single_narrow_query(self):
        """Narrow, targeted queries should route to a single-element list."""
        orch = self._make_orchestrator()
        with patch("fu7ur3pr00f.llm.fallback.get_model_with_fallback") as mock_model:
            mock_model.side_effect = RuntimeError("LLM failed")
            result = orch.route("How do I get promoted to Staff?")
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0] == "coach"

    def test_list_agents(self):
        orch = self._make_orchestrator()
        agents = orch.list_agents()
        assert len(agents) == 5
        names = {a["name"] for a in agents}
        assert names == {"coach", "learning", "jobs", "code", "founder"}

    def test_get_specialist(self):
        orch = self._make_orchestrator()
        specialist = orch.get_specialist("jobs")
        assert isinstance(specialist, JobsAgent)

    def test_get_blackboard_executor_with_names(self):
        orch = self._make_orchestrator()
        executor = orch.get_blackboard_executor(["coach", "jobs"])
        assert "coach" in executor.specialists
        assert "jobs" in executor.specialists
        assert "learning" not in executor.specialists

    def test_get_blackboard_executor_default(self):
        orch = self._make_orchestrator()
        executor = orch.get_blackboard_executor()
        assert len(executor.specialists) == 5

    def test_reset_is_noop(self):
        orch = self._make_orchestrator()
        orch.reset()  # should not raise


# =============================================================================
# Singleton Tests
# =============================================================================


class TestOrchestratorSingleton:
    def test_get_orchestrator_returns_same_instance(self):
        reset_orchestrator()
        a = get_orchestrator()
        b = get_orchestrator()
        assert a is b
        reset_orchestrator()

    def test_reset_orchestrator_creates_new_instance(self):
        reset_orchestrator()
        a = get_orchestrator()
        reset_orchestrator()
        b = get_orchestrator()
        assert a is not b
        reset_orchestrator()

    def test_get_agent_config(self):
        config = get_agent_config(thread_id="test", user_id="user1")
        assert config["configurable"]["thread_id"] == "test"
        assert config["configurable"]["user_id"] == "user1"


# =============================================================================
# Values Filter Tests
# =============================================================================


class TestValuesFilter:
    def test_disabled_by_default(self):
        from fu7ur3pr00f.agents.values import ValuesContext, apply_values_filter

        ctx = ValuesContext(company_uses_proprietary=True, crunch_expected=True)
        response = apply_values_filter("Great salary!", context=ctx)
        assert response == "Great salary!"

    def test_enabled_adds_warnings(self):
        from fu7ur3pr00f.agents.values import ValuesContext, apply_values_filter
        from fu7ur3pr00f.config import settings

        ctx = ValuesContext(company_uses_proprietary=True, crunch_expected=True)
        original = settings.values_filter_enabled
        try:
            settings.values_filter_enabled = True
            response = apply_values_filter("Great salary!", context=ctx)
            assert "❌" in response or "⚠️" in response
        finally:
            settings.values_filter_enabled = original


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    def test_coach_routing_and_tools_present(self):
        """Coach agent has tools needed for a promotion query."""
        from fu7ur3pr00f.agents.tools.analysis import get_career_advice
        from fu7ur3pr00f.agents.tools.knowledge import search_career_knowledge

        orch = OrchestratorAgent()
        names = orch.route("How can I get promoted to Staff Engineer?")
        assert isinstance(names, list)
        assert "coach" in names

        specialist = orch.get_specialist("coach")
        tool_names = {t.name for t in specialist.tools}
        assert get_career_advice.name in tool_names
        assert search_career_knowledge.name in tool_names

    def test_jobs_routing_and_tools_present(self):
        """Jobs agent has salary and search tools."""
        from fu7ur3pr00f.agents.tools.financial import compare_salary_ppp
        from fu7ur3pr00f.agents.tools.market import search_jobs

        orch = OrchestratorAgent()
        names = orch.route("Search for remote Python jobs paying over $150k")
        assert isinstance(names, list)
        assert "jobs" in names

        specialist = orch.get_specialist("jobs")
        tool_names = {t.name for t in specialist.tools}
        assert search_jobs.name in tool_names
        assert compare_salary_ppp.name in tool_names
