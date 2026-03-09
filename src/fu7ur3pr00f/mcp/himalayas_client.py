"""Himalayas MCP client for remote job listings with salary data.

Uses the free Himalayas API (no auth required).
https://himalayas.app/ - 100K+ remote job listings with salary information.
"""

from datetime import UTC, datetime
from typing import Any

from .base import MCPToolResult
from .http_client import HTTPMCPClient


class HimalayasMCPClient(HTTPMCPClient):
    """Himalayas MCP client for remote jobs.

    Free API, no authentication required.
    Returns remote job listings with salary data from himalayas.app.
    """

    BASE_URL = "https://himalayas.app/jobs/api"

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return ["search_jobs", "get_job_categories"]

    async def _tool_search_jobs(self, args: dict[str, Any]) -> MCPToolResult:
        """Search job listings."""
        return await self._search_jobs(
            limit=args.get("limit", 50),
            offset=args.get("offset", 0),
        )

    async def _tool_get_job_categories(self, args: dict[str, Any]) -> MCPToolResult:
        """Get available job categories."""
        return await self._get_categories()

    async def _search_jobs(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> MCPToolResult:
        """Fetch remote job listings from Himalayas.

        Args:
            limit: Max number of jobs to return (max 100)
            offset: Pagination offset

        Returns:
            MCPToolResult with job listings
        """
        client = self._ensure_client()

        params = {
            "limit": min(limit, 100),
            "offset": offset,
        }

        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        jobs_raw = data.get("jobs", [])

        # Clean up and normalize results
        jobs = []
        for job in jobs_raw:
            # Build salary string if available
            salary = None
            min_sal = job.get("minSalary")
            max_sal = job.get("maxSalary")
            currency = job.get("currency", "USD")
            if min_sal and max_sal:
                salary = f"{currency} {min_sal:,} - {max_sal:,}"
            elif min_sal:
                salary = f"{currency} {min_sal:,}+"
            elif max_sal:
                salary = f"Up to {currency} {max_sal:,}"

            # Convert timezone restrictions to readable format
            tz_raw = job.get("timezoneRestrictions", [])
            tz_readable = self._format_timezones(tz_raw) if tz_raw else None

            # Convert expiry timestamp
            expiry_ts = job.get("expiryDate")
            expiry_date = None
            if expiry_ts:
                try:
                    expiry_date = datetime.fromtimestamp(expiry_ts, tz=UTC).isoformat()
                except (ValueError, OSError):
                    pass

            jobs.append(
                {
                    "id": job.get("guid", ""),  # For deduplication
                    "title": job.get("title", ""),
                    "company": job.get("companyName", ""),
                    "company_logo": job.get("companyLogo", ""),
                    "location": ", ".join(job.get("locationRestrictions", [])) or "Worldwide",
                    "timezone_restrictions": tz_readable,
                    "timezone_raw": tz_raw,
                    "seniority": ", ".join(job.get("seniority", []))
                    if job.get("seniority")
                    else None,
                    "categories": job.get("categories", []),
                    "parent_categories": job.get("parentCategories", []),
                    "employment_type": job.get("employmentType", ""),
                    "salary": salary,
                    "salary_min": min_sal,
                    "salary_max": max_sal,
                    "currency": currency,
                    "description": (job.get("excerpt", "") or job.get("description", "") or "")[
                        :500
                    ],
                    "url": job.get("applicationLink", ""),
                    "date_posted": job.get("pubDate", ""),
                    "expiry_date": expiry_date,
                    "site": "himalayas",
                }
            )

        output = {
            "source": "himalayas",
            "total_available": data.get("totalCount", 0),
            "returned": len(jobs),
            "jobs": jobs,
        }

        return self._format_response(output, data, "search_jobs")

    def _format_timezones(self, tz_offsets: list[int]) -> str:
        """Format timezone offsets into readable string.

        Args:
            tz_offsets: List of UTC offsets (e.g., [3] = GMT+3, [-5] = GMT-5)

        Returns:
            Human-readable timezone string
        """
        if not tz_offsets:
            return "Any timezone"

        formatted = []
        for offset in tz_offsets:
            if offset >= 0:
                formatted.append(f"UTC+{offset}")
            else:
                formatted.append(f"UTC{offset}")

        return ", ".join(formatted)

    async def _get_categories(self) -> MCPToolResult:
        """Get available job categories from a sample of jobs."""
        client = self._ensure_client()

        # Fetch a sample to extract categories
        params = {"limit": 100}
        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        jobs = data.get("jobs", [])

        # Extract unique categories
        categories: set[str] = set()
        for job in jobs:
            for cat in job.get("categories", []):
                categories.add(cat)

        output = {
            "categories": sorted(categories),
            "total": len(categories),
        }

        return self._format_response(output, output, "get_job_categories")
