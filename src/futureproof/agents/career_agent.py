"""Career Intelligence Agent.

Single agent with all career intelligence tools — profile management,
analysis, CV generation, data gathering, knowledge search, market
intelligence, and memory.

Uses LangChain's create_agent() with SummarizationMiddleware for automatic
context management. Episodic memory is persisted via ChromaDB.

Usage:
    from futureproof.agents.career_agent import create_career_agent, get_agent_config

    agent = create_career_agent()
    config = get_agent_config(thread_id="main")

    # Stream responses
    for chunk in agent.stream({"messages": [{"role": "user", "content": "..."}]}, config):
        print(chunk)
"""

import logging
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware.summarization import SummarizationMiddleware

from futureproof.agents.middleware import (
    AnalysisSynthesisMiddleware,
    ToolCallRepairMiddleware,
    build_dynamic_prompt,
)
from futureproof.agents.tools import get_all_tools
from futureproof.llm.fallback import get_model_with_fallback
from futureproof.memory.checkpointer import get_checkpointer

logger = logging.getLogger(__name__)

# Cached agent singleton to avoid recompiling the graph on every call
_cached_agent = None
_cached_model_desc: str | None = None


# =============================================================================
# Agent Creation
# =============================================================================


def get_model():
    """Get the LLM model for the agent with automatic fallback."""
    global _cached_model_desc
    model, config = get_model_with_fallback(purpose="agent")
    _cached_model_desc = config.description
    logger.info(f"Career agent using: {config.description}")
    return model


def _get_summary_model():
    """Get a (potentially cheaper) model for summarization."""
    model, config = get_model_with_fallback(purpose="summary")
    logger.info(f"Summarization using: {config.description}")
    return model


def create_career_agent(
    model=None,
    checkpointer=None,
):
    """Create the career intelligence agent (cached singleton).

    Accepts optional dependency overrides for testing. When all args are None
    (the default), uses the cached singleton for performance.

    The system prompt is generated dynamically on every model call via
    build_dynamic_prompt middleware — it injects live profile and knowledge
    base stats so the model always knows what data is available.

    Args:
        model: Optional LLM model override
        checkpointer: Optional checkpointer override

    Returns:
        A compiled agent with all career intelligence tools
    """
    global _cached_agent
    using_defaults = all(arg is None for arg in (model, checkpointer))

    if _cached_agent is not None and using_defaults:
        return _cached_agent

    model = model or get_model()
    checkpointer = checkpointer or get_checkpointer()

    summary_model = _get_summary_model()
    repair = ToolCallRepairMiddleware()
    analysis_display = AnalysisSynthesisMiddleware()
    summarization = SummarizationMiddleware(
        model=summary_model,
        trigger=("tokens", 16000),
        keep=("messages", 20),
    )

    agent = create_agent(
        model=model,
        tools=get_all_tools(),
        middleware=[build_dynamic_prompt, repair, analysis_display, summarization],
        checkpointer=checkpointer,
    )

    if using_defaults:
        _cached_agent = agent
    return agent


def get_agent_model_name() -> str | None:
    """Get the description of the model used by the agent."""
    return _cached_model_desc


def reset_career_agent() -> None:
    """Reset the cached agent instance.

    Call this to force recreation of the agent, e.g., after a model fallback
    or when the system prompt needs to be refreshed.
    """
    global _cached_agent, _cached_model_desc
    _cached_agent = None
    _cached_model_desc = None


def get_agent_config(
    thread_id: str = "main",
    user_id: str = "default",
) -> dict[str, Any]:
    """Get the configuration for invoking the agent.

    Args:
        thread_id: Conversation thread identifier for checkpointing
        user_id: User identifier for profile/memory scoping

    Returns:
        Config dict to pass to agent.invoke() or agent.stream()
    """
    return {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        }
    }
