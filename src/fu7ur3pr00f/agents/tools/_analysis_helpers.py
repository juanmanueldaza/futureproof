"""DRY helpers for LLM-based analysis tools.

Consolidates repeated patterns from analyze_skill_gaps, analyze_career_alignment,
get_career_advice, analyze_market_fit, and analyze_market_skills.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from langchain_core.messages import HumanMessage

from fu7ur3pr00f.agents.tools._async import run_async
from fu7ur3pr00f.llm.fallback import get_model_with_fallback
from fu7ur3pr00f.memory.profile import UserProfile, load_profile
from fu7ur3pr00f.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)


@dataclass
class ToolContext:
    """Encapsulates dependencies for tool execution.

    Provides a single point of access to profile and knowledge service,
    eliminating repeated instantiation across tools.

    Usage:
        ctx = ToolContext.create()
        career_data = ctx.knowledge_service.search(...)
        profile_summary = ctx.profile.summary()
    """

    profile: UserProfile
    knowledge_service: KnowledgeService

    @classmethod
    def create(cls) -> "ToolContext":
        """Factory method — handles all service initialization."""
        return cls(
            profile=load_profile(),
            knowledge_service=KnowledgeService(),
        )


def build_career_context(career_data: list[dict]) -> str:
    """Format knowledge search results for prompt injection.

    Args:
        career_data: List of dicts with 'content' key from KnowledgeService.search()

    Returns:
        Formatted context string, or "No career data available." if empty
    """
    return (
        "\n".join(f"- {r['content']}" for r in career_data)
        if career_data
        else "No career data available."
    )


def invoke_with_context(
    search_query: str,
    prompt: str,
    search_limit: int = 10,
    ctx: ToolContext | None = None,
) -> str:
    """Run the shared profile+knowledge+LLM pipeline.

    Eliminates duplication across analyze_skill_gaps, analyze_career_alignment,
    get_career_advice, analyze_market_fit, and analyze_market_skills.

    Args:
        search_query: Knowledge base search query
        prompt: Fully rendered prompt string with {profile_summary} and
                {career_context} format placeholders
        search_limit: Max knowledge results to retrieve (default 10)
        ctx: Optional pre-created ToolContext for efficiency

    Returns:
        Model text response (result.content)

    Raises:
        Exception: Propagates any LLM or service errors for caller to handle
    """
    if ctx is None:
        ctx = ToolContext.create()

    career_data = ctx.knowledge_service.search(search_query, limit=search_limit)
    career_context = build_career_context(career_data)

    full_prompt = prompt.format(
        profile_summary=ctx.profile.summary(),
        career_context=career_context,
    )

    model, _ = get_model_with_fallback(purpose="analysis")
    result = model.invoke([HumanMessage(content=full_prompt)])
    return result.content  # type: ignore


def fetch_tech_list() -> str:
    """Fetch top 8 hiring technologies from TechTrendsGatherer.

    Used by analyze_market_fit and analyze_market_skills to inject
    current market demand context into their prompts.

    Returns:
        Comma-separated string of top 8 technologies (e.g., "Python, Go, Rust, ...")

    Raises:
        Exception: Propagates any gatherer or async errors
    """
    from fu7ur3pr00f.gatherers.market.tech_trends_gatherer import TechTrendsGatherer

    gatherer = TechTrendsGatherer()
    market_data = run_async(gatherer.gather_with_cache())
    trends = market_data.get("hiring_trends", {})
    tech_list = ", ".join(t[0] for t in trends.get("top_technologies", [])[:8])
    return tech_list


def run_market_analysis(
    search_query: str,
    prompt_fn: Callable[[str], str],
    noun: str,
) -> str:
    """Shared driver for market analysis tools.

    Args:
        search_query: Knowledge base search query
        prompt_fn: Callable that takes tech_list str and returns full prompt
                   (prompt may still contain {profile_summary}/{career_context}
                   placeholders for invoke_with_context)
        noun: Display name for success/error messages

    Returns:
        Formatted analysis result or error message
    """
    try:
        tech_list = fetch_tech_list()
        result = invoke_with_context(search_query, prompt_fn(tech_list))
        return f"{noun}:\n\n{result}"
    except Exception as e:
        return (
            f"Could not complete {noun.lower()}: "
            f"{type(e).__name__}. Check logs for details."
        )


def get_knowledge_service() -> KnowledgeService:
    """Get a KnowledgeService instance.

    Convenience wrapper that eliminates repeated imports and instantiation.
    Use this in tools that only need knowledge service access.

    Returns:
        KnowledgeService instance
    """
    return KnowledgeService()


def get_profile_summary() -> str:
    """Get the current user's profile summary.

    Convenience wrapper for tools that need profile context.

    Returns:
        Profile summary string
    """
    return load_profile().summary()
