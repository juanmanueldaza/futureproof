"""JobSpy MCP client for multi-platform job search.

Uses JobSpy to aggregate jobs from LinkedIn, Indeed, Glassdoor, ZipRecruiter.
MIT licensed, no authentication required.
"""

import hashlib
import json
from typing import Any

from .base import MCPClient, MCPToolError, MCPToolResult


class JobSpyMCPClient(MCPClient):
    """JobSpy MCP client for aggregated job search.

    This client uses the python-jobspy library directly rather than
    spawning an MCP server process. This is simpler and more reliable.

    Supported sites: LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs
    """

    SUPPORTED_SITES = ["linkedin", "indeed", "glassdoor", "zip_recruiter", "google"]

    def __init__(self) -> None:
        self._connected = False
        self._jobspy_available = False

    async def connect(self) -> None:
        """Check if jobspy is available."""
        try:
            # Try to import jobspy (optional dependency)
            import jobspy  # type: ignore[import-not-found]  # noqa: F401

            self._jobspy_available = True
            self._connected = True
        except ImportError:
            # JobSpy not installed - we'll return helpful error
            self._jobspy_available = False
            self._connected = True  # Still "connected" but limited

    async def disconnect(self) -> None:
        """No cleanup needed."""
        self._connected = False

    def is_connected(self) -> bool:
        """Check if client is ready."""
        return self._connected

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return [
            "search_jobs",
            "search_jobs_multi_site",
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call a job search tool."""
        if not self.is_connected():
            raise MCPToolError("Client not connected")

        if not self._jobspy_available:
            return MCPToolResult(
                content=json.dumps(
                    {
                        "error": "JobSpy not installed. Install with: pip install python-jobspy",
                        "fallback": "Use Brave Search for job data instead",
                    }
                ),
                tool_name=tool_name,
                is_error=True,
            )

        try:
            if tool_name == "search_jobs":
                return await self._search_jobs(
                    search_term=arguments.get("search_term", ""),
                    location=arguments.get("location", ""),
                    site_names=arguments.get("sites", ["linkedin", "indeed"]),
                    results_wanted=arguments.get("results_wanted", 20),
                    remote=arguments.get("remote", False),
                )
            elif tool_name == "search_jobs_multi_site":
                return await self._search_jobs(
                    search_term=arguments.get("search_term", ""),
                    location=arguments.get("location", ""),
                    site_names=self.SUPPORTED_SITES,
                    results_wanted=arguments.get("results_wanted", 50),
                    remote=arguments.get("remote", False),
                )
            else:
                raise MCPToolError(f"Unknown tool: {tool_name}")
        except MCPToolError:
            raise
        except Exception as e:
            raise MCPToolError(f"Tool call failed: {e}") from e

    async def _search_jobs(
        self,
        search_term: str,
        location: str = "",
        site_names: list[str] | None = None,
        results_wanted: int = 20,
        remote: bool = False,
    ) -> MCPToolResult:
        """Search for jobs across multiple platforms."""
        if not self._jobspy_available:
            raise MCPToolError("JobSpy not available")

        from jobspy import scrape_jobs  # type: ignore[import-not-found]

        sites = site_names or ["linkedin", "indeed"]

        # Build search parameters
        search_params: dict[str, Any] = {
            "site_name": sites,
            "search_term": search_term,
            "results_wanted": results_wanted,
            "country_indeed": "USA",  # Default to USA
        }

        if location:
            search_params["location"] = location

        if remote:
            search_params["is_remote"] = True

        try:
            # Run the synchronous scrape_jobs in a thread
            import asyncio

            loop = asyncio.get_event_loop()
            jobs_df = await loop.run_in_executor(
                None,
                lambda: scrape_jobs(**search_params),
            )

            # Convert DataFrame to list of dicts
            if jobs_df is not None and not jobs_df.empty:
                jobs = jobs_df.to_dict("records")

                # Clean up the results
                cleaned_jobs = []
                for job in jobs:
                    # Handle NaN values from pandas (they come as float)
                    desc = job.get("description")
                    if desc is None or (isinstance(desc, float) and str(desc) == "nan"):
                        desc = ""
                    else:
                        desc = str(desc)[:500]

                    # Generate unique ID from site + job_url
                    job_url = job.get("job_url", "") or ""
                    site = job.get("site", "") or ""
                    unique_str = f"{site}:{job_url}"
                    job_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]

                    cleaned_jobs.append(
                        {
                            "id": job_id,
                            "title": job.get("title", "") or "",
                            "company": job.get("company", "") or "",
                            "location": job.get("location", "") or "",
                            "job_url": job.get("job_url", "") or "",
                            "site": job.get("site", "") or "",
                            "date_posted": str(job.get("date_posted", "") or ""),
                            "salary_min": job.get("min_amount"),
                            "salary_max": job.get("max_amount"),
                            "salary_currency": job.get("currency", "") or "",
                            "description": desc,
                        }
                    )

                return MCPToolResult(
                    content=json.dumps(
                        {
                            "search_term": search_term,
                            "location": location,
                            "sites": sites,
                            "total_results": len(cleaned_jobs),
                            "jobs": cleaned_jobs,
                        },
                        indent=2,
                    ),
                    raw_response=jobs,
                    tool_name="search_jobs",
                )
            else:
                return MCPToolResult(
                    content=json.dumps(
                        {
                            "search_term": search_term,
                            "location": location,
                            "sites": sites,
                            "total_results": 0,
                            "jobs": [],
                        },
                        indent=2,
                    ),
                    tool_name="search_jobs",
                )

        except Exception as e:
            raise MCPToolError(f"Job search failed: {e}") from e

    # Convenience methods for direct use
    async def search_tech_jobs(
        self,
        role: str,
        location: str = "",
        remote: bool = False,
        results_wanted: int = 30,
    ) -> list[dict[str, Any]]:
        """Search for tech jobs across all platforms (convenience method)."""
        result = await self.call_tool(
            "search_jobs_multi_site",
            {
                "search_term": role,
                "location": location,
                "remote": remote,
                "results_wanted": results_wanted,
            },
        )

        if result.is_error:
            return []

        data = json.loads(result.content)
        return data.get("jobs", [])

    async def search_with_salary(
        self,
        role: str,
        location: str = "",
        min_salary: int = 0,
    ) -> list[dict[str, Any]]:
        """Search for jobs and filter by minimum salary."""
        jobs = await self.search_tech_jobs(role, location, results_wanted=50)

        if min_salary <= 0:
            return jobs

        # Filter by salary
        filtered = []
        for job in jobs:
            salary_min = job.get("salary_min")
            if salary_min and salary_min >= min_salary:
                filtered.append(job)

        return filtered
