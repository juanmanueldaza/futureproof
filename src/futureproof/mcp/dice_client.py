"""Dice MCP client for tech job search.

Uses the official Dice MCP endpoint (no auth required).
https://mcp.dice.com/mcp - Tech-focused job database.
"""

import json
from typing import Any

import httpx

from .base import MCPToolError, MCPToolResult
from .http_client import HTTPMCPClient


class DiceMCPClient(HTTPMCPClient):
    """Dice MCP client for tech jobs.

    Free to use, no authentication required.
    Provides access to Dice's tech-focused job database.
    """

    # Dice MCP endpoint
    BASE_URL = "https://mcp.dice.com/mcp"
    DEFAULT_HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "FutureProof/1.0 (Career Intelligence Tool)",
    }

    def __init__(self) -> None:
        super().__init__()

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return ["search_tech_jobs"]

    async def _tool_search_tech_jobs(self, args: dict[str, Any]) -> MCPToolResult:
        """Search tech job listings."""
        return await self._search_jobs(
            query=args.get("query", ""),
            location=args.get("location", ""),
            remote=args.get("remote", False),
            limit=args.get("limit", 25),
        )

    async def _search_jobs(
        self,
        query: str,
        location: str = "",
        remote: bool = False,
        limit: int = 25,
    ) -> MCPToolResult:
        """Search for tech jobs on Dice.

        Args:
            query: Job title or keywords (e.g., "AI Engineer", "Python Developer")
            location: Location filter (e.g., "New York", "Remote")
            remote: Filter for remote jobs only
            limit: Max number of results

        Returns:
            MCPToolResult with job listings
        """
        client = self._ensure_client()

        # Build MCP request following JSON-RPC format
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_jobs",
                "arguments": {
                    "query": query,
                    "location": location if location else None,
                    "workplaceType": "Remote" if remote else None,
                    "pageSize": limit,
                },
            },
        }

        # Remove None values
        mcp_request["params"]["arguments"] = {
            k: v for k, v in mcp_request["params"]["arguments"].items() if v is not None
        }

        try:
            response = await client.post(self.BASE_URL, json=mcp_request)
            response.raise_for_status()
            data = response.json()

            # Parse MCP response
            if "error" in data:
                raise MCPToolError(f"Dice MCP error: {data['error']}")

            result = data.get("result", {})
            content = result.get("content", [])

            # Extract jobs from response
            jobs = []
            if content and isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        try:
                            job_data = json.loads(item.get("text", "{}"))
                            if isinstance(job_data, list):
                                jobs.extend(job_data)
                            elif isinstance(job_data, dict) and "jobs" in job_data:
                                jobs.extend(job_data["jobs"])
                        except json.JSONDecodeError:
                            pass

            # Clean up results
            cleaned_jobs = []
            for job in jobs[:limit]:
                cleaned_jobs.append(
                    {
                        "title": job.get("title", job.get("jobTitle", "")),
                        "company": job.get("company", job.get("companyName", "")),
                        "location": job.get("location", ""),
                        "salary": job.get("salary", job.get("salaryRange", "")),
                        "url": job.get("url", job.get("jobUrl", "")),
                        "posted": job.get("postedDate", job.get("datePosted", "")),
                        "employment_type": job.get("employmentType", ""),
                    }
                )

            output = {
                "source": "dice",
                "query": query,
                "total_results": len(cleaned_jobs),
                "jobs": cleaned_jobs,
            }

            return self._format_response(output, data, "search_tech_jobs")

        except httpx.HTTPStatusError as e:
            raise MCPToolError(f"Dice API error: {e.response.status_code}") from e
