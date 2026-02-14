"""RemoteOK MCP client for remote job listings.

Uses the free RemoteOK API (no auth required).
https://remoteok.com/ - #1 remote jobs board with 30,000+ listings.
"""

from typing import Any

from .base import MCPToolResult
from .http_client import HTTPMCPClient


class RemoteOKMCPClient(HTTPMCPClient):
    """RemoteOK MCP client.

    Free API, no authentication required.
    Returns remote job listings from remoteok.com.
    """

    BASE_URL = "https://remoteok.com/api"
    DEFAULT_HEADERS = {
        "User-Agent": "FutureProof Career Intelligence/1.0",
        "Accept": "application/json",
    }

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return ["search_remote_jobs"]

    async def _tool_search_remote_jobs(self, args: dict[str, Any]) -> MCPToolResult:
        """Search remote job listings."""
        return await self._search_jobs(
            tags=args.get("tags", []),
            limit=args.get("limit", 50),
        )

    async def _search_jobs(
        self,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> MCPToolResult:
        """Fetch remote job listings from RemoteOK.

        Args:
            tags: Filter by tags (e.g., ["python", "ai", "engineer"])
            limit: Max number of jobs to return

        Returns:
            MCPToolResult with job listings
        """
        client = self._ensure_client()

        response = await client.get(self.BASE_URL)
        response.raise_for_status()

        data = response.json()

        # First item is usually metadata, skip it
        jobs_raw = data[1:] if len(data) > 1 else []

        # Filter by tags if specified
        if tags:
            tags_lower = [t.lower() for t in tags]
            filtered = []
            for job in jobs_raw:
                job_tags = [t.lower() for t in job.get("tags", [])]
                if any(
                    tag in job_tags or tag in job.get("position", "").lower() for tag in tags_lower
                ):
                    filtered.append(job)
            jobs_raw = filtered

        # Limit results
        jobs_raw = jobs_raw[:limit]

        # Clean up results
        jobs = []
        for job in jobs_raw:
            jobs.append(
                {
                    "id": job.get("id", ""),  # For deduplication
                    "slug": job.get("slug", ""),  # Alternative unique ID
                    "title": job.get("position", ""),
                    "company": job.get("company", ""),
                    "company_logo": job.get("company_logo") or job.get("logo", ""),
                    "location": job.get("location", "Remote"),
                    "tags": job.get("tags", []),
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "apply_url": job.get("apply_url", ""),
                    "url": job.get("url", ""),
                    "date_posted": job.get("date", ""),
                    "epoch": job.get("epoch"),  # Unix timestamp for sorting
                    "description": (job.get("description", "") or "")[:500],
                }
            )

        output = {
            "source": "remoteok",
            "total_results": len(jobs),
            "jobs": jobs,
        }

        return self._format_response(output, data, "search_remote_jobs")
