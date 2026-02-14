"""Remotive MCP client for remote job listings.

Uses the free Remotive API (no auth required).
https://remotive.com/ - remote job board with 20,000+ listings.

API provides structured data including:
- Native job IDs
- Tags array for skills
- candidate_required_location for geography
- salary field (when available)
"""

from typing import Any

from .base import MCPToolResult
from .http_client import HTTPMCPClient
from .job_schema import attach_salary
from .salary_parser import parse_salary


class RemotiveMCPClient(HTTPMCPClient):
    """Remotive MCP client using JSON API.

    Free API, no authentication required.
    Returns remote job listings from remotive.com.
    """

    BASE_URL = "https://remotive.com/api/remote-jobs"

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return ["search_jobs"]

    async def _tool_search_jobs(self, args: dict[str, Any]) -> MCPToolResult:
        """Search job listings."""
        return await self._search_jobs(
            category=args.get("category", "software-dev"),
            limit=args.get("limit", 30),
            search=args.get("search"),
        )

    async def _search_jobs(
        self,
        category: str = "software-dev",
        limit: int = 30,
        search: str | None = None,
    ) -> MCPToolResult:
        """Fetch remote job listings from Remotive API.

        Args:
            category: Job category (software-dev, design, devops, etc.)
            limit: Max number of jobs to return
            search: Optional search query

        Returns:
            MCPToolResult with job listings
        """
        client = self._ensure_client()

        # Build query params
        params: dict[str, Any] = {"limit": limit}
        if category and category != "all":
            params["category"] = category
        if search:
            params["search"] = search

        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()

        # API returns {"jobs": [...], "job-count": N, "0-legal-notice": "..."}
        jobs_raw = data.get("jobs", [])

        jobs = []
        for job_data in jobs_raw[:limit]:
            job = self._parse_job(job_data)
            jobs.append(job)

        output = {
            "source": "remotive",
            "category": category,
            "total_results": len(jobs),
            "api_total": data.get("job-count", len(jobs)),
            "jobs": jobs,
        }

        return self._format_response(output, data, "search_jobs")

    def _parse_job(self, job_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a single job from the API response."""
        # Extract salary from the salary field or description
        salary_raw = job_data.get("salary", "")
        salary_data = parse_salary(salary_raw) if salary_raw else None

        job: dict[str, Any] = {
            "id": str(job_data.get("id", "")),
            "title": job_data.get("title", ""),
            "company": job_data.get("company_name", ""),
            "company_logo": job_data.get("company_logo", ""),
            "url": job_data.get("url", ""),
            "category": job_data.get("category", ""),
            "tags": job_data.get("tags", []),
            "job_type": job_data.get("job_type", ""),  # full_time, part_time, etc.
            "location": job_data.get("candidate_required_location", "Worldwide"),
            "date_posted": job_data.get("publication_date", ""),
            "site": "remotive",
        }

        # Add salary if available
        attach_salary(job, salary_data)
        if not salary_data and salary_raw:
            # Keep raw salary even if parsing failed
            job["salary_raw"] = salary_raw

        return job
