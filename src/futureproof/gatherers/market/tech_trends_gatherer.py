"""Tech trends gatherer using Hacker News MCP.

Collects trending technology discussions and hiring patterns
from Hacker News to understand market demands.
"""

import logging
from typing import Any

from ...config import settings
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

    cache_ttl_hours = settings.market_cache_hours

    def _get_cache_key(self, **kwargs: Any) -> str:
        """Generate cache key based on topic."""
        topic = kwargs.get("topic", "general")
        return f"tech_trends_{topic}"

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
            "hn_job_postings": [],
            "errors": [],
        }

        logger.info(f"Gathering tech trends from Hacker News (topic: {topic or 'general'})")

        if not MCPClientFactory.is_available("hn"):
            logger.warning("Hacker News MCP not available")
            results["errors"].append("Hacker News MCP not available")
            return results

        try:
            client = MCPClientFactory.create("hn")
            async with client:
                # Get trending stories
                if topic:
                    logger.info(f"HN: Searching for stories about '{topic}'...")
                    stories_result = await client.call_tool(
                        "search_hn",
                        {"query": topic},
                    )
                else:
                    logger.info("HN: Fetching front page stories...")
                    stories_result = await client.call_tool(
                        "get_top_stories",
                        {"limit": 30},
                    )

                if not stories_result.is_error:
                    stories = self._parse_mcp_content(stories_result.content, "[]")
                    # Extract list from wrapped response (e.g. {"results": [...]})
                    if isinstance(stories, dict):
                        stories = stories.get("results", stories.get("hits", []))
                    results["trending_stories"] = stories
                    logger.info(f"HN: Retrieved {len(stories)} trending stories")
                else:
                    logger.warning(f"HN stories: {stories_result.error_message}")
                    results["errors"].append(f"Stories: {stories_result.error_message}")

                # Get hiring trends (analyze_tech_trends provides richer data)
                logger.info("HN: Analyzing 'Who is Hiring?' threads (this may take a moment)...")
                hiring_result = await client.call_tool(
                    "analyze_tech_trends",
                    {"months": 3},
                )

                if not hiring_result.is_error:
                    hiring = self._parse_mcp_content(hiring_result.content)
                    results["hiring_trends"] = hiring
                    total_jobs = hiring.get("total_job_postings", 0)
                    threads = hiring.get("threads_analyzed", 0)
                    logger.info(f"HN: Analyzed {threads} hiring threads ({total_jobs} job posts)")
                else:
                    logger.warning(f"HN hiring trends: {hiring_result.error_message}")
                    results["errors"].append(f"Hiring: {hiring_result.error_message}")

                # Extract structured job postings from hiring threads
                logger.info("HN: Extracting structured job postings...")
                jobs_result = await client.call_tool(
                    "extract_job_postings",
                    {"months": 1, "limit": 50},
                )

                if not jobs_result.is_error:
                    jobs_data = self._parse_mcp_content(jobs_result.content)
                    results["hn_job_postings"] = jobs_data.get("postings", [])

                    # Log stats
                    postings = results["hn_job_postings"]
                    with_salary = sum(1 for p in postings if p.get("salary_min"))
                    remote_count = sum(1 for p in postings if p.get("remote"))
                    logger.info(
                        f"HN: Extracted {len(postings)} job postings "
                        f"({with_salary} with salary, {remote_count} remote)"
                    )
                else:
                    logger.warning(f"HN job extraction: {jobs_result.error_message}")
                    results["errors"].append(f"Job extraction: {jobs_result.error_message}")

        except Exception as e:
            logger.exception("Error gathering tech trends")
            results["errors"].append(str(e))

        return results

