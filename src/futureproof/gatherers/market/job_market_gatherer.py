"""Job market gatherer using multiple sources.

Collects job listings and salary data to understand
current market demands and compensation ranges.

OCP-compliant: Sources are defined in source_registry.py.
Adding a new source requires only adding an entry to JOB_SOURCE_REGISTRY.

Sources:
- JobSpy: LinkedIn, Indeed, Glassdoor, ZipRecruiter
- RemoteOK: Remote-focused job board
- Himalayas: Remote jobs with salary data
- Jobicy: Remote jobs worldwide (with RSS salary data)
- WeWorkRemotely: RSS-based remote jobs with salary extraction
- Remotive: Remote jobs API with tags and location
- Tavily: Salary research via web search
"""

import logging
from typing import Any

from ...config import settings
from .base import MarketGatherer
from .source_registry import JOB_SOURCE_REGISTRY, SALARY_SOURCE

logger = logging.getLogger(__name__)


class JobMarketGatherer(MarketGatherer):
    """Gather job market data from multiple sources.

    Collects:
    - Job listings from LinkedIn, Indeed, Glassdoor, ZipRecruiter (via JobSpy)
    - Remote jobs from RemoteOK, Himalayas, Jobicy
    - Salary data from web search (via Tavily)

    Cache TTL: 12 hours (job market changes more frequently)
    """

    cache_ttl_hours = settings.job_cache_hours

    def _get_cache_key(self, **kwargs: Any) -> str:
        """Generate cache key based on role and location."""
        role = kwargs.get("role", "developer")
        location = kwargs.get("location", "remote")
        return f"job_market_{role}_{location}".lower().replace(" ", "_")

    async def gather(self, **kwargs: Any) -> dict[str, Any]:
        """Gather job market data.

        OCP-compliant: iterates over JOB_SOURCE_REGISTRY instead of hardcoded blocks.
        Adding a new source requires only adding an entry to source_registry.py.

        Args:
            role: Job role to search for (e.g., "Python Developer")
            location: Location to search in (e.g., "Berlin", "Remote")
            include_salary: Whether to search for salary data
            limit: Maximum results per source (default 30)

        Returns:
            Dictionary with job market data
        """
        role = kwargs.get("role", "Software Developer")
        location = kwargs.get("location", "Remote")
        include_salary = kwargs.get("include_salary", True)
        limit = kwargs.get("limit", 30)

        results: dict[str, Any] = {
            "role": role,
            "location": location,
            "job_listings": [],
            "salary_data": [],
            "summary": {"total_jobs": 0, "sources": [], "remote_positions": 0},
            "errors": [],
        }

        logger.info(f"Gathering job market data for '{role}' in '{location}'")

        # Iterate over configured sources (OCP: no modification needed to add sources)
        for source_config in JOB_SOURCE_REGISTRY:
            if not source_config.enabled:
                continue

            # Build tool args using source-specific builder
            tool_args = source_config.build_tool_args(role, location, limit)

            jobs = await self._gather_from_source(
                source_name=source_config.source_name,
                tool_name=source_config.tool_name,
                tool_args=tool_args,
                results=results,
                source_label=source_config.source_label,
            )

            if jobs:
                # Apply post-processor if defined
                if source_config.post_process:
                    jobs = source_config.post_process(jobs)

                results["job_listings"].extend(jobs)

                results["summary"]["sources"].append(source_config.source_name)

        # Update summary stats
        results["summary"]["total_jobs"] = len(results["job_listings"])
        results["summary"]["remote_positions"] = sum(
            1
            for j in results["job_listings"]
            if "remote" in str(j.get("location", "")).lower() or j.get("is_remote", False)
        )

        # Gather salary data (special handling for different response format)
        if include_salary:
            salary_args = SALARY_SOURCE.build_tool_args(role, location, limit)
            salary_results = await self._gather_from_source(
                source_name=SALARY_SOURCE.source_name,
                tool_name=SALARY_SOURCE.tool_name,
                tool_args=salary_args,
                results=results,
                extractor=lambda p: p.get("results", []),
                source_label=SALARY_SOURCE.source_label,
            )
            if salary_results:
                results["salary_data"] = salary_results

        return results

