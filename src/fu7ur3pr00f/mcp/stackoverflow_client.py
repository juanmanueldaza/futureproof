"""Stack Overflow MCP client for technology trends.

Uses the free Stack Exchange API (300 requests/day without key).
https://api.stackexchange.com/ - Technology popularity and trends.
"""

from typing import Any

from .base import MCPToolError, MCPToolResult
from .http_client import HTTPMCPClient


class StackOverflowMCPClient(HTTPMCPClient):
    """Stack Overflow MCP client for tech trends.

    Free API, no authentication required (300 requests/day).
    With API key: 10,000 requests/day.
    Returns technology popularity data from Stack Overflow.
    """

    BASE_URL = "https://api.stackexchange.com/2.3"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(api_key=api_key)

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return ["get_tag_popularity", "get_trending_tags", "get_tag_info", "get_popular_questions"]

    async def _tool_get_tag_popularity(self, args: dict[str, Any]) -> MCPToolResult:
        """Get popularity metrics for specific tags."""
        return await self._get_tag_popularity(tags=args.get("tags", []))

    async def _tool_get_trending_tags(self, args: dict[str, Any]) -> MCPToolResult:
        """Get most popular tags."""
        return await self._get_trending_tags(page_size=args.get("page_size", 30))

    async def _tool_get_tag_info(self, args: dict[str, Any]) -> MCPToolResult:
        """Get detailed info about a specific tag."""
        return await self._get_tag_info(tag=args.get("tag", ""))

    async def _tool_get_popular_questions(self, args: dict[str, Any]) -> MCPToolResult:
        """Get popular questions for a tag."""
        return await self._get_popular_questions(
            tag=args.get("tag", ""),
            page_size=args.get("page_size", 20),
            sort=args.get("sort", "votes"),
        )

    def _base_params(self) -> dict[str, Any]:
        """Get base parameters for API requests."""
        params: dict[str, Any] = {
            "site": "stackoverflow",
        }
        if self._api_key:
            params["key"] = self._api_key
        return params

    async def _get_tag_popularity(
        self,
        tags: list[str],
    ) -> MCPToolResult:
        """Get popularity metrics for specific tags.

        Args:
            tags: List of tags to check (e.g., ["python", "langchain", "ai"])

        Returns:
            MCPToolResult with tag popularity data
        """
        client = self._ensure_client()

        if not tags:
            raise MCPToolError("At least one tag is required")

        # Stack Exchange API: /tags/{tags}/info for exact tag lookups
        # Use semicolon-separated tags for batch lookup
        tags_param = ";".join(tags[:20])  # Max 20 tags

        params = self._base_params()

        # Use /tags/{tags}/info endpoint for exact matches
        response = await client.get(f"{self.BASE_URL}/tags/{tags_param}/info", params=params)
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        results = []
        for item in items:
            results.append(
                {
                    "tag": item.get("name", ""),
                    "question_count": item.get("count", 0),
                    "has_synonyms": item.get("has_synonyms", False),
                    "is_moderator_only": item.get("is_moderator_only", False),
                }
            )

        output = {
            "source": "stackoverflow",
            "requested_tags": tags,
            "found": len(results),
            "quota_remaining": data.get("quota_remaining", 0),
            "tags": results,
        }

        return self._format_response(output, data, "get_tag_popularity")

    async def _get_trending_tags(
        self,
        page_size: int = 30,
    ) -> MCPToolResult:
        """Get most popular tags on Stack Overflow.

        Args:
            page_size: Number of tags to return

        Returns:
            MCPToolResult with trending tags
        """
        client = self._ensure_client()

        params = self._base_params()
        params.update(
            {
                "order": "desc",
                "sort": "popular",
                "pagesize": min(page_size, 100),
            }
        )

        response = await client.get(f"{self.BASE_URL}/tags", params=params)
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        results = []
        for item in items:
            results.append(
                {
                    "tag": item.get("name", ""),
                    "question_count": item.get("count", 0),
                    "has_synonyms": item.get("has_synonyms", False),
                }
            )

        output = {
            "source": "stackoverflow",
            "total_returned": len(results),
            "quota_remaining": data.get("quota_remaining", 0),
            "tags": results,
        }

        return self._format_response(output, data, "get_trending_tags")

    async def _get_tag_info(
        self,
        tag: str,
    ) -> MCPToolResult:
        """Get detailed info about a specific tag.

        Args:
            tag: Tag name to look up

        Returns:
            MCPToolResult with tag details
        """
        client = self._ensure_client()

        if not tag:
            raise MCPToolError("Tag name is required")

        params = self._base_params()

        response = await client.get(f"{self.BASE_URL}/tags/{tag}/info", params=params)
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        if not items:
            output = {
                "source": "stackoverflow",
                "tag": tag,
                "found": False,
                "quota_remaining": data.get("quota_remaining", 0),
            }
        else:
            item = items[0]
            output = {
                "source": "stackoverflow",
                "tag": tag,
                "found": True,
                "question_count": item.get("count", 0),
                "has_synonyms": item.get("has_synonyms", False),
                "is_moderator_only": item.get("is_moderator_only", False),
                "is_required": item.get("is_required", False),
                "quota_remaining": data.get("quota_remaining", 0),
            }

        return self._format_response(output, data, "get_tag_info")

    async def _get_popular_questions(
        self,
        tag: str,
        page_size: int = 20,
        sort: str = "votes",
    ) -> MCPToolResult:
        """Get popular questions for a specific tag.

        This provides richer insights than tag counts alone - you can see
        what problems developers are actively solving and what's trending.

        Args:
            tag: Tag to search questions for (e.g., "langchain", "pytorch")
            page_size: Number of questions to return (max 100)
            sort: Sort order - "votes" (most upvoted), "activity" (recent activity),
                  "creation" (newest), "hot" (currently trending)

        Returns:
            MCPToolResult with question data including view counts and scores
        """
        client = self._ensure_client()

        if not tag:
            raise MCPToolError("Tag is required")

        params = self._base_params()
        params.update(
            {
                "tagged": tag,
                "order": "desc",
                "sort": sort,
                "pagesize": min(page_size, 100),
                "filter": "withbody",  # Include question body for more context
            }
        )

        response = await client.get(f"{self.BASE_URL}/questions", params=params)
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        questions = []
        for item in items:
            # Extract owner info
            owner = item.get("owner", {})

            questions.append(
                {
                    "id": item.get("question_id"),
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "score": item.get("score", 0),
                    "view_count": item.get("view_count", 0),
                    "answer_count": item.get("answer_count", 0),
                    "is_answered": item.get("is_answered", False),
                    "accepted_answer_id": item.get("accepted_answer_id"),
                    "creation_date": item.get("creation_date"),
                    "last_activity_date": item.get("last_activity_date"),
                    "tags": item.get("tags", []),
                    "owner_reputation": owner.get("reputation", 0),
                    "owner_name": owner.get("display_name", ""),
                    "body_preview": (item.get("body", "") or "")[:300],
                }
            )

        # Calculate some aggregate stats
        total_views = sum(q["view_count"] for q in questions)
        avg_score = sum(q["score"] for q in questions) / len(questions) if questions else 0
        answered_pct = (
            sum(1 for q in questions if q["is_answered"]) / len(questions) * 100 if questions else 0
        )

        output = {
            "source": "stackoverflow",
            "tag": tag,
            "sort": sort,
            "total_returned": len(questions),
            "aggregate_stats": {
                "total_views": total_views,
                "avg_score": round(avg_score, 1),
                "answered_percentage": round(answered_pct, 1),
            },
            "quota_remaining": data.get("quota_remaining", 0),
            "questions": questions,
        }

        return self._format_response(output, data, "get_popular_questions")
