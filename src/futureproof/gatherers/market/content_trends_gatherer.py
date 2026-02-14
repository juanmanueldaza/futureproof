"""Content trends gatherer for tech community insights.

Aggregates trending content from developer communities to understand
what skills and topics are generating interest.

Sources:
- Dev.to: Developer articles and discussions
- Stack Overflow: Technology popularity metrics
- Hacker News: Tech discussions (via existing TechTrendsGatherer)
"""

import logging
from typing import Any

from ...mcp.factory import MCPClientFactory
from .base import MarketGatherer

logger = logging.getLogger(__name__)


class ContentTrendsGatherer(MarketGatherer):
    """Gather content trends from developer communities.

    Collects:
    - Trending Dev.to articles by topic (AI, Python, TypeScript, etc.)
    - Stack Overflow tag popularity and trends
    - Technology engagement metrics

    Cache TTL: 12 hours (content changes moderately)
    """

    # Topics relevant for AI Engineer profile
    AI_TOPICS = ["ai", "machinelearning", "langchain", "llm", "openai", "python"]
    FULLSTACK_TOPICS = ["typescript", "react", "nextjs", "vue", "webdev"]

    def _get_cache_key(self, **kwargs: Any) -> str:
        """Generate cache key based on focus area."""
        focus = kwargs.get("focus", "all")
        return f"content_trends_{focus}".lower().replace(" ", "_")

    def _get_cache_ttl_hours(self) -> int:
        """Content trends cached for 12 hours."""
        from ...config import settings

        return settings.content_cache_hours

    async def gather(self, **kwargs: Any) -> dict[str, Any]:
        """Gather content trends from developer communities.

        Args:
            focus: Focus area - "ai", "fullstack", or "all"
            topics: Custom list of topics to track

        Returns:
            Dictionary with content trends data
        """
        focus = kwargs.get("focus", "all")
        custom_topics = kwargs.get("topics", [])

        # Determine topics based on focus
        if custom_topics:
            topics = custom_topics
        elif focus == "ai":
            topics = self.AI_TOPICS
        elif focus == "fullstack":
            topics = self.FULLSTACK_TOPICS
        else:
            topics = self.AI_TOPICS + self.FULLSTACK_TOPICS

        results: dict[str, Any] = {
            "focus": focus,
            "topics_tracked": topics,
            "devto_articles": [],
            "stackoverflow_trends": {},
            "summary": {},
            "errors": [],
        }

        logger.info(f"Gathering content trends for focus='{focus}' with {len(topics)} topics")

        # Gather from Dev.to
        if MCPClientFactory.is_available("devto"):
            try:
                logger.info("Dev.to: Fetching trending articles by topic...")
                client = MCPClientFactory.create("devto")
                async with client:
                    all_articles = []

                    # Get trending articles for each topic
                    for topic in topics[:6]:  # Limit to avoid rate limits
                        try:
                            logger.debug(f"Dev.to: Fetching articles for #{topic}...")
                            topic_result = await client.call_tool(
                                "get_by_tag",
                                {"tag": topic, "per_page": 10},
                            )

                            if not topic_result.is_error:
                                parsed = self._parse_mcp_content(topic_result.content)
                                articles = parsed.get("articles", [])
                                for article in articles:
                                    article["searched_topic"] = topic
                                all_articles.extend(articles)
                        except Exception as e:
                            logger.warning(f"Error fetching Dev.to articles for {topic}: {e}")

                    # Deduplicate by article ID and sort by reactions
                    seen_ids: set[int] = set()
                    unique_articles = []
                    for article in all_articles:
                        article_id = article.get("id")
                        if article_id and article_id not in seen_ids:
                            seen_ids.add(article_id)
                            unique_articles.append(article)

                    unique_articles.sort(key=lambda x: x.get("reactions_count", 0), reverse=True)
                    results["devto_articles"] = unique_articles[:30]

                    # Calculate engagement metrics
                    total_reactions = sum(a.get("reactions_count", 0) for a in unique_articles)
                    total_comments = sum(a.get("comments_count", 0) for a in unique_articles)
                    results["summary"]["devto_total_articles"] = len(unique_articles)
                    results["summary"]["devto_total_reactions"] = total_reactions
                    results["summary"]["devto_total_comments"] = total_comments
                    logger.info(
                        f"Dev.to: Found {len(unique_articles)} unique articles "
                        f"({total_reactions} reactions, {total_comments} comments)"
                    )

            except Exception as e:
                logger.exception("Error gathering from Dev.to")
                results["errors"].append(f"Dev.to error: {e}")

        # Gather from Stack Overflow
        if MCPClientFactory.is_available("stackoverflow"):
            try:
                logger.info("Stack Overflow: Fetching tag popularity data...")
                client = MCPClientFactory.create("stackoverflow")
                async with client:
                    # Get popularity for tracked topics
                    popularity_result = await client.call_tool(
                        "get_tag_popularity",
                        {"tags": topics},
                    )

                    if not popularity_result.is_error:
                        parsed = self._parse_mcp_content(popularity_result.content)
                        tags_found = parsed.get("tags", [])
                        results["stackoverflow_trends"]["topic_popularity"] = tags_found
                        results["summary"]["stackoverflow_quota_remaining"] = parsed.get(
                            "quota_remaining", 0
                        )
                        logger.info(
                            f"Stack Overflow: Retrieved {len(tags_found)} tag popularity metrics"
                        )
                    else:
                        logger.warning(
                            f"Stack Overflow tag popularity: {popularity_result.error_message}"
                        )

                    # Get overall trending tags
                    logger.debug("Stack Overflow: Fetching overall trending tags...")
                    trending_result = await client.call_tool(
                        "get_trending_tags",
                        {"page_size": 20},
                    )

                    if not trending_result.is_error:
                        parsed = self._parse_mcp_content(trending_result.content)
                        top_tags = parsed.get("tags", [])
                        results["stackoverflow_trends"]["top_tags"] = top_tags
                        logger.info(f"Stack Overflow: Retrieved top {len(top_tags)} trending tags")
                    else:
                        logger.warning(f"Stack Overflow trending: {trending_result.error_message}")

            except Exception as e:
                logger.exception("Error gathering from Stack Overflow")
                results["errors"].append(f"Stack Overflow error: {e}")

        return results

    def to_markdown(self, data: dict[str, Any]) -> str:
        """Convert gathered data to markdown format.

        Args:
            data: Gathered content trends data

        Returns:
            Markdown formatted string
        """
        lines = ["# Content Trends Report\n"]

        focus = data.get("focus", "all")
        topics = data.get("topics_tracked", [])
        lines.append(f"**Focus:** {focus}")
        lines.append(f"**Topics tracked:** {', '.join(topics)}\n")

        # Summary
        summary = data.get("summary", {})
        if summary:
            lines.append("## Summary\n")
            if summary.get("devto_total_articles"):
                lines.append(f"- **Dev.to articles:** {summary['devto_total_articles']}")
                lines.append(f"- **Total reactions:** {summary.get('devto_total_reactions', 0)}")
                lines.append(f"- **Total comments:** {summary.get('devto_total_comments', 0)}")
            lines.append("")

        # Dev.to Articles
        articles = data.get("devto_articles", [])
        if articles:
            lines.append("## Trending Dev.to Articles\n")
            for article in articles[:15]:
                title = article.get("title", "Unknown")
                author = article.get("author", "")
                reactions = article.get("reactions_count", 0)
                comments = article.get("comments_count", 0)
                url = article.get("url", "")
                tags = article.get("tags", [])

                if url:
                    lines.append(f"### [{title}]({url})")
                else:
                    lines.append(f"### {title}")

                lines.append(
                    f"**Author:** {author} | **Reactions:** {reactions} | **Comments:** {comments}"
                )
                if tags:
                    lines.append(f"**Tags:** {', '.join(tags[:5])}")
                lines.append("")

        # Stack Overflow Trends
        so_trends = data.get("stackoverflow_trends", {})
        if so_trends:
            lines.append("## Stack Overflow Technology Trends\n")

            topic_pop = so_trends.get("topic_popularity", [])
            if topic_pop:
                lines.append("### Tracked Topics Popularity\n")
                for tag_info in topic_pop[:12]:
                    tag = tag_info.get("tag", "")
                    count = tag_info.get("question_count", 0)
                    lines.append(f"- **{tag}:** {count:,} questions")
                lines.append("")

            top_tags = so_trends.get("top_tags", [])
            if top_tags:
                lines.append("### Top Overall Tags\n")
                for tag_info in top_tags[:10]:
                    tag = tag_info.get("tag", "")
                    count = tag_info.get("question_count", 0)
                    lines.append(f"- **{tag}:** {count:,} questions")
                lines.append("")

        # Errors
        errors = data.get("errors", [])
        if errors:
            lines.append("## Data Collection Notes\n")
            for error in errors:
                lines.append(f"- {error}")

        return "\n".join(lines)
