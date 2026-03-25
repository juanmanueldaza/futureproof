"""Tests for BaseAgent and specialist agents."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fu7ur3pr00f.agents.specialists.base import BaseAgent, KnowledgeResult, MemoryResult
from fu7ur3pr00f.agents.specialists.coach import CoachAgent
from fu7ur3pr00f.agents.specialists.code import CodeAgent
from fu7ur3pr00f.agents.specialists.founder import FounderAgent
from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
from fu7ur3pr00f.agents.specialists.learning import LearningAgent
from fu7ur3pr00f.agents.specialists.orchestrator import OrchestratorAgent

# =============================================================================
# Dataclass Tests
# =============================================================================


class TestKnowledgeResult:
    def test_create_with_all_fields(self):
        result = KnowledgeResult(
            content="Test content",
            metadata={"source": "test", "section": "experience"},
            score=0.95,
        )
        assert result.content == "Test content"
        assert result.metadata == {"source": "test", "section": "experience"}
        assert result.score == 0.95

    def test_default_score(self):
        result = KnowledgeResult(content="Test", metadata={})
        assert result.score is None


class TestMemoryResult:
    def test_create_with_all_fields(self):
        result = MemoryResult(
            content="Test memory",
            event_type="decision",
            timestamp=1711234567.0,
            score=0.88,
        )
        assert result.content == "Test memory"
        assert result.event_type == "decision"
        assert result.timestamp == 1711234567.0
        assert result.score == 0.88

    def test_default_values(self):
        result = MemoryResult(content="Test", event_type="goal")
        assert result.timestamp is None
        assert result.score is None


# =============================================================================
# BaseAgent Tests
# =============================================================================


class TestBaseAgent:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore[abstract]

    def test_concrete_implementation(self):
        class TestAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "test"

            @property
            def description(self) -> str:
                return "Test agent"

            @property
            def system_prompt(self) -> str:
                return "You are a test agent."

            def can_handle(self, intent: str) -> bool:
                return "test" in intent.lower()

        agent = TestAgent()
        assert agent.name == "test"
        assert agent.description == "Test agent"
        assert agent.system_prompt == "You are a test agent."
        assert agent.can_handle("This is a test") is True
        assert agent.can_handle("No match") is False

    def test_build_system_prompt(self):
        class TestAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "test"

            @property
            def description(self) -> str:
                return "Test"

            @property
            def system_prompt(self) -> str:
                return "Base prompt."

            def can_handle(self, intent: str) -> bool:
                return True

        agent = TestAgent()
        full = agent._build_system_prompt("Profile info", "KB context data")
        assert "Base prompt." in full
        assert "Profile info" in full
        assert "KB context data" in full
        assert "Instructions" in full

    def test_format_profile_empty(self):
        class TestAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "test"

            @property
            def description(self) -> str:
                return "Test"

            @property
            def system_prompt(self) -> str:
                return ""

            def can_handle(self, intent: str) -> bool:
                return True

        agent = TestAgent()
        # With empty dict and mocked profile loader (lazy import)
        with patch("fu7ur3pr00f.memory.profile.load_profile", side_effect=Exception):
            result = agent._format_profile({})
        assert "No profile" in result

    def test_format_profile_from_dict(self):
        class TestAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "test"

            @property
            def description(self) -> str:
                return "Test"

            @property
            def system_prompt(self) -> str:
                return ""

            def can_handle(self, intent: str) -> bool:
                return True

        agent = TestAgent()
        result = agent._format_profile({"name": "Alice", "current_role": "SWE"})
        assert "Alice" in result
        assert "SWE" in result


# =============================================================================
# CoachAgent Tests
# =============================================================================


class TestCoachAgent:
    def test_creation(self):
        agent = CoachAgent()
        assert agent.name == "coach"
        assert "coach" in agent.description.lower()

    def test_can_handle(self):
        agent = CoachAgent()
        assert agent.can_handle("How do I get promoted?") is True
        assert agent.can_handle("I want to become Staff Engineer") is True
        assert agent.can_handle("Leadership development") is True
        assert agent.can_handle("Find me a job") is False
        assert agent.can_handle("Search GitHub repos") is False

    def test_has_system_prompt(self):
        agent = CoachAgent()
        assert len(agent.system_prompt) > 100
        assert (
            "promotion" in agent.system_prompt.lower()
            or "career" in agent.system_prompt.lower()
        )

    @pytest.mark.asyncio
    async def test_process_calls_llm(self):
        agent = CoachAgent()
        mock_result = MagicMock()
        mock_result.content = "Coaching advice here."
        with patch.object(
            agent, "_call_llm", return_value="Coaching advice here."
        ) as mock_llm:
            with patch.object(agent, "search_knowledge", return_value=[]):
                response = await agent.process({"query": "How do I get promoted?"})
        assert "Coaching advice" in response
        mock_llm.assert_called_once()


# =============================================================================
# Other Specialist Tests
# =============================================================================


class TestLearningAgent:
    def test_creation(self):
        agent = LearningAgent()
        assert agent.name == "learning"

    def test_can_handle(self):
        agent = LearningAgent()
        assert agent.can_handle("I want to learn Python") is True
        assert agent.can_handle("How to become an expert?") is True
        assert agent.can_handle("certification courses") is True
        assert agent.can_handle("get promoted") is False


class TestJobsAgent:
    def test_creation(self):
        agent = JobsAgent()
        assert agent.name == "jobs"

    def test_can_handle(self):
        agent = JobsAgent()
        assert agent.can_handle("Find me a job") is True
        assert agent.can_handle("remote python developer") is True
        assert agent.can_handle("salary negotiation") is True
        assert agent.can_handle("learn Python") is False


class TestCodeAgent:
    def test_creation(self):
        agent = CodeAgent()
        assert agent.name == "code"

    def test_can_handle(self):
        agent = CodeAgent()
        assert agent.can_handle("Improve my GitHub") is True
        assert agent.can_handle("open source contributions") is True
        assert agent.can_handle("get promoted") is False


class TestFounderAgent:
    def test_creation(self):
        agent = FounderAgent()
        assert agent.name == "founder"

    def test_can_handle(self):
        agent = FounderAgent()
        assert agent.can_handle("Should I start a company?") is True
        assert agent.can_handle("launch my startup") is True
        assert agent.can_handle("MVP planning") is True
        assert agent.can_handle("get promoted") is False


# =============================================================================
# OrchestratorAgent Tests
# =============================================================================


class TestOrchestratorAgent:
    def test_creation(self):
        agent = OrchestratorAgent()
        assert agent.name == "orchestrator"
        assert "routes" in agent.description.lower()

    def test_can_handle_all(self):
        agent = OrchestratorAgent()
        assert agent.can_handle("Anything at all") is True

    @pytest.mark.asyncio
    async def test_initialize(self):
        agent = OrchestratorAgent()
        await agent.initialize()
        assert "coach" in agent.specialists
        assert "learning" in agent.specialists
        assert "jobs" in agent.specialists
        assert "code" in agent.specialists
        assert "founder" in agent.specialists

    def test_routing_coach(self):
        agent = OrchestratorAgent()
        agent.specialists = {
            "coach": CoachAgent(),
            "learning": LearningAgent(),
            "jobs": JobsAgent(),
            "code": CodeAgent(),
            "founder": FounderAgent(),
        }
        assert agent._route("How do I get promoted?") == "coach"
        assert agent._route("Leadership development") == "coach"

    def test_routing_learning(self):
        agent = OrchestratorAgent()
        agent.specialists = {
            "coach": CoachAgent(),
            "learning": LearningAgent(),
            "jobs": JobsAgent(),
            "code": CodeAgent(),
            "founder": FounderAgent(),
        }
        assert agent._route("I want to learn Python") == "learning"

    def test_routing_jobs(self):
        agent = OrchestratorAgent()
        agent.specialists = {
            "coach": CoachAgent(),
            "learning": LearningAgent(),
            "jobs": JobsAgent(),
            "code": CodeAgent(),
            "founder": FounderAgent(),
        }
        assert agent._route("Find me a job") == "jobs"
        assert agent._route("hiring") == "jobs"

    def test_routing_code(self):
        agent = OrchestratorAgent()
        agent.specialists = {
            "coach": CoachAgent(),
            "learning": LearningAgent(),
            "jobs": JobsAgent(),
            "code": CodeAgent(),
            "founder": FounderAgent(),
        }
        assert agent._route("Improve my GitHub repos") == "code"

    def test_routing_founder(self):
        agent = OrchestratorAgent()
        agent.specialists = {
            "coach": CoachAgent(),
            "learning": LearningAgent(),
            "jobs": JobsAgent(),
            "code": CodeAgent(),
            "founder": FounderAgent(),
        }
        assert agent._route("Should I start a company?") == "founder"

    def test_routing_default_coach(self):
        agent = OrchestratorAgent()
        agent.specialists = {
            "coach": CoachAgent(),
            "learning": LearningAgent(),
            "jobs": JobsAgent(),
            "code": CodeAgent(),
            "founder": FounderAgent(),
        }
        assert agent._route("Help me with something") == "coach"

    @pytest.mark.asyncio
    async def test_get_available_agents(self):
        agent = OrchestratorAgent()
        await agent.initialize()
        agents = agent.get_available_agents()
        assert len(agents) == 5
        names = {a["name"] for a in agents}
        assert names == {"coach", "learning", "jobs", "code", "founder"}

    @pytest.mark.asyncio
    async def test_handle_delegates_to_specialist(self):
        agent = OrchestratorAgent()
        await agent.initialize()
        agent.specialists["coach"] = MagicMock()
        agent.specialists["coach"].can_handle.return_value = True
        agent.specialists["coach"].KEYWORDS = CoachAgent.KEYWORDS
        agent.specialists["coach"].process = AsyncMock(return_value="Coach says hello")

        response = await agent.handle("How do I get promoted?")
        assert response == "Coach says hello"

    def test_fallback_message(self):
        agent = OrchestratorAgent()
        agent.specialists = {"coach": CoachAgent()}
        msg = agent._fallback_message()
        assert "coach" in msg.lower()


# =============================================================================
# Values Filter (opt-in) Tests
# =============================================================================


class TestValuesFilter:
    def test_disabled_by_default(self):
        from fu7ur3pr00f.agents.values import ValuesContext, apply_values_filter

        ctx = ValuesContext(company_uses_proprietary=True, crunch_expected=True)
        response = apply_values_filter("Great salary!", context=ctx)
        # Values filter is disabled by default — response unchanged
        assert response == "Great salary!"

    def test_enabled_via_config(self):
        from fu7ur3pr00f.agents.values import ValuesContext, apply_values_filter

        ctx = ValuesContext(company_uses_proprietary=True, crunch_expected=True)
        with patch("fu7ur3pr00f.config.settings") as mock_settings:
            mock_settings.values_filter_enabled = True
            response = apply_values_filter("Great salary!", context=ctx)
        # Should now include warnings
        assert "⚠️" in response or "red flag" in response.lower() or "❌" in response


# =============================================================================
# Integration Tests
# =============================================================================


class TestMultiAgentIntegration:
    @pytest.mark.asyncio
    async def test_orchestrator_routes_to_coach(self):
        orchestrator = OrchestratorAgent()
        await orchestrator.initialize()
        assert (
            orchestrator._route("How can I get promoted to Staff Engineer?") == "coach"
        )

    @pytest.mark.asyncio
    async def test_full_flow_with_mocked_llm(self):
        orchestrator = OrchestratorAgent()
        await orchestrator.initialize()

        # Mock the LLM call on the coach agent
        with patch.object(
            orchestrator.specialists["coach"],
            "_call_llm",
            return_value="You should focus on system design and leadership.",
        ):
            with patch.object(
                orchestrator.specialists["coach"],
                "search_knowledge",
                return_value=[],
            ):
                response = await orchestrator.handle("How can I get promoted?")

        assert "system design" in response.lower() or "leadership" in response.lower()
