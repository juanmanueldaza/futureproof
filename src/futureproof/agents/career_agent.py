"""Career Intelligence Agent using multi-agent supervisor pattern.

This module implements a multi-agent architecture with:
- A Supervisor agent that handles profile, analysis, generation, and memory
- A Research agent that handles data gathering, knowledge search, and market intelligence
- Handoff tools for seamless transfer between agents
- SummarizationMiddleware for automatic context management
- InMemoryStore for cross-thread episodic memory

Usage:
    from futureproof.agents.career_agent import create_career_agent, get_agent_config

    agent = create_career_agent()
    config = get_agent_config(thread_id="main")

    # Stream responses
    for chunk in agent.stream({"messages": [{"role": "user", "content": "..."}]}, config):
        print(chunk)
"""

import logging
from typing import Any, Literal, NotRequired, cast

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.messages import AIMessage, ToolMessage
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from futureproof.agents.tools import get_research_tools, get_supervisor_tools
from futureproof.llm.fallback import get_model_with_fallback
from futureproof.memory.checkpointer import get_checkpointer
from futureproof.memory.profile import load_profile
from futureproof.memory.store import get_memory_store

logger = logging.getLogger(__name__)

# Cached agent singleton to avoid recompiling the graph on every call
_cached_agent = None


# =============================================================================
# System Prompts
# =============================================================================

SUPERVISOR_PROMPT = """You are FutureProof, an intelligent career advisor and team supervisor.

## Your Role
You help users navigate their career by:
- Managing their profile (skills, goals, target roles)
- Analyzing skill gaps and career alignment
- Generating tailored CVs
- Providing strategic career advice
- Remembering decisions and preferences

## User Profile
{user_profile}

## Team
You have a Research agent that handles data gathering and job market research.
Use `transfer_to_research` when the user needs:
- Fresh data from GitHub, GitLab, or portfolio sites
- Job market searches or salary information
- Tech trends and hiring patterns
- Knowledge base searches about the user's background

## Guidelines
1. **Be conversational**: Be helpful and natural.
2. **Delegate research**: Transfer to Research agent for data gathering and searches.
3. **Be proactive**: If you notice something relevant, mention it.
4. **Remember context**: Reference past conversations and decisions when relevant.
5. **Be honest**: If you don't know something, say so clearly.
6. **Stay focused**: You're a career advisor, not a general assistant.

## Response Style
- Keep responses concise but informative
- Use markdown for formatting when helpful
- Suggest next steps when appropriate
"""

RESEARCH_PROMPT = """You are the Research agent for FutureProof, a career intelligence system.

## Your Role
You gather and search for career-related information:
- Fetch fresh data from GitHub, GitLab, and portfolio sites
- Search the career knowledge base for the user's skills and experience
- Search the job market for relevant opportunities
- Find tech trends and salary information

## Guidelines
1. **Be thorough**: Gather complete data when asked.
2. **Summarize findings**: Present results clearly and concisely.
3. **Transfer back**: After completing research, transfer back to the supervisor
   using `transfer_to_supervisor` so it can advise the user.
4. **Report issues**: If data sources are unavailable, say so clearly.
"""


# =============================================================================
# Multi-Agent State
# =============================================================================


class MultiAgentState(AgentState):
    """State for the multi-agent supervisor graph."""

    active_agent: NotRequired[str]


# =============================================================================
# Handoff Tools
# =============================================================================


@tool
def transfer_to_research(runtime: ToolRuntime) -> Command:
    """Transfer to research agent for data gathering and market intelligence."""
    last_ai_message = next(
        (msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)),
        None,
    )
    transfer_message = ToolMessage(
        content="Transferring to research agent",
        tool_call_id=runtime.tool_call_id,
    )
    messages = [last_ai_message, transfer_message] if last_ai_message else [transfer_message]
    return Command(
        goto="research_agent",
        update={"active_agent": "research_agent", "messages": messages},
        graph=Command.PARENT,
    )


@tool
def transfer_to_supervisor(runtime: ToolRuntime) -> Command:
    """Transfer back to the supervisor agent with research results."""
    last_ai_message = next(
        (msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)),
        None,
    )
    transfer_message = ToolMessage(
        content="Research complete, transferring back to supervisor",
        tool_call_id=runtime.tool_call_id,
    )
    messages = [last_ai_message, transfer_message] if last_ai_message else [transfer_message]
    return Command(
        goto="supervisor",
        update={"active_agent": "supervisor", "messages": messages},
        graph=Command.PARENT,
    )


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


