"""Job market gatherer using JobSpy and Brave MCP.

Collects job listings and salary data to understand
current market demands and compensation ranges.
"""

import logging
from typing import Any

from ...mcp.factory import MCPClientFactory
from .base import MarketGatherer

logger = logging.getLogger(__name__)


class JobMarketGatherer(MarketGatherer):
    """Gather job market data from multiple sources.

    Collects:
    - Job listings from LinkedIn, Indeed, Glassdoor, ZipRecruiter (via JobSpy)
    - Salary data from web search (via Brave)

    Cache TTL: 12 hours (job market changes more frequently)
    """

    def _get_cache_key(self, **kwargs: Any) -> str:
        """Generate cache key based on role and location."""
        role = kwargs.get("role", "developer")
        location = kwargs.get("location", "remote")
        return f"job_market_{role}_{location}".lower().replace(" ", "_")

    def _get_cache_ttl_hours(self) -> int:
        """Job market data cached for 12 hours."""
        from ...config import settings

        return settings.job_cache_hours

    async def gather(self, **kwargs: Any) -> dict[str, Any]:
        """Gather job market data.

        Args:
            role: Job role to search for (e.g., "Python Developer")
            location: Location to search in (e.g., "Berlin", "Remote")
            include_salary: Whether to search for salary data

        Returns:
            Dictionary with job market data
        """
        role = kwargs.get("role", "Software Developer")
        location = kwargs.get("location", "Remote")
        include_salary = kwargs.get("include_salary", True)

        results: dict[str, Any] = {
            "role": role,
            "location": location,
            "job_listings": [],
            "salary_data": [],
            "summary": {},
            "errors": [],
        }

        # Gather from JobSpy
        if MCPClientFactory.is_available("jobspy"):
            try:
                client = MCPClientFactory.create("jobspy")
                jobs_result = await client.call_tool(
                    "search_jobs",
                    {
                        "search_term": role,
                        "location": location,
                        "results_wanted": 30,
                    },
                )

                if not jobs_result.is_error:
                    jobs = jobs_result.content or []
                    results["job_listings"] = jobs

                    # Calculate summary stats
                    results["summary"]["total_jobs"] = len(jobs)
                    results["summary"]["sources"] = list({j.get("source", "unknown") for j in jobs})

                    # Count remote positions
                    remote_count = sum(
                        1
                        for j in jobs
                        if "remote" in j.get("location", "").lower() or j.get("is_remote", False)
                    )
                    results["summary"]["remote_positions"] = remote_count
                else:
                    results["errors"].append(f"JobSpy: {jobs_result.error_message}")

            except Exception as e:
                logger.exception("Error gathering from JobSpy")
                results["errors"].append(f"JobSpy error: {e}")
        else:
            results["errors"].append("JobSpy MCP not available")

        # Gather salary data from Brave
        if include_salary and MCPClientFactory.is_available("brave"):
            try:
                client = MCPClientFactory.create("brave")
                salary_result = await client.call_tool(
                    "web_search",
                    {
                        "query": f"{role} salary {location} 2024 2025",
                        "count": 8,
                    },
                )

                if not salary_result.is_error:
                    results["salary_data"] = salary_result.content or []
                else:
                    results["errors"].append(f"Brave: {salary_result.error_message}")

            except Exception as e:
                logger.exception("Error gathering salary data")
                results["errors"].append(f"Brave error: {e}")

        return results

    def to_markdown(self, data: dict[str, Any]) -> str:
        """Convert gathered data to markdown format.

        Args:
            data: Gathered job market data

        Returns:
            Markdown formatted string
        """
        lines = ["# Job Market Report\n"]

        role = data.get("role", "Unknown")
        location = data.get("location", "Unknown")
        lines.append(f"**Role:** {role}")
        lines.append(f"**Location:** {location}\n")

        # Summary
        summary = data.get("summary", {})
        if summary:
            lines.append("## Summary\n")
            lines.append(f"- **Total listings found:** {summary.get('total_jobs', 0)}")
            lines.append(f"- **Remote positions:** {summary.get('remote_positions', 0)}")
            if summary.get("sources"):
                lines.append(f"- **Sources:** {', '.join(summary['sources'])}")
            lines.append("")

        # Job listings
        jobs = data.get("job_listings", [])
        if jobs:
            lines.append("## Job Listings\n")
            for job in jobs[:20]:  # Limit display
                title = job.get("title", "Unknown Title")
                company = job.get("company", "Unknown Company")
                job_location = job.get("location", location)
                salary = job.get("salary", "")

                lines.append(f"### {title}")
                lines.append(f"**Company:** {company}")
                lines.append(f"**Location:** {job_location}")
                if salary:
                    lines.append(f"**Salary:** {salary}")

                desc = job.get("description", "")
                if desc:
                    # Truncate long descriptions
                    desc = desc[:400] + "..." if len(desc) > 400 else desc
                    lines.append(f"\n{desc}")
                lines.append("")

        # Salary data
        salary_data = data.get("salary_data", [])
        if salary_data:
            lines.append("## Salary Information\n")
            for item in salary_data[:6]:
                title = item.get("title", "")
                snippet = item.get("description", item.get("snippet", ""))
                if title:
                    lines.append(f"### {title}")
                if snippet:
                    lines.append(snippet)
                lines.append("")

        # Errors
        errors = data.get("errors", [])
        if errors:
            lines.append("## Data Collection Notes\n")
            for error in errors:
                lines.append(f"- {error}")

        return "\n".join(lines)
