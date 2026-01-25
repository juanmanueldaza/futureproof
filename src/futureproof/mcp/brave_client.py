"""Brave Search MCP client for job and salary research.

Uses the Brave Search API (2000 free queries/month).
Provides web search, news search, and job-related queries.
"""

import json
from typing import Any

import httpx

from ..config import settings
from .base import MCPClient, MCPConnectionError, MCPToolError, MCPToolResult


class BraveSearchMCPClient(MCPClient):
    """Brave Search MCP client.

    This is a lightweight client that directly calls the Brave Search API
    rather than spawning an external MCP server process.

    Free tier: 2000 queries/month, 1 query/second.
    """

    API_URL = "https://api.search.brave.com/res/v1"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.brave_api_key
        self._connected = False
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Initialize HTTP client."""
        if not self._api_key:
            raise MCPConnectionError("Brave API key not configured. Set BRAVE_API_KEY in .env")

        try:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self._api_key,
                },
            )
            self._connected = True
        except Exception as e:
            raise MCPConnectionError(f"Failed to initialize Brave client: {e}") from e

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
        self._connected = False

    def is_connected(self) -> bool:
        """Check if client is ready."""
        return self._connected and self._client is not None

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return [
            "web_search",
            "news_search",
            "search_jobs",
            "search_salary",
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call a tool on the Brave Search API."""
        if not self.is_connected():
            raise MCPToolError("Client not connected")

        try:
            if tool_name == "web_search":
                return await self._web_search(
                    query=arguments.get("query", ""),
                    count=arguments.get("count", 20),
                )
            elif tool_name == "news_search":
                return await self._news_search(
                    query=arguments.get("query", ""),
                    count=arguments.get("count", 20),
                )
            elif tool_name == "search_jobs":
                return await self._search_jobs(
                    role=arguments.get("role", ""),
                    location=arguments.get("location", ""),
                    remote=arguments.get("remote", False),
                )
            elif tool_name == "search_salary":
                return await self._search_salary(
                    role=arguments.get("role", ""),
                    location=arguments.get("location", ""),
                )
            else:
                raise MCPToolError(f"Unknown tool: {tool_name}")
        except MCPToolError:
            raise
        except Exception as e:
            raise MCPToolError(f"Tool call failed: {e}") from e

    async def _web_search(self, query: str, count: int = 20) -> MCPToolResult:
        """Perform a web search."""
        if not self._client:
            raise MCPToolError("Client not initialized")

        params = {
            "q": query,
            "count": min(count, 20),  # Max 20 per request on free tier
        }

        response = await self._client.get(f"{self.API_URL}/web/search", params=params)
        response.raise_for_status()

        data = response.json()
        results = []

        for item in data.get("web", {}).get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                }
            )

        return MCPToolResult(
            content=json.dumps(results, indent=2),
            raw_response=data,
            tool_name="web_search",
        )

    async def _news_search(self, query: str, count: int = 20) -> MCPToolResult:
        """Search for news articles."""
        if not self._client:
            raise MCPToolError("Client not initialized")

        params = {
            "q": query,
            "count": min(count, 20),
        }

        response = await self._client.get(f"{self.API_URL}/news/search", params=params)
        response.raise_for_status()

        data = response.json()
        results = []

        for item in data.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "age": item.get("age", ""),
                }
            )

        return MCPToolResult(
            content=json.dumps(results, indent=2),
            raw_response=data,
            tool_name="news_search",
        )

    async def _search_jobs(
        self,
        role: str,
        location: str = "",
        remote: bool = False,
    ) -> MCPToolResult:
        """Search for job postings."""
        if not self._client:
            raise MCPToolError("Client not initialized")

        # Build search query
        query_parts = [f"{role} jobs"]
        if location:
            query_parts.append(location)
        if remote:
            query_parts.append("remote")

        query = " ".join(query_parts)

        params = {
            "q": query,
            "count": 20,
        }

        response = await self._client.get(f"{self.API_URL}/web/search", params=params)
        response.raise_for_status()

        data = response.json()
        results = []

        for item in data.get("web", {}).get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                }
            )

        return MCPToolResult(
            content=json.dumps(
                {
                    "query": query,
                    "results": results,
                },
                indent=2,
            ),
            raw_response=data,
            tool_name="search_jobs",
        )

    async def _search_salary(self, role: str, location: str = "") -> MCPToolResult:
        """Search for salary information."""
        if not self._client:
            raise MCPToolError("Client not initialized")

        # Build search query for salary data
        query_parts = [f"{role} salary"]
        if location:
            query_parts.append(location)
        query_parts.append("2024 2025")  # Focus on recent data

        query = " ".join(query_parts)

        params = {
            "q": query,
            "count": 20,
        }

        response = await self._client.get(f"{self.API_URL}/web/search", params=params)
        response.raise_for_status()

        data = response.json()
        results = []

        for item in data.get("web", {}).get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                }
            )

        return MCPToolResult(
            content=json.dumps(
                {
                    "query": query,
                    "results": results,
                },
                indent=2,
            ),
            raw_response=data,
            tool_name="search_salary",
        )

    # Convenience methods for direct use
    async def search_tech_jobs(
        self,
        role: str,
        location: str = "",
        remote: bool = False,
    ) -> list[dict[str, Any]]:
        """Search for tech jobs (convenience method)."""
        result = await self.call_tool(
            "search_jobs",
            {
                "role": role,
                "location": location,
                "remote": remote,
            },
        )
        data = json.loads(result.content)
        return data.get("results", [])

    async def search_salary_data(
        self,
        role: str,
        location: str = "",
    ) -> list[dict[str, Any]]:
        """Search for salary data (convenience method)."""
        result = await self.call_tool(
            "search_salary",
            {
                "role": role,
                "location": location,
            },
        )
        data = json.loads(result.content)
        return data.get("results", [])
