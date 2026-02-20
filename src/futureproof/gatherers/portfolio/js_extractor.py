"""JavaScript content extraction for portfolio scraping.

Single Responsibility: Parse JS content files for portfolio data.

Note: This uses regex parsing which is inherently fragile for parsing JS.
Consider alternatives for production use:
- Using a JS parser library (e.g., esprima via subprocess)
- Requiring structured data files (JSON) instead
- Using headless browser for JS-heavy sites
"""

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ...utils.logging import get_logger

if TYPE_CHECKING:
    from .fetcher import PortfolioFetcher

logger = get_logger(__name__)

# Security limits
MAX_JS_FILES = 5  # Maximum JS files to fetch per page
MAX_CONTENT_FILES = 3  # Maximum content files to fetch per JS file
MAX_JSON_SIZE = 1024 * 1024  # 1MB limit for JSON parsing


@dataclass
class JSContent:
    """Content extracted from JavaScript files."""

    projects: list[dict] = field(default_factory=list)
    socials: list[dict] = field(default_factory=list)
    bio: dict = field(default_factory=dict)
    source_url: str | None = None


class JSExtractor:
    """Extract content from JavaScript files.

    Single responsibility: Parse JS content files for portfolio data.

    Warning: Uses regex parsing which is fragile. May fail on complex JS structures.
    """

    def extract(
        self,
        html: str,
        base_url: str,
        fetcher: "PortfolioFetcher",
    ) -> JSContent:
        """Find and extract content from linked JavaScript files.

        Args:
            html: HTML containing script references
            base_url: Base URL for resolving relative paths
            fetcher: Object implementing fetch() method

        Returns:
            JSContent with extracted projects, socials, bio
        """
        soup = BeautifulSoup(html, "html.parser")
        js_files_processed = 0

        for script in soup.find_all("script", type="module"):
            # Rate limiting: don't fetch too many JS files
            if js_files_processed >= MAX_JS_FILES:
                logger.debug("Reached max JS file limit (%d)", MAX_JS_FILES)
                break

            src = script.get("src")
            if not src:
                continue

            js_url = urljoin(base_url, src)
            try:
                result = fetcher.fetch(js_url)
                js_files_processed += 1

                content = self._find_content_imports(result.content, js_url, fetcher)
                if content.projects or content.socials or content.bio:
                    logger.debug("Found JS content from %s", content.source_url)
                    return content
            except Exception as e:
                logger.debug("Failed to process JS file %s: %s", js_url, e)

        return JSContent()

    def _find_content_imports(
        self,
        js_text: str,
        js_url: str,
        fetcher: "PortfolioFetcher",
    ) -> JSContent:
        """Find and fetch content files from import statements."""
        imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", js_text)
        content_files_processed = 0

        for imp in imports:
            # Rate limiting: don't fetch too many content files
            if content_files_processed >= MAX_CONTENT_FILES:
                logger.debug("Reached max content file limit (%d)", MAX_CONTENT_FILES)
                break

            if "content" not in imp.lower():
                continue

            content_url = urljoin(js_url, imp)
            try:
                result = fetcher.fetch(content_url)
                content_files_processed += 1

                # Size limit check
                if len(result.content) > MAX_JSON_SIZE:
                    logger.warning("Content file too large: %d bytes", len(result.content))
                    continue

                content = self._parse_content_file(result.content)
                content.source_url = content_url
                return content
            except Exception as e:
                logger.debug("Failed to fetch content file %s: %s", content_url, e)

        return JSContent()

    def _parse_content_file(self, js_text: str) -> JSContent:
        """Parse a JavaScript content file.

        This method uses regex which is inherently fragile for parsing JS.
        It handles common patterns but may fail on complex structures.
        """
        result = JSContent()

        # Try to extract 'content' object
        result.bio = self._extract_content_object(js_text)

        # Extract projects array
        result.projects = self._extract_array(
            js_text,
            "projects",
            ["name", "description", "url", "github"],
        )

        # Extract socials array
        result.socials = self._extract_array(
            js_text,
            "socials",
            ["name", "url", "icon"],
        )

        return result

    def _extract_content_object(self, js_text: str) -> dict:
        """Extract the main content object."""
        match = re.search(
            r"(?:const|let|var)\s+content\s*=\s*(\{[\s\S]*?\});?\s*(?:const|let|var|export|$)",
            js_text,
        )
        if not match:
            return {}

        try:
            js_obj = match.group(1)
            # Clean JS object for JSON parsing
            js_obj = re.sub(r",(\s*[}\]])", r"\1", js_obj)  # Remove trailing commas
            js_obj = re.sub(r"(\s)(\w+):", r'\1"\2":', js_obj)  # Quote unquoted keys
            return json.loads(js_obj)
        except json.JSONDecodeError:
            # Fallback: try extracting individual language blocks
            bio = {}
            for lang in ["en", "es"]:
                lang_match = re.search(
                    rf"{lang}:\s*\{{([^}}]+)\}}",
                    js_text,
                    re.DOTALL,
                )
                if lang_match:
                    bio[lang] = lang_match.group(1)
            return bio

    def _extract_array(
        self,
        js_text: str,
        array_name: str,
        fields: list[str],
    ) -> list[dict]:
        """Extract an array of objects from JS."""
        # Try property syntax first (projects: [...])
        pattern = rf"{array_name}:\s*\[([\s\S]*?)\]"
        match = re.search(pattern, js_text)

        if not match:
            # Try top-level variable (const projects = [...])
            pattern = rf"(?:const|let|var)\s+{array_name}\s*=\s*\[([\s\S]*?)\];"
            match = re.search(pattern, js_text)

        if not match:
            return []

        items = []
        array_str = match.group(1)

        for obj_match in re.finditer(r"\{([^}]+)\}", array_str):
            obj_str = obj_match.group(1)
            item = {}
            for field_name in fields:
                field_match = re.search(
                    rf'{field_name}:\s*["\']([^"\']+)["\']',
                    obj_str,
                )
                if field_match:
                    item[field_name] = field_match.group(1)
            if item:
                items.append(item)

        return items
