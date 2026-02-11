"""Tavily Search MCP client for market research and salary data.

Uses the Tavily API (1000 free queries/month, no credit card required).
Get your key at: https://tavily.com/
"""

from typing import Any

from ..config import settings
from .base import MCPConnectionError, MCPToolResult
from .http_client import HTTPMCPClient


class TavilyMCPClient(HTTPMCPClient):
    """Tavily Search MCP client.

    Free tier: 1000 queries/month, no credit card required.
    """

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(api_key=api_key or settings.tavily_api_key)

    def _validate_connection(self) -> None:
        """Validate that API key is configured."""
        if not self._api_key:
            raise MCPConnectionError(
                "Tavily API key not configured. Set TAVILY_API_KEY in .env\n"
                "Get your free key at: https://tavily.com/"
            )

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return ["web_search", "search_salary"]

    async def _tool_web_search(self, args: dict[str, Any]) -> MCPToolResult:
        """Perform a web search."""
        return await self._search(
            query=args.get("query", ""),
            max_results=args.get("count", 10),
        )

    async def _tool_search_salary(self, args: dict[str, Any]) -> MCPToolResult:
        """Search for salary data."""
        role = args.get("role", "")
        location = args.get("location", "")
        query = f"{role} salary {location} 2025".strip()
        return await self._search(query=query, max_results=10)

    async def _search(self, query: str, max_results: int = 10) -> MCPToolResult:
        """Perform a search using Tavily API."""
        client = self._ensure_client()

        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": min(max_results, 20),
            "include_answer": True,
        }

        response = await client.post(self.BASE_URL, json=payload)
        response.raise_for_status()

        data = response.json()
        results = []

        for item in data.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                }
            )

        output = {
            "query": query,
            "answer": data.get("answer", ""),
            "results": results,
        }

        return self._format_response(output, data, "web_search")
