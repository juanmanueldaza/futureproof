"""Hacker News MCP client for tech trends and job market data.

Uses the Hacker News Algolia API (no authentication required).
Provides access to "Who is Hiring?" threads and tech trend analysis.
"""

import json
import re
from collections import Counter
from typing import Any

import httpx

from .base import MCPClient, MCPConnectionError, MCPToolError, MCPToolResult


class HackerNewsMCPClient(MCPClient):
    """Hacker News MCP client using Algolia Search API.

    This is a lightweight client that directly calls the HN Algolia API
    rather than spawning an external MCP server process.

    Rate limit: 10,000 requests/hour from a single IP.
    """

    ALGOLIA_API_URL = "https://hn.algolia.com/api/v1"

    # Tech terms to track in job postings
    TECH_TERMS: dict[str, list[str]] = {
        "languages": [
            "python",
            "javascript",
            "typescript",
            "rust",
            "go",
            "java",
            "kotlin",
            "swift",
            "ruby",
            "c++",
            "c#",
            "scala",
            "elixir",
        ],
        "frameworks": [
            "react",
            "vue",
            "angular",
            "nextjs",
            "django",
            "fastapi",
            "rails",
            "spring",
            "nestjs",
            "express",
            "flask",
            "svelte",
        ],
        "ai_ml": [
            "machine learning",
            "deep learning",
            "llm",
            "gpt",
            "ai",
            "pytorch",
            "tensorflow",
            "langchain",
            "openai",
            "anthropic",
            "rag",
            "embeddings",
            "transformers",
            "computer vision",
            "nlp",
        ],
        "cloud": [
            "aws",
            "gcp",
            "azure",
            "kubernetes",
            "docker",
            "terraform",
            "serverless",
            "lambda",
            "cloudflare",
            "vercel",
        ],
        "data": [
            "postgresql",
            "mongodb",
            "redis",
            "elasticsearch",
            "kafka",
            "spark",
            "snowflake",
            "databricks",
            "dbt",
            "airflow",
        ],
        "devops": [
            "ci/cd",
            "github actions",
            "jenkins",
            "gitlab ci",
            "devops",
            "sre",
            "infrastructure",
            "monitoring",
            "observability",
        ],
    }

    def __init__(self) -> None:
        self._connected = False
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Initialize HTTP client."""
        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            self._connected = True
        except Exception as e:
            raise MCPConnectionError(f"Failed to initialize HN client: {e}") from e

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
            "search_hn",
            "get_hiring_threads",
            "analyze_tech_trends",
            "get_top_stories",
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call a tool on the HN API."""
        if not self.is_connected():
            raise MCPToolError("Client not connected")

        try:
            if tool_name == "search_hn":
                return await self._search_hn(arguments.get("query", ""))
            elif tool_name == "get_hiring_threads":
                return await self._get_hiring_threads(arguments.get("months", 3))
            elif tool_name == "analyze_tech_trends":
                return await self._analyze_tech_trends(arguments.get("months", 3))
            elif tool_name == "get_top_stories":
                return await self._get_top_stories(arguments.get("limit", 30))
            else:
                raise MCPToolError(f"Unknown tool: {tool_name}")
        except MCPToolError:
            raise
        except Exception as e:
            raise MCPToolError(f"Tool call failed: {e}") from e

    async def _search_hn(self, query: str) -> MCPToolResult:
        """Search Hacker News for a query."""
        if not self._client:
            raise MCPToolError("Client not initialized")

        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": 50,
        }

        response = await self._client.get(f"{self.ALGOLIA_API_URL}/search", params=params)
        response.raise_for_status()

        data = response.json()
        hits = data.get("hits", [])

        results = []
        for hit in hits:
            results.append(
                {
                    "title": hit.get("title", ""),
                    "url": hit.get("url", ""),
                    "points": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "created_at": hit.get("created_at", ""),
                }
            )

        return MCPToolResult(
            content=json.dumps(results, indent=2),
            raw_response=data,
            tool_name="search_hn",
        )

    async def _get_hiring_threads(self, months: int = 3) -> MCPToolResult:
        """Get recent 'Who is Hiring?' threads."""
        if not self._client:
            raise MCPToolError("Client not initialized")

        params = {
            "query": "Ask HN: Who is hiring?",
            "tags": "ask_hn",
            "hitsPerPage": months,
        }

        response = await self._client.get(f"{self.ALGOLIA_API_URL}/search", params=params)
        response.raise_for_status()

        data = response.json()
        threads = []

        for hit in data.get("hits", []):
            threads.append(
                {
                    "title": hit.get("title", ""),
                    "objectID": hit.get("objectID", ""),
                    "created_at": hit.get("created_at", ""),
                    "num_comments": hit.get("num_comments", 0),
                }
            )

        return MCPToolResult(
            content=json.dumps(threads, indent=2),
            raw_response=data,
            tool_name="get_hiring_threads",
        )

    async def _analyze_tech_trends(self, months: int = 3) -> MCPToolResult:
        """Analyze tech trends from Who is Hiring threads."""
        if not self._client:
            raise MCPToolError("Client not initialized")

        # Get hiring threads
        threads_result = await self._get_hiring_threads(months)
        threads = json.loads(threads_result.content)

        tech_counts: Counter[str] = Counter()
        total_jobs = 0

        # Analyze comments from each thread
        for thread in threads:
            story_id = thread.get("objectID")
            if not story_id:
                continue

            # Get comments for this hiring thread
            params = {
                "tags": f"comment,story_{story_id}",
                "hitsPerPage": 500,
            }

            response = await self._client.get(f"{self.ALGOLIA_API_URL}/search", params=params)
            if response.status_code != 200:
                continue

            comments = response.json().get("hits", [])
            total_jobs += len(comments)

            # Count tech mentions
            for comment in comments:
                text = comment.get("comment_text", "").lower()
                for category, terms in self.TECH_TERMS.items():
                    for term in terms:
                        # Use word boundary for more accurate matching
                        if re.search(rf"\b{re.escape(term)}\b", text):
                            tech_counts[f"{category}:{term}"] += 1

        # Build results
        results = {
            "total_job_postings": total_jobs,
            "threads_analyzed": len(threads),
            "tech_mentions": dict(tech_counts.most_common(50)),
            "by_category": self._group_by_category(tech_counts),
        }

        return MCPToolResult(
            content=json.dumps(results, indent=2),
            raw_response=results,
            tool_name="analyze_tech_trends",
        )

    async def _get_top_stories(self, limit: int = 30) -> MCPToolResult:
        """Get top tech stories from HN."""
        if not self._client:
            raise MCPToolError("Client not initialized")

        params = {
            "tags": "front_page",
            "hitsPerPage": limit,
        }

        response = await self._client.get(f"{self.ALGOLIA_API_URL}/search", params=params)
        response.raise_for_status()

        data = response.json()
        stories = []

        for hit in data.get("hits", []):
            stories.append(
                {
                    "title": hit.get("title", ""),
                    "url": hit.get("url", ""),
                    "points": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                }
            )

        return MCPToolResult(
            content=json.dumps(stories, indent=2),
            raw_response=data,
            tool_name="get_top_stories",
        )

    def _group_by_category(self, tech_counts: Counter[str]) -> dict[str, list[dict[str, Any]]]:
        """Group tech mentions by category."""
        categories: dict[str, list[dict[str, Any]]] = {}

        for key, count in tech_counts.items():
            if ":" not in key:
                continue
            category, term = key.split(":", 1)
            if category not in categories:
                categories[category] = []
            categories[category].append({"term": term, "count": count})

        # Sort each category by count
        for category in categories:
            categories[category].sort(key=lambda x: x["count"], reverse=True)

        return categories

    # Convenience methods for direct use
    async def get_tech_trends(self, months: int = 3) -> dict[str, Any]:
        """Get tech trends analysis (convenience method)."""
        result = await self.call_tool("analyze_tech_trends", {"months": months})
        return json.loads(result.content)

    async def get_hiring_data(self, months: int = 3) -> list[dict[str, Any]]:
        """Get hiring thread data (convenience method)."""
        result = await self.call_tool("get_hiring_threads", {"months": months})
        return json.loads(result.content)