def create_career_agent():
    """Create the multi-agent career intelligence system (cached singleton).

    Architecture:
        ┌─────────────────────────────────────────┐
        │              StateGraph                  │
        │  ┌──────────┐     ┌──────────────────┐  │
        │  │Supervisor │◄───►│ Research Agent    │  │
        │  │  Agent    │     │ (gather, search,  │  │
        │  │(profile,  │     │  market intel)    │  │
        │  │ analyze,  │     └──────────────────┘  │
        │  │ generate, │                           │
        │  │ memory)   │                           │
        │  └──────────┘                            │
        └─────────────────────────────────────────┘

    Returns:
        A compiled multi-agent StateGraph
    """
    global _cached_agent
    if _cached_agent is not None:
        return _cached_agent

    model = get_model()
    checkpointer = get_checkpointer()
    store = get_memory_store()
    profile_context = _get_user_profile_context()

    summarization = SummarizationMiddleware(
        model=model,
        trigger=("tokens", 8000),
        keep=("messages", 20),
    )

    # Create the supervisor agent (profile, analysis, generation, memory)
    supervisor_agent = create_agent(
        model=model,
        tools=get_supervisor_tools() + [transfer_to_research],
        store=store,
        system_prompt=SUPERVISOR_PROMPT.format(user_profile=profile_context),
        middleware=[summarization],
    )

    # Create the research agent (gathering, knowledge search, market intel)
    research_agent = create_agent(
        model=model,
        tools=get_research_tools() + [transfer_to_supervisor],
        store=store,
        system_prompt=RESEARCH_PROMPT,
        middleware=[summarization],
    )

    # Build the multi-agent graph
    builder: StateGraph = StateGraph(MultiAgentState)
    builder.add_node("supervisor", supervisor_agent)
    builder.add_node("research_agent", research_agent)

    # Start with supervisor
    builder.add_edge(START, "supervisor")

    # Route based on active agent after each step
    def route_after_agent(
        state: MultiAgentState,
    ) -> Literal["supervisor", "research_agent", "__end__"]:
        active = state.get("active_agent", "supervisor")
        # Check if the last message indicates the conversation should end
        messages = state.get("messages", [])
        if messages and not isinstance(messages[-1], (ToolMessage,)):
            # If the last message is from an AI (not a tool), and there's no
            # pending transfer, end the conversation turn
            last = messages[-1]
            if isinstance(last, AIMessage) and not last.tool_calls:
                return "__end__"
        return active  # type: ignore[return-value]

    builder.add_conditional_edges(
        "supervisor",
        route_after_agent,
        {
            "supervisor": "supervisor",
            "research_agent": "research_agent",
            "__end__": END,
        },
    )
    builder.add_conditional_edges(
        "research_agent",
        route_after_agent,
        {
            "supervisor": "supervisor",
            "research_agent": "research_agent",
            "__end__": END,
        },
    )

    agent = builder.compile(checkpointer=checkpointer)

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


def chat(
    message: str,
    thread_id: str = "main",
    stream: bool = True,
):
    """Send a message to the career agent.

    This is a convenience function for simple interactions.

    Args:
        message: The user's message
        thread_id: Conversation thread for persistence
        stream: Whether to stream the response

    Yields:
        Response chunks if streaming, otherwise returns full response
    """
    agent = create_career_agent()
    config = get_agent_config(thread_id=thread_id)

    input_message: Any = {"messages": [HumanMessage(content=message)]}

    if stream:
        for chunk, metadata in agent.stream(
            input_message,
            cast(RunnableConfig, config),
            stream_mode="messages",
        ):
            # chunk can be AIMessageChunk or str depending on stream mode
            if hasattr(chunk, "content") and chunk.content:  # type: ignore[union-attr]
                yield chunk.content  # type: ignore[union-attr]
    else:
        result = agent.invoke(input_message, cast(RunnableConfig, config))
        return result["messages"][-1].content


async def achat(
    message: str,
    thread_id: str = "main",
):
    """Async version of chat for use in async contexts.

    Args:
        message: The user's message
        thread_id: Conversation thread for persistence

    Yields:
        Response chunks as they're generated
    """
    agent = create_career_agent()
    config = get_agent_config(thread_id=thread_id)

    input_message: Any = {"messages": [HumanMessage(content=message)]}

    async for chunk, metadata in agent.astream(
        input_message,
        cast(RunnableConfig, config),
        stream_mode="messages",
    ):
        # chunk can be AIMessageChunk or str depending on stream mode
        if hasattr(chunk, "content") and chunk.content:  # type: ignore[union-attr]
            yield chunk.content  # type: ignore[union-attr]
