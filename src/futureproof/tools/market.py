"""Market intelligence tools for LLM tool calling.

These tools wrap MCP clients and can be bound to LLMs for dynamic
data retrieval during analysis. When the LLM determines it needs
more market data, it can invoke these tools.

Usage:
    from langchain_core.tools import tool
    from futureproof.tools.market import search_jobs, get_tech_trends

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools([search_jobs, get_tech_trends])

    # LLM can now call these tools during analysis
    response = llm_with_tools.invoke("What Python jobs are available in Berlin?")
"""

import asyncio
import logging
from typing import Any

from langchain_core.tools import tool

from ..config import settings
from ..mcp.factory import MCPClientFactory

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Run async coroutine in sync context."""
    try:
        asyncio.get_running_loop()
        # If we're already in an async context, run in thread pool
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(coro)


@tool
def search_jobs(
    role: str,
    location: str = "Remote",
    remote_only: bool = False,
) -> str:
    """Search for job listings across multiple platforms.

    Use this tool when you need current job market data for a specific role
    or location. Returns job listings from LinkedIn, Indeed, Glassdoor, and
    ZipRecruiter.

    Args:
        role: Job title or role to search for (e.g., "Python Developer", "DevOps Engineer")
        location: Geographic location (e.g., "Berlin", "San Francisco", "Remote")
        remote_only: If True, only return remote positions

    Returns:
        Formatted job listings with titles, companies, locations, and descriptions
    """
    if not MCPClientFactory.is_available("jobspy"):
        return "JobSpy is not available. Enable it in configuration."

    try:
        client = MCPClientFactory.create("jobspy")
        result = _run_async(
            client.call_tool(
                "search_jobs",
                {
                    "search_term": role,
                    "location": location,
                    "results_wanted": 20,
                    "country_indeed": "USA" if "US" in location.upper() else "Germany",
                },
            )
        )

        if result.is_error:
            return f"Error searching jobs: {result.error_message}"

        jobs = result.content
        if not jobs:
            return f"No jobs found for '{role}' in '{location}'"

        # Format job results
        output_lines = [f"## Job Listings: {role} in {location}\n"]
        for job in jobs[:15]:  # Limit to 15 results
            output_lines.append(f"### {job.get('title', 'Unknown Title')}")
            output_lines.append(f"**Company:** {job.get('company', 'Unknown')}")
            output_lines.append(f"**Location:** {job.get('location', location)}")
            if job.get("salary"):
                output_lines.append(f"**Salary:** {job['salary']}")
            if job.get("description"):
                desc = (
                    job["description"][:300] + "..."
                    if len(job.get("description", "")) > 300
                    else job.get("description", "")
                )
                output_lines.append(f"**Description:** {desc}")
            output_lines.append("")

        return "\n".join(output_lines)

    except Exception as e:
        logger.exception("Error in search_jobs tool")
        return f"Error searching jobs: {e}"


@tool
def get_tech_trends(topic: str = "programming") -> str:
    """Get current technology trends from Hacker News.

    Use this tool to understand what technologies, frameworks, and topics
    are trending in the developer community. Useful for identifying
    emerging skills and market demands.

    Args:
        topic: Technology topic to search for (e.g., "Python", "Rust", "AI", "DevOps")

    Returns:
        Summary of trending discussions and patterns from Hacker News
    """
    if not MCPClientFactory.is_available("hn"):
        return "Hacker News MCP is not available."

    try:
        client = MCPClientFactory.create("hn")
        result = _run_async(
            client.call_tool(
                "search_stories",
                {
                    "query": topic,
                    "num_results": 30,
                },
            )
        )

        if result.is_error:
            return f"Error fetching trends: {result.error_message}"

        stories = result.content
        if not stories:
            return f"No trending stories found for '{topic}'"

        # Format trend results
        output_lines = [f"## Tech Trends: {topic}\n"]
        output_lines.append(f"Based on {len(stories)} recent Hacker News discussions:\n")

        for story in stories[:15]:
            title = story.get("title", "Unknown")
            points = story.get("points", 0)
            comments = story.get("num_comments", 0)
            output_lines.append(f"- **{title}** ({points} points, {comments} comments)")

        return "\n".join(output_lines)

    except Exception as e:
        logger.exception("Error in get_tech_trends tool")
        return f"Error fetching trends: {e}"


@tool
def search_salary_data(
    role: str,
    location: str = "United States",
) -> str:
    """Search for salary information for a specific role and location.

    Use this tool when you need salary benchmarks or compensation data
    for career advice. Uses Brave Search to find recent salary reports.

    Args:
        role: Job title to search salary for (e.g., "Senior Python Developer")
        location: Geographic location for salary data (e.g., "Germany", "San Francisco")

    Returns:
        Salary information and ranges from various sources
    """
    if not MCPClientFactory.is_available("brave"):
        # Fallback message with general guidance
        return (
            f"Brave Search API not configured. To get salary data for '{role}' in '{location}', "
            "consider checking: Glassdoor, Levels.fyi, LinkedIn Salary Insights, "
            "or PayScale for current market rates."
        )

    try:
        client = MCPClientFactory.create("brave")
        query = f"{role} salary {location} 2024 2025"
        result = _run_async(
            client.call_tool(
                "web_search",
                {
                    "query": query,
                    "count": 10,
                },
            )
        )

        if result.is_error:
            return f"Error searching salary data: {result.error_message}"

        results = result.content
        if not results:
            return f"No salary data found for '{role}' in '{location}'"

        # Format salary search results
        output_lines = [f"## Salary Data: {role} in {location}\n"]
        output_lines.append("Sources found:\n")

        for item in results[:8]:
            title = item.get("title", "Unknown")
            snippet = item.get("description", item.get("snippet", ""))
            url = item.get("url", "")
            output_lines.append(f"### {title}")
            if snippet:
                output_lines.append(snippet)
            if url:
                output_lines.append(f"Source: {url}")
            output_lines.append("")

        return "\n".join(output_lines)

    except Exception as e:
        logger.exception("Error in search_salary_data tool")
        return f"Error searching salary data: {e}"


@tool
def search_hiring_trends(months_back: int = 3) -> str:
    """Get hiring trends from Hacker News "Who is Hiring?" threads.

    Use this tool to understand what technologies and skills companies
    are actively hiring for. Analyzes recent monthly hiring threads.

    Args:
        months_back: How many months of hiring data to analyze (1-6)

    Returns:
        Summary of hiring trends including popular technologies and roles
    """
    if not MCPClientFactory.is_available("hn"):
        return "Hacker News MCP is not available."

    months_back = min(max(months_back, 1), 6)  # Clamp to 1-6

    try:
        client = MCPClientFactory.create("hn")
        result = _run_async(
            client.call_tool(
                "get_hiring_trends",
                {
                    "months": months_back,
                },
            )
        )

        if result.is_error:
            return f"Error fetching hiring trends: {result.error_message}"

        trends = result.content
        if not trends:
            return "No hiring trend data available"

        # Format hiring trends
        output_lines = ["## Hacker News Hiring Trends\n"]
        output_lines.append(
            f"Based on the last {months_back} month(s) of 'Who is Hiring?' threads:\n"
        )

        if isinstance(trends, dict):
            if trends.get("top_technologies"):
                output_lines.append("### Most Requested Technologies")
                for tech, count in trends["top_technologies"][:15]:
                    output_lines.append(f"- {tech}: {count} mentions")
                output_lines.append("")

            if trends.get("top_roles"):
                output_lines.append("### Most Common Roles")
                for role, count in trends["top_roles"][:10]:
                    output_lines.append(f"- {role}: {count} postings")
                output_lines.append("")

            if trends.get("remote_percentage"):
                output_lines.append(
                    f"**Remote-friendly positions:** {trends['remote_percentage']}%"
                )
        else:
            output_lines.append(str(trends))

        return "\n".join(output_lines)

    except Exception as e:
        logger.exception("Error in search_hiring_trends tool")
        return f"Error fetching hiring trends: {e}"


# Collect all tools for easy binding
ALL_MARKET_TOOLS = [
    search_jobs,
    get_tech_trends,
    search_salary_data,
    search_hiring_trends,
]


def get_available_tools() -> list:
    """Get list of tools that are currently available based on configuration.

    Returns:
        List of tool functions that can be used
    """
    available = []

    # JobSpy tools
    if settings.jobspy_enabled:
        available.append(search_jobs)

    # Hacker News tools
    if settings.hn_mcp_enabled:
        available.append(get_tech_trends)
        available.append(search_hiring_trends)

    # Brave Search tools
    if settings.has_brave_mcp:
        available.append(search_salary_data)

    return available
