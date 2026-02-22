"""Tests for agent middleware."""

from typing import Any, cast
from unittest.mock import MagicMock, patch

from langchain.agents.middleware.types import AgentState, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from futureproof.agents.middleware import (
    AnalysisSynthesisMiddleware,
    ToolCallRepairMiddleware,
    _ANALYSIS_MARKER,
    build_dynamic_prompt,
)


def _make_state(messages: list[Any]) -> AgentState[Any]:
    """Build a minimal AgentState dict."""
    return cast(AgentState[Any], {"messages": messages})


def _make_runtime():
    """Build a mock Runtime."""
    return MagicMock()


class TestBuildDynamicPrompt:
    """Tests for build_dynamic_prompt middleware."""

    def _call_middleware(self, mock_profile, mock_stats):
        """Invoke wrap_model_call and capture the system message passed to handler."""
        captured = {}

        def handler(request):
            captured["system_message"] = request.system_message
            return MagicMock()

        request = ModelRequest(
            model=MagicMock(),
            messages=[HumanMessage(content="hello")],
            system_message=SystemMessage(content="original"),
        )

        with (
            patch("futureproof.memory.profile.load_profile", return_value=mock_profile),
            patch(
                "futureproof.services.knowledge_service.KnowledgeService.get_stats",
                return_value=mock_stats,
            ),
        ):
            build_dynamic_prompt.wrap_model_call(request, handler)

        return captured["system_message"].content

    def test_with_data_available(self):
        """Dynamic prompt includes knowledge base stats when data exists."""
        profile = MagicMock()
        profile.name = "Juan"
        profile.summary.return_value = "Name: Juan\nRole: Engineer"

        stats = {
            "total_chunks": 350,
            "by_source": {"linkedin": 280, "portfolio": 45, "assessment": 25},
        }

        content = self._call_middleware(profile, stats)
        assert "Name: Juan" in content
        assert "linkedin: 280 chunks" in content
        assert "portfolio: 45 chunks" in content
        assert "assessment: 25 chunks" in content
        assert "do not ask the user" in content.lower()

    def test_with_no_data(self):
        """Dynamic prompt indicates no data when knowledge base is empty."""
        profile = MagicMock()
        profile.name = None
        profile.summary.return_value = "No profile information available."

        stats = {"total_chunks": 0, "by_source": {}}

        content = self._call_middleware(profile, stats)
        assert "No profile configured yet" in content
        assert "No career data indexed" in content
        assert "gather_all_career_data" in content

    def test_partial_sources(self):
        """Only lists sources that have chunks in the data availability section."""
        profile = MagicMock()
        profile.name = "Ana"
        profile.summary.return_value = "Name: Ana"

        stats = {
            "total_chunks": 100,
            "by_source": {"linkedin": 100, "portfolio": 0, "assessment": 0},
        }

        content = self._call_middleware(profile, stats)
        assert "linkedin: 100 chunks" in content
        # Zero-chunk sources should not appear in the data availability section
        assert "portfolio: 0" not in content
        assert "assessment: 0" not in content


