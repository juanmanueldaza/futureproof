"""Tech trends gatherer using Hacker News MCP.

Collects trending technology discussions and hiring patterns
from Hacker News to understand market demands.
"""

import logging
from typing import Any

from ...mcp.factory import MCPClientFactory
from .base import MarketGatherer

logger = logging.getLogger(__name__)


class TechTrendsGatherer(MarketGatherer):
    """Gather tech trends from Hacker News.

    Collects:
    - Trending technology discussions
    - "Who is Hiring?" thread analysis
    - Popular programming languages and frameworks

    Cache TTL: 24 hours (trends don't change that fast)
    """

    def _get_cache_key(self, **kwargs: Any) -> str:
        """Generate cache key based on topic."""
        topic = kwargs.get("topic", "general")
        return f"tech_trends_{topic}"

    def _get_cache_ttl_hours(self) -> int:
        """Tech trends cached for 24 hours."""
        from ...config import settings

        return settings.market_cache_hours

    async def gather(self, **kwargs: Any) -> dict[str, Any]:
        """Gather tech trends from Hacker News.

        Args:
            topic: Optional topic to focus on (e.g., "Python", "Rust")

        Returns:
            Dictionary with tech trends data
        """
        topic = kwargs.get("topic", "")
        results: dict[str, Any] = {
            "source": "hacker_news",
            "topic": topic or "general",
            "trending_stories": [],
            "hiring_trends": {},
            "errors": [],
        }

        if not MCPClientFactory.is_available("hn"):
            results["errors"].append("Hacker News MCP not available")
            return results

        try:
            client = MCPClientFactory.create("hn")

            # Get trending stories
            if topic:
                stories_result = await client.call_tool(
                    "search_stories",
                    {"query": topic, "num_results": 30},
                )
            else:
                stories_result = await client.call_tool(
                    "get_top_stories",
                    {"num_stories": 30},
                )

            if not stories_result.is_error:
                results["trending_stories"] = stories_result.content or []
            else:
                results["errors"].append(f"Stories: {stories_result.error_message}")

            # Get hiring trends
            hiring_result = await client.call_tool(
                "get_hiring_trends",
                {"months": 3},
            )

            if not hiring_result.is_error:
                results["hiring_trends"] = hiring_result.content or {}
            else:
                results["errors"].append(f"Hiring: {hiring_result.error_message}")

        except Exception as e:
            logger.exception("Error gathering tech trends")
            results["errors"].append(str(e))

        return results

    def to_markdown(self, data: dict[str, Any]) -> str:
        """Convert gathered data to markdown format.

        Args:
            data: Gathered tech trends data

        Returns:
            Markdown formatted string
        """
        lines = ["# Tech Trends Report\n"]

        topic = data.get("topic", "general")
        if topic != "general":
            lines.append(f"**Focus:** {topic}\n")

        # Trending stories
        stories = data.get("trending_stories", [])
        if stories:
            lines.append("## Trending Discussions\n")
            for story in stories[:15]:
                title = story.get("title", "Unknown")
                points = story.get("points", 0)
                comments = story.get("num_comments", 0)
                lines.append(f"- **{title}** ({points} pts, {comments} comments)")
            lines.append("")

        # Hiring trends
        hiring = data.get("hiring_trends", {})
        if hiring:
            lines.append("## Hiring Trends\n")

            if hiring.get("top_technologies"):
                lines.append("### Most Requested Technologies")
                for tech, count in hiring["top_technologies"][:12]:
                    lines.append(f"- {tech}: {count} mentions")
                lines.append("")

            if hiring.get("top_roles"):
                lines.append("### Most Common Roles")
                for role, count in hiring["top_roles"][:8]:
                    lines.append(f"- {role}: {count} postings")
                lines.append("")

            if hiring.get("remote_percentage"):
                lines.append(f"**Remote-friendly:** {hiring['remote_percentage']}% of positions\n")

        # Errors
        errors = data.get("errors", [])
        if errors:
            lines.append("## Data Collection Notes\n")
            for error in errors:
                lines.append(f"- {error}")

        return "\n".join(lines)
