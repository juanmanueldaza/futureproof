"""Agent middleware for state repair and dynamic prompt injection."""

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import dynamic_prompt
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)

# TTL cache for build_dynamic_prompt — avoids repeated disk I/O
# and ChromaDB queries across the 3-5 model calls per user message.
_prompt_cache: str | None = None
_prompt_cache_time: float = 0.0
_prompt_cache_lock = threading.Lock()
_PROMPT_TTL = 5.0  # seconds


# =============================================================================
# Dynamic Prompt — injects live profile + knowledge stats into system prompt
# =============================================================================


@dynamic_prompt
def build_dynamic_prompt(request: ModelRequest) -> str:
    """Build system prompt with live profile and knowledge base stats.

    Runs on every model call via wrap_model_call, replacing the static
    system_prompt. Uses a 5-second TTL cache to avoid repeated disk I/O
    and ChromaDB queries across the 3-5 model calls per user message.
    """
    global _prompt_cache, _prompt_cache_time

    now = time.monotonic()
    with _prompt_cache_lock:
        if (
            _prompt_cache is not None
            and (now - _prompt_cache_time) < _PROMPT_TTL
        ):
            return _prompt_cache

    result = _build_prompt_uncached()

    with _prompt_cache_lock:
        _prompt_cache = result
        _prompt_cache_time = time.monotonic()

    return result


def _build_prompt_uncached() -> str:
    """Generate the full system prompt (no caching)."""
    from futureproof.memory.profile import load_profile
    from futureproof.prompts import load_prompt
    from futureproof.services.knowledge_service import KnowledgeService

    # Single stats call — reused for auto-populate and data section
    service = KnowledgeService()
    stats = service.get_stats()

    profile = load_profile()
    summary = profile.summary()

    # Auto-populate profile if data exists but profile is empty
    if summary == "No profile information available.":
        if stats.get("total_chunks", 0) > 0:
            try:
                from futureproof.agents.tools.gathering import (
                    _auto_populate_profile,
                )

                _auto_populate_profile()
                profile = load_profile()
                summary = profile.summary()
            except Exception:
                pass  # Best-effort; don't break the prompt

    profile_context = (
        summary
        if summary != "No profile information available."
        else "No profile configured yet."
    )
    base = load_prompt("system").format(
        user_profile=profile_context,
    )

    # Append live knowledge base stats
    total = stats.get("total_chunks", 0)

    if total > 0:
        by_source = stats.get("by_source", {})
        sources = [
            f"- {src}: {count} chunks"
            for src, count in by_source.items()
            if count > 0
        ]
        data_section = (
            "\n\n## Data Availability (live)\n"
            + "\n".join(sources)
            + "\n\nCareer data is indexed and available. "
            "Use it immediately — do not ask the user to provide "
            "information that is already in the knowledge base."
        )
    else:
        data_section = (
            "\n\n## Data Availability (live)\n"
            "No career data indexed yet. "
            "You CANNOT answer career questions without data. "
            "Call `gather_all_career_data` immediately — the user "
            "will be asked to confirm before it runs."
        )

    return base + data_section


def _invalidate_prompt_cache() -> None:
    """Clear the dynamic prompt TTL cache. For tests."""
    global _prompt_cache
    with _prompt_cache_lock:
        _prompt_cache = None


# Analysis tools whose results are displayed directly to the user in Rich panels.
# The outer agent doesn't need to see (and rewrite) these — it just needs to know
# the analysis ran successfully.
_ANALYSIS_TOOLS = frozenset({
    "analyze_skill_gaps",
    "analyze_career_alignment",
    "get_career_advice",
})

_ANALYSIS_MARKER = (
    "[Detailed analysis was displayed directly to the user. "
    "Do not repeat or summarize it. Instead: reference salary data, "
    "ask about current compensation if unknown, and suggest "
    "1-2 concrete next steps.]"
)


