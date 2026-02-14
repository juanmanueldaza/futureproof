"""Jobicy MCP client for remote job listings.

Uses the free Jobicy API and RSS feed (no auth required).
https://jobicy.com/ - Remote jobs with detailed information.

The RSS feed provides salary data that the API doesn't include.
"""

import xml.etree.ElementTree as ET
from typing import Any

from .base import MCPToolResult
from .http_client import HTTPMCPClient
from .job_schema import clean_html_entities
from .salary_parser import parse_salary


class JobicyMCPClient(HTTPMCPClient):
    """Jobicy MCP client for remote jobs.

    Free API and RSS feed, no authentication required.
    Returns remote job listings from jobicy.com.

    Uses RSS feed to get salary data that the JSON API doesn't provide.
    """

    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"
    RSS_URL = "https://jobicy.com/feed/newjobs"
    DEFAULT_HEADERS = {
        "User-Agent": "FutureProof Career Intelligence/1.0",
        "Accept": "application/json, application/rss+xml",
    }

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return ["search_remote_jobs"]

    async def _tool_search_remote_jobs(self, args: dict[str, Any]) -> MCPToolResult:
        """Search remote job listings."""
        return await self._search_jobs(
            count=args.get("count", 50),
            geo=args.get("geo"),
            industry=args.get("industry"),
            tag=args.get("tag"),
        )

    async def _fetch_rss_salary_data(self) -> dict[str, dict[str, Any]]:
        """Fetch salary data from RSS feed.

        The RSS feed has <salary> tags that the API doesn't provide.

        Returns:
            Dict mapping job ID to salary data
        """
        client = self._ensure_client()

        try:
            response = await client.get(self.RSS_URL)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            salary_map: dict[str, dict[str, Any]] = {}

            for job in root.findall(".//job"):
                job_id = job.get("id", "")
                if not job_id:
                    continue

                salary_raw = job.findtext("salary", "")
                if salary_raw:
                    # Clean CDATA wrapper if present
                    salary_raw = salary_raw.strip()
                    salary_data = parse_salary(salary_raw)

                    if salary_data:
                        salary_map[job_id] = {
                            "salary_min": salary_data.min_amount,
                            "salary_max": salary_data.max_amount,
                            "salary_currency": salary_data.currency,
                            "salary_period": salary_data.period,
                            "salary_raw": salary_data.raw,
                        }
                    else:
                        # Keep raw value even if parsing failed
                        salary_map[job_id] = {"salary_raw": salary_raw}

            return salary_map
        except Exception:
            # RSS fetch is supplementary, don't fail if it errors
            return {}

    async def _search_jobs(
        self,
        count: int = 50,
        geo: str | None = None,
        industry: str | None = None,
        tag: str | None = None,
    ) -> MCPToolResult:
        """Fetch remote job listings from Jobicy.

        Args:
            count: Number of jobs to return (max 50)
            geo: Filter by geography (e.g., "usa", "europe")
            industry: Filter by industry
            tag: Filter by tag/keyword

        Returns:
            MCPToolResult with job listings
        """
        client = self._ensure_client()

        # Fetch salary data from RSS in parallel conceptually
        # (we'll await it before merging)
        salary_map = await self._fetch_rss_salary_data()

        params: dict[str, Any] = {
            "count": min(count, 50),
        }
        if geo:
            params["geo"] = geo
        if industry:
            params["industry"] = industry
        if tag:
            params["tag"] = tag

        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        jobs_raw = data.get("jobs", [])

        # Clean up and normalize results
        jobs = []
        for job in jobs_raw:
            job_id = str(job.get("id", ""))

            # Clean HTML entities from title
            title = clean_html_entities(job.get("jobTitle", ""))

            job_entry: dict[str, Any] = {
                "id": job_id,
                "title": title,
                "company": job.get("companyName", ""),
                "company_logo": job.get("companyLogo", ""),
                "location": job.get("jobGeo", "Remote"),
                "seniority": job.get("jobLevel"),
                "categories": job.get("jobIndustry", []),
                "employment_type": job.get("jobType", []),
                "description": (job.get("jobExcerpt", "") or "")[:500],
                "url": job.get("url", ""),
                "date_posted": job.get("pubDate", ""),
                "site": "jobicy",
            }

            # Merge salary data from RSS if available
            if job_id in salary_map:
                job_entry.update(salary_map[job_id])

            jobs.append(job_entry)

        # Count jobs with salary data
        with_salary = sum(1 for j in jobs if j.get("salary_min") or j.get("salary_raw"))

        output = {
            "source": "jobicy",
            "total_returned": len(jobs),
            "with_salary": with_salary,
            "jobs": jobs,
        }

        return self._format_response(output, data, "search_remote_jobs")
