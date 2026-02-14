"""Hacker News MCP client for tech trends and job market data.

Uses the Hacker News Algolia API (no authentication required).
Provides access to "Who is Hiring?" threads and tech trend analysis.
"""

import json
import re
from collections import Counter
from typing import Any

from .base import MCPToolResult
from .http_client import HTTPMCPClient


class HackerNewsMCPClient(HTTPMCPClient):
    """Hacker News MCP client using Algolia Search API.

    This is a lightweight client that directly calls the HN Algolia API
    rather than spawning an external MCP server process.

    Rate limit: 10,000 requests/hour from a single IP.
    """

    BASE_URL = "https://hn.algolia.com/api/v1"

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
        super().__init__()

    # Salary patterns for extraction
    SALARY_PATTERNS: list[str] = [
        r"\$(\d{2,3})[kK]?\s*[-–—to]+\s*\$?(\d{2,3})[kK]",  # $150k-$200k
        r"(\d{2,3})[kK]\s*[-–—to]+\s*(\d{2,3})[kK]",  # 150k-200k
        r"\$(\d{3},?\d{3})\s*[-–—to]+\s*\$?(\d{3},?\d{3})",  # $150,000-$200,000
        r"(\d{3},?\d{3})\s*[-–—to]+\s*(\d{3},?\d{3})",  # 150,000-200,000
        r"\$(\d{2,3})[kK]",  # $150k (single value)
        r"(\d{2,3})[kK]\s*(?:USD|usd|per year|/yr|/year)",  # 150k USD
    ]

    async def list_tools(self) -> list[str]:
        """List available tools."""
        return [
            "search_hn",
            "get_hiring_threads",
            "analyze_tech_trends",
            "get_top_stories",
            "get_freelancing_threads",
            "get_seeking_work_threads",
            "extract_job_postings",
        ]

    # Tool handler methods (called by HTTPMCPClient.call_tool via _get_tool_handler)

    async def _tool_search_hn(self, args: dict[str, Any]) -> MCPToolResult:
        """Search Hacker News for a query."""
        return await self._search_hn(args.get("query", ""))

    async def _tool_get_hiring_threads(self, args: dict[str, Any]) -> MCPToolResult:
        """Get recent 'Who is Hiring?' threads."""
        return await self._get_hiring_threads(args.get("months", 3))

    async def _tool_analyze_tech_trends(self, args: dict[str, Any]) -> MCPToolResult:
        """Analyze tech trends from Who is Hiring threads."""
        return await self._analyze_tech_trends(args.get("months", 3))

    async def _tool_get_top_stories(self, args: dict[str, Any]) -> MCPToolResult:
        """Get top tech stories from HN."""
        return await self._get_top_stories(args.get("limit", 30))

    async def _tool_get_freelancing_threads(self, args: dict[str, Any]) -> MCPToolResult:
        """Get recent 'Freelancer? Seeking freelancer?' threads."""
        return await self._get_freelancing_threads(args.get("months", 3))

    async def _tool_get_seeking_work_threads(self, args: dict[str, Any]) -> MCPToolResult:
        """Get recent 'Who wants to be hired?' threads."""
        return await self._get_seeking_work_threads(args.get("months", 3))

    async def _tool_extract_job_postings(self, args: dict[str, Any]) -> MCPToolResult:
        """Extract and parse individual job postings from hiring threads."""
        return await self._extract_job_postings(
            months=args.get("months", 1),
            limit=args.get("limit", 100),
        )

    async def _search_hn(self, query: str) -> MCPToolResult:
        """Search Hacker News for a query."""
        client = self._ensure_client()

        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": 50,
        }

        response = await client.get(f"{self.BASE_URL}/search", params=params)
        response.raise_for_status()

        data = response.json()
        hits = data.get("hits", [])

        results = []
        for hit in hits:
            results.append(
                {
                    "id": hit.get("objectID", ""),
                    "title": hit.get("title", ""),
                    "url": hit.get("url", ""),
                    "author": hit.get("author", ""),
                    "points": hit.get("points", 0),
                    "num_comments": hit.get("num_comments", 0),
                    "created_at": hit.get("created_at", ""),
                    "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                }
            )

        output = {"results": results, "total": len(results)}
        return self._format_response(output, data, "search_hn")

    async def _get_hiring_threads(self, months: int = 3) -> MCPToolResult:
        """Get recent 'Who is Hiring?' threads.

        Uses search_by_date to get the most recent monthly threads posted by 'whoishiring'.
        """
        client = self._ensure_client()

        # Use search_by_date to get recent threads, filter by author 'whoishiring'
        # and search for "Who is hiring" (not "Who wants to be hired")
        params = {
            "query": "Who is hiring",
            "tags": "story,author_whoishiring",
            "hitsPerPage": months * 2,  # Fetch extra to filter out "wants to be hired"
        }

        # Use search_by_date endpoint to get most recent first
        response = await client.get(f"{self.BASE_URL}/search_by_date", params=params)
        response.raise_for_status()

        data = response.json()
        threads = []

        for hit in data.get("hits", []):
            title = hit.get("title", "")
            # Filter to only "Who is hiring?" threads, not "Who wants to be hired?"
            if "who is hiring" in title.lower() and "wants to be hired" not in title.lower():
                threads.append(
                    {
                        "title": title,
                        "objectID": hit.get("objectID", ""),
                        "created_at": hit.get("created_at", ""),
                        "num_comments": hit.get("num_comments", 0),
                    }
                )
                if len(threads) >= months:
                    break

        output = {"threads": threads, "total": len(threads)}
        return self._format_response(output, data, "get_hiring_threads")

    async def _analyze_tech_trends(self, months: int = 3) -> MCPToolResult:
        """Analyze tech trends from Who is Hiring threads."""
        client = self._ensure_client()

        # Get hiring threads
        threads_result = await self._get_hiring_threads(months)
        threads_data = json.loads(threads_result.content)
        threads = threads_data.get("threads", [])

        tech_counts: Counter[str] = Counter()
        total_jobs = 0

        # Analyze comments from each thread
        for thread in threads:
            story_id = thread.get("objectID") or thread.get("id")
            if not story_id:
                continue

            # Get comments for this hiring thread
            params = {
                "tags": f"comment,story_{story_id}",
                "hitsPerPage": 500,
            }

            response = await client.get(f"{self.BASE_URL}/search", params=params)
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

        return self._format_response(results, results, "analyze_tech_trends")

    async def _get_top_stories(self, limit: int = 30) -> MCPToolResult:
        """Get top tech stories from HN."""
        client = self._ensure_client()

        params = {
            "tags": "front_page",
            "hitsPerPage": limit,
        }

        response = await client.get(f"{self.BASE_URL}/search", params=params)
        response.raise_for_status()

        data = response.json()
        stories = []

        for hit in data.get("hits", []):
            stories.append(
                {
                    "id": hit.get("objectID", ""),
                    "title": hit.get("title", ""),
                    "url": hit.get("url", ""),
                    "author": hit.get("author", ""),
                    "points": hit.get("points", 0),
                    "num_comments": hit.get("num_comments", 0),
                    "created_at": hit.get("created_at", ""),
                    "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                }
            )

        output = {"stories": stories, "total": len(stories)}
        return self._format_response(output, data, "get_top_stories")

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

    async def _get_freelancing_threads(self, months: int = 3) -> MCPToolResult:
        """Get recent 'Freelancer? Seeking freelancer?' threads.

        These monthly threads contain freelance opportunities and
        people offering freelance services.
        """
        client = self._ensure_client()

        params = {
            "query": "Freelancer Seeking freelancer",
            "tags": "story,author_whoishiring",
            "hitsPerPage": months,
        }

        # Use search_by_date to get most recent first
        response = await client.get(f"{self.BASE_URL}/search_by_date", params=params)
        response.raise_for_status()

        data = response.json()
        threads = []

        for hit in data.get("hits", []):
            title = hit.get("title", "")
            if "freelancer" in title.lower():
                threads.append(
                    {
                        "title": title,
                        "id": hit.get("objectID", ""),
                        "created_at": hit.get("created_at", ""),
                        "num_comments": hit.get("num_comments", 0),
                        "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    }
                )
                if len(threads) >= months:
                    break

        output = {"threads": threads, "total": len(threads)}
        return self._format_response(output, data, "get_freelancing_threads")

    async def _get_seeking_work_threads(self, months: int = 3) -> MCPToolResult:
        """Get recent 'Who wants to be hired?' threads.

        These monthly threads contain people looking for work,
        useful for understanding how others position themselves.
        """
        client = self._ensure_client()

        params = {
            "query": "Who wants to be hired",
            "tags": "story,author_whoishiring",
            "hitsPerPage": months * 2,  # Fetch extra to filter
        }

        # Use search_by_date to get most recent first
        response = await client.get(f"{self.BASE_URL}/search_by_date", params=params)
        response.raise_for_status()

        data = response.json()
        threads = []

        for hit in data.get("hits", []):
            title = hit.get("title", "")
            if "wants to be hired" in title.lower():
                threads.append(
                    {
                        "title": title,
                        "id": hit.get("objectID", ""),
                        "created_at": hit.get("created_at", ""),
                        "num_comments": hit.get("num_comments", 0),
                        "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    }
                )
                if len(threads) >= months:
                    break

        output = {"threads": threads, "total": len(threads)}
        return self._format_response(output, data, "get_seeking_work_threads")

    async def _extract_job_postings(self, months: int = 1, limit: int = 100) -> MCPToolResult:
        """Extract and parse individual job postings from hiring threads.

        This fetches actual comment text from "Who is hiring?" threads and
        parses out structured data: company, tech stack, salary, location, remote.

        Args:
            months: Number of recent hiring threads to analyze
            limit: Max job postings to return

        Returns:
            MCPToolResult with parsed job postings
        """
        client = self._ensure_client()

        # Get recent hiring threads
        threads_result = await self._get_hiring_threads(months)
        threads_data = json.loads(threads_result.content)
        threads = threads_data.get("threads", [])

        job_postings: list[dict[str, Any]] = []

        for thread in threads:
            story_id = thread.get("objectID") or thread.get("id")
            if not story_id:
                continue

            # Fetch comments (job postings) from this thread
            params = {
                "tags": f"comment,story_{story_id}",
                "hitsPerPage": min(limit * 2, 500),  # Fetch extra, filter later
            }

            response = await client.get(f"{self.BASE_URL}/search", params=params)
            if response.status_code != 200:
                continue

            comments = response.json().get("hits", [])

            for comment in comments:
                # Skip replies to job postings (we want top-level only)
                if comment.get("parent_id") != int(story_id):
                    continue

                text = comment.get("comment_text", "")
                if not text or len(text) < 50:  # Skip very short comments
                    continue

                # Parse the job posting
                parsed = self._parse_job_posting(text, comment)
                if parsed:
                    parsed["thread_id"] = story_id
                    parsed["thread_title"] = thread.get("title", "")
                    parsed["thread_date"] = thread.get("created_at", "")
                    job_postings.append(parsed)

                if len(job_postings) >= limit:
                    break

            if len(job_postings) >= limit:
                break

        output = {
            "source": "hn_hiring",
            "threads_analyzed": len(threads),
            "total_postings": len(job_postings),
            "postings": job_postings,
        }

        return self._format_response(output, output, "extract_job_postings")

    def _parse_job_posting(self, text: str, comment: dict[str, Any]) -> dict[str, Any] | None:
        """Parse a job posting comment into structured data.

        Extracts: company, location, remote status, salary, tech stack.
        """
        import html

        # Decode HTML entities
        text = html.unescape(text)

        # Remove HTML tags but preserve structure
        clean_text = re.sub(r"<[^>]+>", " ", text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        # Skip if too short after cleaning
        if len(clean_text) < 30:
            return None

        # Extract company name (usually at the start or in first line)
        company = self._extract_company(text, clean_text)

        # Extract location
        location = self._extract_location(clean_text)

        # Check for remote
        remote = self._is_remote(clean_text)

        # Extract salary
        salary_info = self._extract_salary(clean_text)

        # Extract tech stack
        tech_stack = self._extract_tech_stack(clean_text)

        # Extract job title hints
        title_hints = self._extract_title_hints(clean_text)

        return {
            "id": comment.get("objectID", ""),
            "company": company,
            "title_hints": title_hints,
            "location": location,
            "remote": remote,
            "salary_min": salary_info.get("min"),
            "salary_max": salary_info.get("max"),
            "salary_raw": salary_info.get("raw"),
            "tech_stack": tech_stack,
            "text_preview": clean_text[:500],
            "full_text": clean_text,
            "hn_url": f"https://news.ycombinator.com/item?id={comment.get('objectID', '')}",
            "author": comment.get("author", ""),
            "created_at": comment.get("created_at", ""),
            "site": "hn_hiring",
        }

    def _extract_company(self, html_text: str, clean_text: str) -> str | None:
        """Extract company name from job posting."""
        # Pattern 1: Company name at start, often bold or linked
        # e.g., "<b>Acme Corp</b> | Remote | ..."
        bold_match = re.search(r"<b>([^<]+)</b>", html_text)
        if bold_match:
            return bold_match.group(1).strip()

        # Pattern 2: Company name in link
        link_match = re.search(r"<a[^>]*>([^<]+)</a>", html_text)
        if link_match and len(link_match.group(1)) < 50:
            potential = link_match.group(1).strip()
            if not potential.startswith("http"):
                return potential

        # Pattern 3: First line before pipe or dash
        first_line = clean_text.split("\n")[0] if "\n" in clean_text else clean_text[:100]
        pipe_match = re.match(r"^([^|–—\-]+)", first_line)
        if pipe_match:
            potential = pipe_match.group(1).strip()
            # Filter out if it looks like a job title
            if len(potential) < 50 and not any(
                w in potential.lower()
                for w in ["engineer", "developer", "hiring", "looking", "seeking"]
            ):
                return potential

        return None

    def _extract_location(self, text: str) -> str | None:
        """Extract location from job posting."""
        text_lower = text.lower()

        # Common location patterns
        location_patterns = [
            r"\b(san francisco|sf bay area|bay area)\b",
            r"\b(new york|nyc|ny)\b",
            r"\b(los angeles|la)\b",
            r"\b(seattle|wa)\b",
            r"\b(austin|tx)\b",
            r"\b(boston|ma)\b",
            r"\b(denver|co)\b",
            r"\b(chicago|il)\b",
            r"\b(london|uk)\b",
            r"\b(berlin|germany)\b",
            r"\b(toronto|canada)\b",
            r"\b(worldwide|anywhere|global)\b",
            r"\b([A-Z][a-z]+,\s*[A-Z]{2})\b",  # City, ST format
        ]

        for pattern in location_patterns:
            match = re.search(pattern, text_lower if "worldwide" in pattern else text)
            if match:
                return match.group(1).title()

        return None

    def _is_remote(self, text: str) -> bool:
        """Check if job is remote."""
        text_lower = text.lower()
        remote_patterns = [
            r"\bremote\b",
            r"\bwork from home\b",
            r"\bwfh\b",
            r"\bfully distributed\b",
            r"\banywhere\b",
            r"\bglobal team\b",
        ]
        return any(re.search(p, text_lower) for p in remote_patterns)

    def _extract_salary(self, text: str) -> dict[str, Any]:
        """Extract salary information from text."""
        result: dict[str, Any] = {"min": None, "max": None, "raw": None}

        for pattern in self.SALARY_PATTERNS:
            match = re.search(pattern, text)
            if match:
                result["raw"] = match.group(0)
                groups = match.groups()

                if len(groups) >= 2:
                    # Range: min-max
                    try:
                        min_val = int(groups[0].replace(",", ""))
                        max_val = int(groups[1].replace(",", ""))
                        # Convert to full amounts if in K
                        if min_val < 1000:
                            min_val *= 1000
                        if max_val < 1000:
                            max_val *= 1000
                        result["min"] = min_val
                        result["max"] = max_val
                    except (ValueError, TypeError):
                        pass
                elif len(groups) == 1:
                    # Single value
                    try:
                        val = int(groups[0].replace(",", ""))
                        if val < 1000:
                            val *= 1000
                        result["min"] = val
                        result["max"] = val
                    except (ValueError, TypeError):
                        pass
                break

        return result

    def _extract_tech_stack(self, text: str) -> list[str]:
        """Extract mentioned technologies from text."""
        text_lower = text.lower()
        found_tech: list[str] = []

        for category, terms in self.TECH_TERMS.items():
            for term in terms:
                if re.search(rf"\b{re.escape(term)}\b", text_lower):
                    found_tech.append(term)

        return found_tech

    def _extract_title_hints(self, text: str) -> list[str]:
        """Extract job title hints from text."""
        text_lower = text.lower()
        titles: list[str] = []

        # Regex patterns for job titles (split for readability)
        seniority = r"(senior|sr\.?|staff|principal|lead|junior|jr\.?)"
        roles = r"(software|backend|frontend|full[- ]?stack|ml|ai|data|devops|sre|platform)"
        title_patterns = [
            rf"\b{seniority}\s*{roles}\s*(engineer|developer)?\b",
            rf"\b{roles}\s*(engineer|developer)\b",
            r"\b(engineering|tech|technical)\s*lead\b",
            r"\b(cto|vp of engineering|head of engineering)\b",
            r"\b(machine learning|ml|ai)\s*(engineer|scientist|researcher)\b",
            r"\b(data)\s*(engineer|scientist|analyst)\b",
        ]

        for pattern in title_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, tuple):
                    title = " ".join(m for m in match if m).strip()
                else:
                    title = match
                if title and title not in titles:
                    titles.append(title.title())

        return titles[:3]  # Limit to top 3
