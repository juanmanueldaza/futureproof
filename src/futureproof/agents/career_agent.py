"""Career Intelligence Agent.

Single agent with all career intelligence tools — profile management,
analysis, CV generation, data gathering, knowledge search, market
intelligence, and memory.

Uses LangChain's create_agent() with SummarizationMiddleware for automatic
context management and InMemoryStore for cross-thread episodic memory.

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
from langchain.agents.middleware import SummarizationMiddleware

from futureproof.agents.tools import get_all_tools
from futureproof.llm.fallback import get_model_with_fallback
from futureproof.memory.checkpointer import get_checkpointer
from futureproof.memory.profile import load_profile
from futureproof.memory.store import get_memory_store
from futureproof.prompts.system import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Cached agent singleton to avoid recompiling the graph on every call
_cached_agent = None


# =============================================================================
# Agent Creation
# =============================================================================


def get_model():
    """Get the LLM model for the agent with automatic fallback."""
    model, config = get_model_with_fallback()
    logger.info(f"Career agent using: {config.description}")
    return model


def _get_user_profile_context() -> str:
    """Get user profile context for system prompts."""
    profile = load_profile()
    return profile.summary() if profile.name else "No profile configured yet."


def create_career_agent(
    model=None,
    checkpointer=None,
    store=None,
    profile_context=None,
):
    """Create the career intelligence agent (cached singleton).

    Accepts optional dependency overrides for testing. When all args are None
    (the default), uses the cached singleton for performance.

    Args:
        model: Optional LLM model override
        checkpointer: Optional checkpointer override
        store: Optional InMemoryStore override
        profile_context: Optional profile context string override

    Returns:
        A compiled agent with all career intelligence tools
    """
    global _cached_agent
    using_defaults = all(arg is None for arg in (model, checkpointer, store, profile_context))

    if _cached_agent is not None and using_defaults:
        return _cached_agent

    model = model or get_model()
    checkpointer = checkpointer or get_checkpointer()
    store = store or get_memory_store()
    profile_context = profile_context or _get_user_profile_context()

    summarization = SummarizationMiddleware(
        model=model,
        trigger=("tokens", 8000),
        keep=("messages", 20),
    )

    agent = create_agent(
        model=model,
        tools=get_all_tools(),
        store=store,
        system_prompt=SYSTEM_PROMPT.format(user_profile=profile_context),
        middleware=[summarization],
        checkpointer=checkpointer,
    )

    if using_defaults:
        _cached_agent = agent
    return agent


def reset_career_agent() -> None:
    """Reset the cached agent instance.

    Call this to force recreation of the agent, e.g., after a model fallback
    or when the system prompt needs to be refreshed.
    """
    global _cached_agent
    _cached_agent = None


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
