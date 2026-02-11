"""Dev.to MCP client for tech content trends.

Uses the free Dev.to API (no auth required).
https://dev.to/ - Developer community with trending articles.
"""

from typing import Any

from .base import MCPToolResult
from .http_client import HTTPMCPClient


class DevToMCPClient(HTTPMCPClient):
    """Dev.to MCP client for tech articles and trends.

    Free API, no authentication required.
    Returns trending articles from dev.to.
    """

    BASE_URL = "https://dev.to/api/articles"
    DEFAULT_HEADERS = {
        "User-Agent": "FutureProof Career Intelligence/1.0",
        "Accept": "application/json",
    }

    def __init__(self) -> None:
        super().__init__()

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return ["search_articles", "get_trending", "get_by_tag"]

    async def _tool_search_articles(self, args: dict[str, Any]) -> MCPToolResult:
        """Search Dev.to articles."""
        return await self._search_articles(
            query=args.get("query", ""),
            per_page=args.get("per_page", 30),
        )

    async def _tool_get_trending(self, args: dict[str, Any]) -> MCPToolResult:
        """Get trending Dev.to articles."""
        return await self._get_trending(per_page=args.get("per_page", 30))

    async def _tool_get_by_tag(self, args: dict[str, Any]) -> MCPToolResult:
        """Get Dev.to articles by tag."""
        return await self._get_by_tag(
            tag=args.get("tag", ""),
            per_page=args.get("per_page", 30),
        )

    async def _search_articles(
        self,
        query: str,
        per_page: int = 30,
    ) -> MCPToolResult:
        """Search Dev.to articles.

        Args:
            query: Search query
            per_page: Number of articles to return

        Returns:
            MCPToolResult with article listings
        """
        client = self._ensure_client()

        # Dev.to doesn't have a search endpoint, use tag-based filtering
        # For general search, we fetch top articles
        params = {
            "per_page": min(per_page, 100),
            "top": 7,  # Top articles from last 7 days
        }

        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        articles = response.json()
        return self._format_articles(articles, "search_articles")

    async def _get_trending(
        self,
        per_page: int = 30,
    ) -> MCPToolResult:
        """Get trending Dev.to articles.

        Args:
            per_page: Number of articles to return

        Returns:
            MCPToolResult with trending articles
        """
        client = self._ensure_client()

        params = {
            "per_page": min(per_page, 100),
            "top": 7,  # Top articles from last 7 days
        }

        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        articles = response.json()
        return self._format_articles(articles, "get_trending")

    async def _get_by_tag(
        self,
        tag: str,
        per_page: int = 30,
    ) -> MCPToolResult:
        """Get Dev.to articles by tag.

        Args:
            tag: Tag to filter by (e.g., "python", "ai", "machinelearning")
            per_page: Number of articles to return

        Returns:
            MCPToolResult with tagged articles
        """
        client = self._ensure_client()

        params = {
            "tag": tag.lower(),
            "per_page": min(per_page, 100),
            "top": 30,  # Top articles from last 30 days for specific tags
        }

        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        articles = response.json()
        return self._format_articles(articles, "get_by_tag", tag=tag)

    def _format_articles(
        self,
        articles: list[dict[str, Any]],
        tool_name: str,
        tag: str | None = None,
    ) -> MCPToolResult:
        """Format articles into consistent structure."""
        formatted = []
        for article in articles:
            user = article.get("user", {})
            formatted.append(
                {
                    "id": article.get("id"),
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", ""),
                    "canonical_url": article.get("canonical_url", ""),
                    "cover_image": article.get("cover_image"),
                    # Author info
                    "author": user.get("name", ""),
                    "author_username": user.get("username", ""),
                    "author_github": user.get("github_username"),
                    "author_twitter": user.get("twitter_username"),
                    # Content metadata
                    "tags": article.get("tag_list", []),
                    "reading_time_minutes": article.get("reading_time_minutes", 0),
                    "language": article.get("language", "en"),
                    # Engagement metrics
                    "reactions_count": article.get("public_reactions_count", 0),
                    "comments_count": article.get("comments_count", 0),
                    # Freshness fields
                    "created_at": article.get("created_at", ""),
                    "published_at": article.get("published_timestamp", ""),
                    "edited_at": article.get("edited_at"),
                    "last_comment_at": article.get("last_comment_at"),
                    "source": "devto",
                }
            )

        output: dict[str, Any] = {
            "source": "devto",
            "total_returned": len(formatted),
            "articles": formatted,
        }
        if tag:
            output["tag"] = tag

        return self._format_response(output, articles, tool_name)
