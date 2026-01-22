"""HTML content extraction for portfolio scraping.

Single Responsibility: Parse HTML and extract semantic content.
"""

import json
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

from ...utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedContent:
    """Structured content extracted from HTML."""

    url: str
    title: str = ""
    meta_description: str = ""
    headings: list[dict] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    json_ld: list[dict] = field(default_factory=list)
    open_graph: dict[str, str] = field(default_factory=dict)
    twitter_card: dict[str, str] = field(default_factory=dict)
    meta_tags: dict[str, str] = field(default_factory=dict)


class HTMLExtractor:
    """Extract structured content from HTML.

    Single responsibility: Parse HTML and extract semantic content.
    """

    SECTION_PATTERNS = ["about", "projects", "skills", "experience", "contact", "work"]
    MIN_PARAGRAPH_LENGTH = 20
    MAX_SECTION_LENGTH = 2000

    def extract(self, html: str, url: str) -> ExtractedContent:
        """Extract all relevant content from HTML.

        Args:
            html: Raw HTML string
            url: Source URL for reference

        Returns:
            ExtractedContent with all extracted data
        """
        soup = BeautifulSoup(html, "html.parser")
        content = ExtractedContent(url=url)

        # Extract JSON-LD before removing scripts
        content.json_ld = self._extract_json_ld(soup)

        # Extract meta tags
        content.title = self._extract_title(soup)
        content.meta_description = self._extract_meta_description(soup)
        content.open_graph = self._extract_open_graph(soup)
        content.twitter_card = self._extract_twitter_card(soup)
        content.meta_tags = self._extract_other_meta(soup)

        # Remove script/style before text extraction
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        # Extract text content
        content.headings = self._extract_headings(soup)
        content.paragraphs = self._extract_paragraphs(soup)
        content.links = self._extract_links(soup)
        content.sections = self._extract_sections(soup)

        logger.debug(
            "Extracted from %s: %d headings, %d paragraphs, %d sections",
            url,
            len(content.headings),
            len(content.paragraphs),
            len(content.sections),
        )

        return content

    def _extract_json_ld(self, soup: BeautifulSoup) -> list[dict]:
        """Extract JSON-LD structured data."""
        results = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                if script.string:
                    data = json.loads(script.string)
                    results.append(data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug("Failed to parse JSON-LD: %s", e)
        return results

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        return soup.title.get_text(strip=True) if soup.title else ""

    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description."""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and isinstance(meta, Tag):
            content = meta.get("content")
            return str(content) if content else ""
        return ""

    def _extract_open_graph(self, soup: BeautifulSoup) -> dict[str, str]:
        """Extract Open Graph meta tags."""
        og: dict[str, str] = {}
        for tag in soup.find_all("meta", property=re.compile(r"^og:")):
            if isinstance(tag, Tag):
                prop = tag.get("property")
                content = tag.get("content")
                if prop and content:
                    key = str(prop).replace("og:", "")
                    og[key] = str(content)
        return og

    def _extract_twitter_card(self, soup: BeautifulSoup) -> dict[str, str]:
        """Extract Twitter Card meta tags."""
        tw: dict[str, str] = {}
        for tag in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")}):
            if isinstance(tag, Tag):
                name = tag.get("name")
                content = tag.get("content")
                if name and content:
                    key = str(name).replace("twitter:", "")
                    tw[key] = str(content)
        return tw

    def _extract_other_meta(self, soup: BeautifulSoup) -> dict[str, str]:
        """Extract other useful meta tags (author, keywords, theme-color)."""
        meta: dict[str, str] = {}
        for name in ["author", "keywords", "theme-color"]:
            tag = soup.find("meta", attrs={"name": name})
            if tag and isinstance(tag, Tag):
                content = tag.get("content")
                if content:
                    meta[name] = str(content)
        return meta

    def _extract_headings(self, soup: BeautifulSoup) -> list[dict]:
        """Extract h1, h2, h3 headings."""
        headings = []
        for tag_name in ["h1", "h2", "h3"]:
            for heading in soup.find_all(tag_name):
                text = heading.get_text(strip=True)
                if text:
                    headings.append({"level": tag_name, "text": text})
        return headings

    def _extract_paragraphs(self, soup: BeautifulSoup) -> list[str]:
        """Extract meaningful paragraphs (filtering short ones)."""
        return [
            p.get_text(strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > self.MIN_PARAGRAPH_LENGTH
        ]

    def _extract_links(self, soup: BeautifulSoup) -> list[dict]:
        """Extract links with their text."""
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if text and href and isinstance(href, str) and not href.startswith("#"):
                links.append({"text": text, "href": href})
        return links

    def _extract_sections(self, soup: BeautifulSoup) -> dict[str, str]:
        """Extract named sections by id/class patterns."""
        sections: dict[str, str] = {}
        for pattern in self.SECTION_PATTERNS:
            # Try finding by id first
            section = soup.find(id=lambda x: bool(x and pattern in str(x).lower()))
            # If not found, try by class
            if not section:
                section = soup.find(class_=lambda x: bool(x and pattern in str(x).lower()))
            if section:
                text = section.get_text(separator=" ", strip=True)
                if text:
                    sections[pattern] = text[: self.MAX_SECTION_LENGTH]
        return sections