class TestAnalysisSynthesisMiddleware:
    """Tests for AnalysisSynthesisMiddleware (wrap_model_call)."""

    def setup_method(self):
        self.middleware = AnalysisSynthesisMiddleware()

    def _make_handler(self, response_msg=None):
        """Build a handler that captures messages and returns a configurable response."""
        captured = {}

        if response_msg is None:
            # Default: final response (no tool_calls)
            response_msg = AIMessage(content="Generic advice here...")

        def handler(req):
            captured["messages"] = req.messages
            return ModelResponse(result=[response_msg])

        return handler, captured

    def _call_masking(self, messages):
        """Invoke wrap_model_call and return the messages the handler received."""
        handler, captured = self._make_handler()
        request = ModelRequest(
            model=MagicMock(),
            messages=messages,
            system_message=SystemMessage(content="system"),
        )
        # Patch synthesis to avoid real LLM call
        with patch.object(self.middleware, "_synthesize", return_value=ModelResponse(result=[AIMessage(content="synth")])):
            self.middleware.wrap_model_call(request, handler)
        return captured["messages"]

    # =========================================================================
    # Phase 1: Masking tests
    # =========================================================================

    def test_no_analysis_tools_passthrough(self):
        """Handler receives original messages when no analysis tools present."""
        messages = [
            HumanMessage(content="hello"),
            AIMessage(
                content="",
                tool_calls=[{"id": "call_1", "name": "get_user_profile", "args": {}}],
            ),
            ToolMessage(content="Name: Juan", tool_call_id="call_1", name="get_user_profile"),
        ]
        handler, captured = self._make_handler()
        request = ModelRequest(
            model=MagicMock(),
            messages=messages,
            system_message=SystemMessage(content="system"),
        )
        self.middleware.wrap_model_call(request, handler)
        # Messages unchanged — same objects
        assert captured["messages"][2].content == "Name: Juan"

    def test_replaces_analysis_content(self):
        """Replaces content of analysis tool results with marker."""
        messages = [
            HumanMessage(content="analyze me"),
            AIMessage(
                content="",
                tool_calls=[{"id": "call_1", "name": "analyze_career_alignment", "args": {}}],
            ),
            ToolMessage(
                content="### Professional Identity\n- Senior Engineer at Accenture\n...",
                tool_call_id="call_1",
                name="analyze_career_alignment",
            ),
        ]
        result = self._call_masking(messages)
        tool_msg = result[2]
        assert isinstance(tool_msg, ToolMessage)
        assert tool_msg.content == _ANALYSIS_MARKER
        assert tool_msg.tool_call_id == "call_1"
        assert tool_msg.name == "analyze_career_alignment"

    def test_preserves_non_analysis_tools(self):
        """Non-analysis tools (salary, profile) remain untouched."""
        messages = [
            HumanMessage(content="money"),
            AIMessage(
                content="",
                tool_calls=[
                    {"id": "call_1", "name": "get_salary_insights", "args": {}},
                    {"id": "call_2", "name": "analyze_skill_gaps", "args": {}},
                ],
            ),
            ToolMessage(
                content="Salary: $150K-$200K",
                tool_call_id="call_1",
                name="get_salary_insights",
            ),
            ToolMessage(
                content="### Alignment Score: 85/100\n...",
                tool_call_id="call_2",
                name="analyze_skill_gaps",
            ),
        ]
        result = self._call_masking(messages)
        # Salary tool untouched
        assert result[2].content == "Salary: $150K-$200K"
        # Analysis tool replaced
        assert result[3].content == _ANALYSIS_MARKER

    def test_preserves_tool_call_id(self):
        """tool_call_id is preserved after replacement."""
        messages = [
            AIMessage(
                content="",
                tool_calls=[{"id": "tc_abc123", "name": "get_career_advice", "args": {}}],
            ),
            ToolMessage(
                content="Long advice text...",
                tool_call_id="tc_abc123",
                name="get_career_advice",
            ),
        ]
        result = self._call_masking(messages)
        tool_msg = result[1]
        assert tool_msg.tool_call_id == "tc_abc123"
        assert tool_msg.name == "get_career_advice"

    def test_multiple_analysis_tools(self):
        """All analysis tools in a mixed set are replaced."""
        messages = [
            HumanMessage(content="full analysis"),
            AIMessage(
                content="",
                tool_calls=[
                    {"id": "c1", "name": "get_user_profile", "args": {}},
                    {"id": "c2", "name": "analyze_career_alignment", "args": {}},
                    {"id": "c3", "name": "analyze_skill_gaps", "args": {}},
                    {"id": "c4", "name": "get_salary_insights", "args": {}},
                ],
            ),
            ToolMessage(content="Profile data", tool_call_id="c1", name="get_user_profile"),
            ToolMessage(content="Career analysis...", tool_call_id="c2", name="analyze_career_alignment"),
            ToolMessage(content="Skill gaps...", tool_call_id="c3", name="analyze_skill_gaps"),
            ToolMessage(content="Salary data...", tool_call_id="c4", name="get_salary_insights"),
        ]
        result = self._call_masking(messages)
        # Profile (index 2) and salary (index 5) untouched
        assert result[2].content == "Profile data"
        assert result[5].content == "Salary data..."
        # Analysis tools (index 3, 4) replaced
        assert result[3].content == _ANALYSIS_MARKER
        assert result[4].content == _ANALYSIS_MARKER

    def test_empty_messages(self):
        """Handler receives empty list when no messages."""
        handler, captured = self._make_handler()
        request = ModelRequest(
            model=MagicMock(),
            messages=[],
            system_message=SystemMessage(content="system"),
        )
        self.middleware.wrap_model_call(request, handler)
        assert captured["messages"] == []

    # =========================================================================
    # Phase 2: Synthesis tests
    # =========================================================================

    def test_synthesis_called_on_final_response(self):
        """When analysis tools present and response has no tool_calls, synthesis is triggered."""
        messages = [
            HumanMessage(content="how to earn more?"),
            AIMessage(
                content="",
                tool_calls=[{"id": "c1", "name": "analyze_career_alignment", "args": {}}],
            ),
            ToolMessage(
                content="Career alignment: 85/100...",
                tool_call_id="c1",
                name="analyze_career_alignment",
            ),
        ]
        # Handler returns final response (no tool_calls)
        handler, _ = self._make_handler(AIMessage(content="Generic advice..."))
        request = ModelRequest(
            model=MagicMock(),
            messages=messages,
            system_message=SystemMessage(content="system"),
        )

        synthesis_result = AIMessage(content="Target $180K-$200K at Google...")
        with patch.object(
            self.middleware, "_synthesize", return_value=ModelResponse(result=[synthesis_result])
        ) as mock_synth:
            response = self.middleware.wrap_model_call(request, handler)

        mock_synth.assert_called_once()
        # The synthesis result replaces the generic response
        assert response.result[0].content == "Target $180K-$200K at Google..."

    def test_no_synthesis_when_agent_calls_more_tools(self):
        """When response has tool_calls, no synthesis — agent continues."""
        messages = [
            HumanMessage(content="how to earn more?"),
            AIMessage(
                content="",
                tool_calls=[{"id": "c1", "name": "analyze_career_alignment", "args": {}}],
            ),
            ToolMessage(
                content="Career alignment: 85/100...",
                tool_call_id="c1",
                name="analyze_career_alignment",
            ),
        ]
        # Handler returns response WITH tool_calls (agent wants to call more tools)
        tool_call_response = AIMessage(
            content="",
            tool_calls=[{"id": "c2", "name": "get_salary_insights", "args": {}}],
        )
        handler, _ = self._make_handler(tool_call_response)
        request = ModelRequest(
            model=MagicMock(),
            messages=messages,
            system_message=SystemMessage(content="system"),
        )

        with patch.object(self.middleware, "_synthesize") as mock_synth:
            response = self.middleware.wrap_model_call(request, handler)

        mock_synth.assert_not_called()
        # Original response with tool_calls is returned
        assert response.result[0].tool_calls[0]["name"] == "get_salary_insights"

    def test_no_synthesis_without_analysis_tools(self):
        """No synthesis when no analysis tools were in the conversation."""
        messages = [
            HumanMessage(content="what's my profile?"),
            AIMessage(
                content="",
                tool_calls=[{"id": "c1", "name": "get_user_profile", "args": {}}],
            ),
            ToolMessage(content="Name: Juan", tool_call_id="c1", name="get_user_profile"),
        ]
        handler, _ = self._make_handler(AIMessage(content="Your name is Juan."))
        request = ModelRequest(
            model=MagicMock(),
            messages=messages,
            system_message=SystemMessage(content="system"),
        )

        with patch.object(self.middleware, "_synthesize") as mock_synth:
            response = self.middleware.wrap_model_call(request, handler)

        mock_synth.assert_not_called()
        assert response.result[0].content == "Your name is Juan."

    def test_synthesize_extracts_user_question(self):
        """_synthesize extracts the last HumanMessage as the user question."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Synthesis result")

        messages = [
            HumanMessage(content="first question"),
            HumanMessage(content="how to leverage my skills?"),
            AIMessage(
                content="",
                tool_calls=[{"id": "c1", "name": "analyze_skill_gaps", "args": {}}],
            ),
            ToolMessage(content="Gaps found...", tool_call_id="c1", name="analyze_skill_gaps"),
        ]
        analysis_results = {"analyze_skill_gaps": "Gaps found..."}

        with (
            patch(
                "futureproof.llm.fallback.get_model_with_fallback",
                return_value=(mock_model, MagicMock(description="test-model")),
            ),
            patch(
                "futureproof.prompts.load_prompt",
                return_value="Q: {user_question}\nR: {tool_results}",
            ),
        ):
            result = self.middleware._synthesize(messages, analysis_results)

        # Verify the synthesis model was called
        mock_model.invoke.assert_called_once()
        call_args = mock_model.invoke.call_args[0][0]
        prompt_content = call_args[0].content
        # Should contain the LAST human message
        assert "how to leverage my skills?" in prompt_content
        assert result.result[0].content == "Synthesis result"

    def test_synthesize_includes_other_tool_results(self):
        """_synthesize includes non-analysis tool results (salary, profile)."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Synthesis")

        messages = [
            HumanMessage(content="money"),
            AIMessage(
                content="",
                tool_calls=[
                    {"id": "c1", "name": "get_salary_insights", "args": {}},
                    {"id": "c2", "name": "analyze_career_alignment", "args": {}},
                ],
            ),
            ToolMessage(content="Salary: $150K-$200K", tool_call_id="c1", name="get_salary_insights"),
            ToolMessage(content="Alignment: 85/100", tool_call_id="c2", name="analyze_career_alignment"),
        ]
        analysis_results = {"analyze_career_alignment": "Alignment: 85/100"}

        with (
            patch(
                "futureproof.llm.fallback.get_model_with_fallback",
                return_value=(mock_model, MagicMock(description="test-model")),
            ),
            patch(
                "futureproof.prompts.load_prompt",
                return_value="Q: {user_question}\nR: {tool_results}",
            ),
        ):
            self.middleware._synthesize(messages, analysis_results)

        call_args = mock_model.invoke.call_args[0][0]
        prompt_content = call_args[0].content
        # Should contain both analysis AND salary data
        assert "Alignment: 85/100" in prompt_content
        assert "Salary: $150K-$200K" in prompt_content

    def test_synthesize_empty_response_passthrough(self):
        """When handler returns empty result, no synthesis attempted."""
        messages = [
            HumanMessage(content="analyze"),
            AIMessage(
                content="",
                tool_calls=[{"id": "c1", "name": "analyze_skill_gaps", "args": {}}],
            ),
            ToolMessage(content="Gaps...", tool_call_id="c1", name="analyze_skill_gaps"),
        ]

        def handler(req):
            return ModelResponse(result=[])

        request = ModelRequest(
            model=MagicMock(),
            messages=messages,
            system_message=SystemMessage(content="system"),
        )

        with patch.object(self.middleware, "_synthesize") as mock_synth:
            response = self.middleware.wrap_model_call(request, handler)

        mock_synth.assert_not_called()
        assert response.result == []


