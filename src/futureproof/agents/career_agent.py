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

logger = logging.getLogger(__name__)

# Cached agent singleton to avoid recompiling the graph on every call
_cached_agent = None


# =============================================================================
# System Prompt
# =============================================================================

SYSTEM_PROMPT = """You are FutureProof, an intelligent career advisor.

## Your Role
You help users navigate their career by:
- Managing their profile (skills, goals, target roles)
- Gathering career data from GitHub, GitLab, portfolio sites, LinkedIn, and assessments
- Searching and managing a career knowledge base
- Analyzing skill gaps, career alignment, and market positioning
- Generating tailored CVs
- Searching job markets, tech trends, and salary data
- Providing strategic career advice
- Remembering decisions and preferences

## User Profile
{user_profile}

## Your Tools

### Profile Management
- `get_user_profile` — View current profile
- `update_user_name`, `update_current_role`, `update_user_skills` — Update profile fields
- `set_target_roles`, `update_user_goal` — Set career targets

### Data Gathering
- `gather_github_data`, `gather_gitlab_data`, `gather_portfolio_data` — Fetch from sources
- `gather_linkedin_data` — Process LinkedIn export ZIP from data/raw/
- `gather_assessment_data` — Process CliftonStrengths Gallup PDFs from data/raw/
- `gather_all_career_data` — Gather from all sources (auto-detects LinkedIn/Gallup files)
- `get_stored_career_data` — Check what data is already stored

### Knowledge Base
- `search_career_knowledge` — Search indexed career data (supports source filtering)
- `get_knowledge_stats` — Show indexing statistics
- `index_career_knowledge` — Index gathered data for search
- `clear_career_knowledge` — Clear indexed data (with confirmation)

### Analysis
- `analyze_skill_gaps` — Identify gaps for a target role
- `analyze_career_alignment` — Assess career trajectory alignment
- `get_career_advice` — Get strategic career advice
- `analyze_market_fit` — Compare profile against market demands
- `analyze_market_skills` — Analyze skills vs market requirements

### CV Generation
- `generate_cv_draft` — Quick CV draft for a target role
- `generate_cv` — Full CV generation (with confirmation)

### Market Intelligence
- `search_jobs` — Search job listings
- `get_tech_trends` — Get technology trend data
- `get_salary_insights` — Get salary information
- `gather_market_data` — Comprehensive market data gathering

### Memory
- `remember_decision` — Record a career decision
- `remember_job_application` — Record a job application
- `recall_memories` — Search past decisions and applications
- `get_memory_stats` — View memory statistics

## Knowledge Base Sources
When using `search_career_knowledge`, use the `sources` filter to target the right data:
- **"assessment"**: CliftonStrengths themes, strengths insights, action items, blind spots
- **"github"**: GitHub repositories, contributions, code projects
- **"gitlab"**: GitLab projects and contributions
- **"linkedin"**: Work history, education, certifications, recommendations
- **"portfolio"**: Portfolio website content, personal projects

For CliftonStrengths or strengths-related queries, always filter with `sources=["assessment"]`.

## IMPORTANT: Always check data before responding
Before saying you don't have information about the user (strengths, skills, experience,
assessments, projects, etc.), ALWAYS search the knowledge base first. The user's
CliftonStrengths, GitHub projects, portfolio data, and other gathered information are
stored in the knowledge base — not in the profile. Never assume data is missing without
searching for it.

## Guidelines
1. **Be conversational**: Be helpful and natural.
2. **Use the right tool**: Each task has a dedicated tool — use it directly.
   Don't approximate (e.g., don't use `search_career_knowledge` instead of
   `analyze_skill_gaps` for analysis tasks).
3. **Complete all requested tasks**: When the user asks for multiple steps, execute
   ALL of them using the appropriate tools. Do not stop partway and ask for confirmation
   to continue — just do them all. Only pause for HITL interrupts.
4. **Index after gathering**: After gathering new data, index it into the knowledge base
   so it becomes searchable.
5. **Populate profile after gathering**: If the user profile is empty or incomplete after
   gathering data, search the knowledge base for key profile information (name, current role,
   skills, years of experience) and populate the profile using the profile tools. Use LinkedIn
   and GitHub data as primary sources for this.
6. **Be proactive**: If you notice something relevant, mention it.
7. **Remember context**: Reference past conversations and decisions when relevant.
8. **Be honest**: If you don't know something, say so clearly.
9. **Stay focused**: You're a career advisor, not a general assistant.
10. **Never echo internal state**: If you see a conversation summary in your context,
   use it for context only. NEVER repeat, quote, or display it in your response.
   Start your reply directly addressing the user's latest message.

## Response Style
- Keep responses concise but informative
- Use markdown for formatting when helpful
- Suggest next steps when appropriate
"""


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
