"""We Work Remotely MCP client for remote job listings via RSS.

Uses the free We Work Remotely RSS feed (no auth required).
https://weworkremotely.com/ - one of the largest remote job boards.

RSS feeds provide structured data including:
- <region> tag for location
- <category> tag for job type
- Salary info embedded in descriptions
"""

import hashlib
import re
import xml.etree.ElementTree as ET
from html import unescape
from typing import Any

from .base import MCPToolResult
from .http_client import HTTPMCPClient
from .job_schema import attach_salary
from .salary_parser import extract_salary_from_html


class WeWorkRemotelyMCPClient(HTTPMCPClient):
    """We Work Remotely MCP client using RSS feeds.

    Free RSS feed, no authentication required.
    Returns remote job listings from weworkremotely.com.
    """

    # RSS feeds by category
    RSS_FEEDS = {
        "programming": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "design": "https://weworkremotely.com/categories/remote-design-jobs.rss",
        "devops": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "management": "https://weworkremotely.com/categories/remote-management-jobs.rss",
        "all": "https://weworkremotely.com/remote-jobs.rss",
    }

    BASE_URL = "https://weworkremotely.com"
    DEFAULT_HEADERS = {
        "User-Agent": "FutureProof Career Intelligence/1.0",
        "Accept": "application/rss+xml, application/xml, text/xml",
    }

    def __init__(self) -> None:
        super().__init__()

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return ["search_jobs"]

    async def _tool_search_jobs(self, args: dict[str, Any]) -> MCPToolResult:
        """Search job listings."""
        return await self._search_jobs(
            category=args.get("category", "programming"),
            limit=args.get("limit", 30),
        )

    async def _search_jobs(
        self,
        category: str = "programming",
        limit: int = 30,
    ) -> MCPToolResult:
        """Fetch remote job listings from WeWorkRemotely RSS.

        Args:
            category: Job category (programming, design, devops, management, all)
            limit: Max number of jobs to return

        Returns:
            MCPToolResult with job listings
        """
        client = self._ensure_client()

        # Get RSS feed URL
        feed_url = self.RSS_FEEDS.get(category, self.RSS_FEEDS["programming"])

        response = await client.get(feed_url)
        response.raise_for_status()

        # Parse RSS XML
        root = ET.fromstring(response.content)

        jobs = []
        for item in root.findall(".//item"):
            job = self._parse_item(item)
            if job:
                jobs.append(job)
            if len(jobs) >= limit:
                break

        output = {
            "source": "weworkremotely",
            "category": category,
            "total_results": len(jobs),
            "jobs": jobs,
        }

        return self._format_response(output, response.text, "search_jobs")

    def _parse_item(self, item: ET.Element) -> dict[str, Any] | None:
        """Parse a single RSS item into a job dict."""
        title_raw = item.findtext("title", "")
        link = item.findtext("link", "")
        guid = item.findtext("guid", link)
        description = item.findtext("description", "")
        pub_date = item.findtext("pubDate", "")
        region = item.findtext("region", "")
        category = item.findtext("category", "")

        if not title_raw or not link:
            return None

        # Parse company and title from "Company: Job Title" format
        company, title = self._parse_title(title_raw)

        # Generate unique ID from guid
        job_id = hashlib.md5(guid.encode()).hexdigest()[:12]

        # Unescape HTML in description
        description_text = unescape(description) if description else ""

        # Extract salary from description
        salary_data = extract_salary_from_html(description_text)

        job: dict[str, Any] = {
            "id": job_id,
            "title": title,
            "company": company,
            "url": link,
            "region": region or "Remote",
            "category": category,
            "date_posted": pub_date,
            "description": self._clean_description(description_text)[:500],
            "site": "weworkremotely",
        }

        # Add salary if found
        attach_salary(job, salary_data)

        return job

    def _parse_title(self, title_raw: str) -> tuple[str, str]:
        """Parse 'Company: Job Title' into (company, title).

        Args:
            title_raw: Raw title string like "Acme Inc: Senior Developer"

        Returns:
            Tuple of (company, title)
        """
        if ": " in title_raw:
            parts = title_raw.split(": ", 1)
            return parts[0].strip(), parts[1].strip()
        return "", title_raw.strip()

    def _clean_description(self, html: str) -> str:
        """Clean HTML description to plain text."""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        # Unescape HTML entities
        text = unescape(text)
        return text.strip()