class AnalysisSynthesisMiddleware(AgentMiddleware):
    """Two-pass middleware: masks analysis results, then synthesizes the final response.

    Pass 1 (before model): Replaces analysis tool results with short markers so
    the agent model (GPT-4o) can't rewrite them into generic advice. The user
    already sees full results in Rich UI panels during streaming.

    Pass 2 (after model): When the agent produces its final response (no more
    tool_calls) and analysis tools were used, the generic response is DISCARDED
    and replaced with a focused synthesis from a separate LLM call that sees
    the actual tool data and has a narrow, specific task.

    Uses wrap_model_call so modifications are ephemeral — the persisted state
    keeps the original analysis results and the synthesized response.
    """

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        # Find the last HumanMessage index — only consider analysis tools
        # from the current turn (after the last user message)
        last_human_idx = -1
        for i in range(len(request.messages) - 1, -1, -1):
            if isinstance(request.messages[i], HumanMessage):
                last_human_idx = i
                break

        # Phase 1: Mask analysis tool results with markers
        modified: list[AnyMessage] = []
        analysis_results: dict[str, str] = {}  # tool_name → original content
        for idx, msg in enumerate(request.messages):
            if (
                isinstance(msg, ToolMessage)
                and msg.name in _ANALYSIS_TOOLS
                and idx > last_human_idx
            ):
                analysis_results[msg.name] = msg.content
                modified.append(
                    ToolMessage(
                        content=_ANALYSIS_MARKER,
                        name=msg.name,
                        tool_call_id=msg.tool_call_id,
                    )
                )
            else:
                modified.append(msg)

        if analysis_results:
            logger.info(
                "Masked %d analysis tool result(s)", len(analysis_results)
            )
            response = handler(request.override(messages=modified))
        else:
            return handler(request)

        # Phase 2: If this is the final response (no tool_calls), synthesize
        if not response.result:
            return response

        ai_msg = response.result[0]
        if not isinstance(ai_msg, AIMessage) or ai_msg.tool_calls:
            # Agent wants to call more tools — let it continue
            return response

        # Final response detected — replace with synthesis
        logger.info("Synthesizing final response (replacing generic agent text)")
        return self._synthesize(
            request.messages, analysis_results, last_human_idx,
        )

    def _synthesize(
        self,
        messages: list[AnyMessage],
        analysis_results: dict[str, str],
        last_human_idx: int,
    ) -> ModelResponse:
        """Build a focused synthesis from tool results via a separate LLM call."""
        from futureproof.llm.fallback import get_model_with_fallback
        from futureproof.prompts import load_prompt

        # Extract the user's question (last HumanMessage)
        user_question = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_question = msg.content
                break

        # Only collect tool results from current turn (after last user msg)
        other_results: list[str] = []
        for msg in messages[last_human_idx:]:
            if (
                isinstance(msg, ToolMessage)
                and msg.name not in _ANALYSIS_TOOLS
                and msg.content
            ):
                other_results.append(f"**{msg.name}:**\n{msg.content}")

        # Build the tool results context
        parts: list[str] = []
        for name, content in analysis_results.items():
            parts.append(f"**{name}:**\n{content}")
        parts.extend(other_results)
        tool_results = "\n\n---\n\n".join(parts)

        # Load synthesis prompt and format
        prompt_template = load_prompt("synthesis")
        prompt = prompt_template.format(
            user_question=user_question,
            tool_results=tool_results,
        )

        # Call synthesis model
        model, config = get_model_with_fallback(purpose="synthesis")
        logger.info("Synthesis model: %s", config.description)
        result = model.invoke([SystemMessage(content=prompt)])

        return ModelResponse(result=[result])


class ToolCallRepairMiddleware(AgentMiddleware):
    """Detects and repairs orphaned tool_calls in message history.

    When parallel tool execution via the Send API fails to merge results
    back into the messages channel, this middleware injects synthetic error
    ToolMessages so the model can proceed instead of crashing with a 400
    "tool_call_ids did not have response messages" error.

    Must be placed before SummarizationMiddleware in the middleware list
    so repairs happen before any message summarization.
    """

    def before_model(self, state: AgentState[Any], runtime: Runtime) -> dict[str, Any] | None:
        messages = state["messages"]
        if not messages:
            return None

        # Find the last AIMessage (scan from end)
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if not isinstance(msg, AIMessage):
                continue

            if not msg.tool_calls:
                return None  # Last AIMessage has no tool_calls — nothing to repair

            # Collect tool_call_ids that have matching ToolMessages after this AIMessage
            expected_ids = {tc["id"] for tc in msg.tool_calls if tc.get("id")}
            found_ids: set[str] = set()
            for j in range(i + 1, len(messages)):
                tmsg = messages[j]
                if isinstance(tmsg, ToolMessage) and tmsg.tool_call_id:
                    found_ids.add(tmsg.tool_call_id)

            missing_ids = expected_ids - found_ids
            if not missing_ids:
                return None  # All tool_calls have matching responses

            logger.warning(
                "Repairing %d orphaned tool_call(s): %s",
                len(missing_ids),
                missing_ids,
            )
            return {
                "messages": [
                    ToolMessage(
                        content=(
                            "Tool execution failed — results were lost due to a "
                            "state synchronization error. Please retry if needed."
                        ),
                        tool_call_id=tid,
                    )
                    for tid in missing_ids
                ]
            }

        return None
