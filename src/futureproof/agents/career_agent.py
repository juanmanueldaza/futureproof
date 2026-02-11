"""Career Intelligence Agent using LangGraph ReAct pattern.

This is the conversational agent that replaces the old command-based CLI.
It uses LangGraph's create_react_agent with custom tools for career intelligence.

The agent:
- Maintains conversation history via SqliteSaver checkpointer
- Has access to tools for gathering data, analyzing skills, generating CVs
- Streams responses token-by-token for real-time terminal output
- Supports human-in-the-loop for approvals (CV generation, etc.)

Usage:
    from futureproof.agents.career_agent import create_career_agent, get_agent_config

    agent = create_career_agent()
    config = get_agent_config(thread_id="main")

    # Stream responses
    for chunk in agent.stream({"messages": [{"role": "user", "content": "..."}]}, config):
        print(chunk)
"""

import logging
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent

# Import tools (will be created in Phase 2, for now use placeholder)
from futureproof.agents.tools import get_career_tools
from futureproof.llm.fallback import get_model_with_fallback
from futureproof.memory.checkpointer import get_checkpointer
from futureproof.memory.profile import load_profile

logger = logging.getLogger(__name__)

# Career advisor system prompt
CAREER_ADVISOR_PROMPT = """You are FutureProof, an intelligent career advisor.

## Your Role
You help users navigate their career by:
- Analyzing their skills and identifying gaps for target roles
- Finding relevant job opportunities
- Generating tailored CVs and cover letters
- Providing strategic career advice
- Remembering their goals, preferences, and past decisions

## User Profile
{user_profile}

## Guidelines
1. **Be conversational**: This is a chat, not a command interface. Be helpful and natural.
2. **Use `search_career_knowledge` tool**: To answer questions about the user's background,
   skills, projects, or experience, search the knowledge base. Don't assume - search first.
3. **Be proactive**: If you notice something relevant (skill gap, opportunity match), mention it.
4. **Use tools for fresh data**: Use tools when you need real-time job market data or to
   update/gather new information.
5. **Remember context**: Reference past conversations and decisions when relevant.
6. **Be honest**: If you don't know something or can't help, say so clearly.
7. **Stay focused**: You're a career advisor, not a general assistant.

## Available Capabilities
- Search career knowledge base for user's skills, projects, experience
- Gather fresh career data from GitHub, GitLab, LinkedIn, portfolio sites
- Analyze skill gaps between current skills and target roles
- Search job market for relevant opportunities
- Generate CVs tailored to specific roles
- Remember user decisions and preferences for future reference

## Response Style
- Keep responses concise but informative
- Use markdown for formatting when helpful
- Suggest next steps when appropriate
- Ask clarifying questions if the request is ambiguous
"""


def get_model():
    """Get the LLM model for the agent with automatic fallback.

    Uses the FallbackLLMManager to select the best available model
    and automatically fall back to alternatives on rate limits.

    Returns:
        A LangChain chat model instance
    """
    model, config = get_model_with_fallback()
    logger.info(f"Career agent using: {config.description}")
    return model


def get_system_prompt() -> str:
    """Build the system prompt with user profile context.

    Note: Career data is NOT included in the prompt to keep token usage low.
    The agent should use the `search_career_knowledge` tool to retrieve
    relevant career data on-demand from the knowledge base (RAG).
    """
    profile = load_profile()
    profile_context = profile.summary() if profile.name else "No profile configured yet."

    return CAREER_ADVISOR_PROMPT.format(
        user_profile=profile_context,
    )


def create_career_agent():
    """Create the career intelligence ReAct agent.

    Returns:
        A compiled LangGraph agent with:
        - Checkpointing for conversation persistence
        - Tools for career intelligence operations
        - Streaming enabled for real-time responses
    """
    model = get_model()
    tools = get_career_tools()
    checkpointer = get_checkpointer()

    # Create the ReAct agent
    agent = create_react_agent(
        model=model,
        tools=tools,
        checkpointer=checkpointer,
        prompt=get_system_prompt(),
    )

    return agent


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

    input_message = {"messages": [HumanMessage(content=message)]}

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

    input_message = {"messages": [HumanMessage(content=message)]}

    async for chunk, metadata in agent.astream(
        input_message,
        cast(RunnableConfig, config),
        stream_mode="messages",
    ):
        # chunk can be AIMessageChunk or str depending on stream mode
        if hasattr(chunk, "content") and chunk.content:  # type: ignore[union-attr]
            yield chunk.content  # type: ignore[union-attr]