class TestToolCallRepairMiddleware:
    """Tests for ToolCallRepairMiddleware."""

    def setup_method(self):
        self.middleware = ToolCallRepairMiddleware()
        self.runtime = _make_runtime()

    def test_no_messages(self):
        result = self.middleware.before_model(_make_state([]), self.runtime)
        assert result is None

    def test_no_tool_calls(self):
        state = _make_state(
            [
                HumanMessage(content="hello"),
                AIMessage(content="hi there"),
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is None

    def test_all_tool_calls_matched(self):
        state = _make_state(
            [
                HumanMessage(content="analyze"),
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "tool_a", "args": {}}],
                ),
                ToolMessage(content="result", tool_call_id="call_1"),
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is None

    def test_single_orphaned_tool_call(self):
        state = _make_state(
            [
                HumanMessage(content="analyze"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "call_1", "name": "tool_a", "args": {}},
                        {"id": "call_2", "name": "tool_b", "args": {}},
                    ],
                ),
                ToolMessage(content="result", tool_call_id="call_1"),
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is not None
        assert len(result["messages"]) == 1
        msg = result["messages"][0]
        assert isinstance(msg, ToolMessage)
        assert msg.tool_call_id == "call_2"
        assert "state synchronization error" in msg.content

    def test_all_tool_calls_orphaned(self):
        state = _make_state(
            [
                HumanMessage(content="analyze"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "call_1", "name": "tool_a", "args": {}},
                        {"id": "call_2", "name": "tool_b", "args": {}},
                        {"id": "call_3", "name": "tool_c", "args": {}},
                    ],
                ),
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is not None
        assert len(result["messages"]) == 3
        repair_ids = {m.tool_call_id for m in result["messages"]}
        assert repair_ids == {"call_1", "call_2", "call_3"}

    def test_only_checks_last_ai_message(self):
        """Earlier AIMessage with orphaned tool_calls should be ignored."""
        state = _make_state(
            [
                HumanMessage(content="first"),
                AIMessage(
                    content="",
                    tool_calls=[{"id": "old_call", "name": "tool_a", "args": {}}],
                ),
                # No ToolMessage for old_call — but it's not the last AIMessage
                HumanMessage(content="second"),
                AIMessage(content="plain response"),
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is None

    def test_last_ai_with_tool_calls_has_orphans(self):
        """The last AIMessage with tool_calls has orphans, even if not the very last message."""
        state = _make_state(
            [
                HumanMessage(content="first"),
                AIMessage(content="earlier response"),
                HumanMessage(content="analyze"),
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "tool_a", "args": {}}],
                ),
                # No ToolMessage for call_1
            ]
        )
        result = self.middleware.before_model(state, self.runtime)
        assert result is not None
        assert len(result["messages"]) == 1
        assert result["messages"][0].tool_call_id == "call_1"
