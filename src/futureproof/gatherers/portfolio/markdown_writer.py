"""Markdown generation for portfolio content.

Single Responsibility: Format extracted content as markdown.
"""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .html_extractor import ExtractedContent
    from .js_extractor import JSContent


class PortfolioMarkdownWriter:
    """Generate markdown from extracted portfolio content.

    Single responsibility: Format content as markdown.
    """

    MAX_PARAGRAPHS = 20

    def generate(
        self,
        content: "ExtractedContent",
        js_content: "JSContent",
    ) -> str:
        """Generate markdown from extracted content.

        Args:
            content: HTML-extracted content
            js_content: JavaScript-extracted content

        Returns:
            Formatted markdown string
        """
        sections = [
            self._header(content),
            self._description(content),
            self._json_ld_profile(content),
            self._open_graph(content),
            self._meta_info(content),
            self._js_projects(js_content),
            self._js_socials(js_content),
            self._js_bio(js_content),
            self._html_sections(content),
            self._fallback_content(content, js_content),
            self._all_links(content),
        ]

        return "\n".join(s for s in sections if s)

    def _header(self, content: "ExtractedContent") -> str:
        """Generate document header."""
        title = content.title or "Personal Portfolio"
        return (
            f"# Portfolio: {title}\n\n"
            f"**URL:** {content.url}\n"
            f"**Scraped:** {datetime.now().isoformat()}\n"
        )

    def _description(self, content: "ExtractedContent") -> str:
        """Generate description section."""
        if not content.meta_description:
            return ""
        return f"\n## Description\n\n{content.meta_description}\n"

    def _json_ld_profile(self, content: "ExtractedContent") -> str:
        """Generate professional profile from JSON-LD Person data."""
        lines: list[str] = []
        for ld in content.json_ld:
            if ld.get("@type") != "Person":
                continue
            lines.extend(
                [
                    "\n## Professional Profile (Structured Data)\n",
                    f"- **Name:** {ld.get('name', 'N/A')}",
                    f"- **Job Title:** {ld.get('jobTitle', 'N/A')}",
                    f"- **Description:** {ld.get('description', 'N/A')}",
                    f"- **Email:** {ld.get('email', 'N/A')}",
                    "",
                ]
            )
            if ld.get("sameAs"):
                lines.append("**Social Links:**\n")
                for link in ld["sameAs"]:
                    lines.append(f"- {link}")
                lines.append("")
        return "\n".join(lines)

    def _open_graph(self, content: "ExtractedContent") -> str:
        """Generate Open Graph data section."""
        return self._dict_section("Open Graph Data", content.open_graph)

    def _meta_info(self, content: "ExtractedContent") -> str:
        """Generate meta information section."""
        return self._dict_section("Meta Information", content.meta_tags)

    def _dict_section(self, title: str, data: dict[str, str]) -> str:
        """Format a dict as a markdown section with key-value list."""
        if not data:
            return ""
        lines = [f"\n## {title}\n"]
        for key, value in data.items():
            lines.append(f"- **{key}:** {value}")
        return "\n".join(lines) + "\n"

    def _js_projects(self, js_content: "JSContent") -> str:
        """Generate featured projects section from JS data."""
        if not js_content.projects:
            return ""
        lines = ["\n## Featured Projects\n"]
        for proj in js_content.projects:
            lines.append(f"### {proj.get('name', 'Untitled')}\n")
            lines.append(f"- **Description:** {proj.get('description', 'N/A')}")
            if proj.get("url"):
                lines.append(f"- **Live URL:** {proj['url']}")
            if proj.get("github"):
                lines.append(f"- **GitHub:** {proj['github']}")
            lines.append("")
        return "\n".join(lines)

    def _js_socials(self, js_content: "JSContent") -> str:
        """Generate social links section from JS data."""
        if not js_content.socials:
            return ""
        lines = ["\n## Social Links\n"]
        for social in js_content.socials:
            name = social.get("name", "Link")
            url = social.get("url", "")
            if url:
                lines.append(f"- **{name}:** {url}")
        return "\n".join(lines) + "\n"

    def _js_bio(self, js_content: "JSContent") -> str:
        """Generate about section from JS content bio."""
        if not js_content.bio:
            return ""
        # Try to get English bio first
        en_bio = js_content.bio.get("en", {})
        if not isinstance(en_bio, dict):
            return ""

        bio_text = en_bio.get("bio", "")
        subtitle = en_bio.get("subtitle", "")

        if not (bio_text or subtitle):
            return ""

        lines = ["\n## About (from content)\n"]
        if subtitle:
            lines.append(f"**Role:** {subtitle}\n")
        if bio_text:
            lines.append(bio_text)
        return "\n".join(lines) + "\n"

    def _html_sections(self, content: "ExtractedContent") -> str:
        """Generate sections extracted from HTML."""
        if not content.sections:
            return ""
        lines: list[str] = []
        for name, text in content.sections.items():
            lines.append(f"\n## {name.title()}\n")
            lines.append(text)
        return "\n".join(lines) + "\n"

    def _fallback_content(
        self,
        content: "ExtractedContent",
        js_content: "JSContent",
    ) -> str:
        """Use headings/paragraphs if no sections or projects found."""
        if content.sections or js_content.projects:
            return ""

        lines: list[str] = []
        if content.headings:
            lines.append("\n## Content Structure\n")
            for heading in content.headings:
                level = int(heading["level"][1])
                prefix = "#" * (level + 1)
                lines.append(f"{prefix} {heading['text']}\n")

        if content.paragraphs:
            lines.append("\n## Main Content\n")
            for para in content.paragraphs[: self.MAX_PARAGRAPHS]:
                lines.append(para + "\n")

        return "\n".join(lines)

    def _all_links(self, content: "ExtractedContent") -> str:
        """Generate all links section."""
        if not content.links:
            return ""

        lines = ["\n## All Links\n"]
        seen: set[tuple[str, str]] = set()
        for link in content.links:
            key = (link["text"], link["href"])
            if key not in seen and link["text"]:
                seen.add(key)
                lines.append(f"- [{link['text']}]({link['href']})")
        return "\n".join(lines) + "\n"
