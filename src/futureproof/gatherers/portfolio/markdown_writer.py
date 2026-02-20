"""Section generation for portfolio content.

Single Responsibility: Format extracted content as labeled sections.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from ...memory.chunker import Section

if TYPE_CHECKING:
    from .html_extractor import ExtractedContent
    from .js_extractor import JSContent


class PortfolioMarkdownWriter:
    """Generate sections from extracted portfolio content.

    Single responsibility: Format content as Section(name, content) tuples.
    """

    MAX_PARAGRAPHS = 20

    def generate(
        self,
        content: "ExtractedContent",
        js_content: "JSContent",
    ) -> list[Section]:
        """Generate sections from extracted content.

        Args:
            content: HTML-extracted content
            js_content: JavaScript-extracted content

        Returns:
            List of Section(name, content) tuples
        """
        builders = [
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

        # Flatten: most return Section|None, _html_sections returns list
        sections: list[Section] = []
        for result in builders:
            if result is None:
                continue
            if isinstance(result, list):
                sections.extend(result)
            else:
                sections.append(result)
        return sections

    def _header(self, content: "ExtractedContent") -> Section:
        """Generate document header."""
        title = content.title or "Personal Portfolio"
        text = (
            f"**Title:** {title}\n"
            f"**URL:** {content.url}\n"
            f"**Scraped:** {datetime.now().isoformat()}"
        )
        return Section("Header", text)

    def _description(self, content: "ExtractedContent") -> Section | None:
        """Generate description section."""
        if not content.meta_description:
            return None
        return Section("Description", content.meta_description)

    def _json_ld_profile(self, content: "ExtractedContent") -> Section | None:
        """Generate professional profile from JSON-LD Person data."""
        lines: list[str] = []
        for ld in content.json_ld:
            if ld.get("@type") != "Person":
                continue
            lines.extend(
                [
                    f"- **Name:** {ld.get('name', 'N/A')}",
                    f"- **Job Title:** {ld.get('jobTitle', 'N/A')}",
                    f"- **Description:** {ld.get('description', 'N/A')}",
                    f"- **Email:** {ld.get('email', 'N/A')}",
                ]
            )
            if ld.get("sameAs"):
                lines.append("\n**Social Links:**")
                for link in ld["sameAs"]:
                    lines.append(f"- {link}")
        if not lines:
            return None
        return Section("Professional Profile", "\n".join(lines))

    def _open_graph(self, content: "ExtractedContent") -> Section | None:
        """Generate Open Graph data section."""
        return self._dict_section("Open Graph Data", content.open_graph)

    def _meta_info(self, content: "ExtractedContent") -> Section | None:
        """Generate meta information section."""
        return self._dict_section("Meta Information", content.meta_tags)

    def _dict_section(self, title: str, data: dict[str, str]) -> Section | None:
        """Format a dict as a section with key-value list."""
        if not data:
            return None
        lines = [f"- **{key}:** {value}" for key, value in data.items()]
        return Section(title, "\n".join(lines))

    def _js_projects(self, js_content: "JSContent") -> Section | None:
        """Generate featured projects section from JS data."""
        if not js_content.projects:
            return None
        lines: list[str] = []
        for proj in js_content.projects:
            lines.append(f"### {proj.get('name', 'Untitled')}")
            lines.append(f"- **Description:** {proj.get('description', 'N/A')}")
            if proj.get("url"):
                lines.append(f"- **Live URL:** {proj['url']}")
            if proj.get("github"):
                lines.append(f"- **GitHub:** {proj['github']}")
            lines.append("")
        return Section("Featured Projects", "\n".join(lines).rstrip())

    def _js_socials(self, js_content: "JSContent") -> Section | None:
        """Generate social links section from JS data."""
        if not js_content.socials:
            return None
        lines: list[str] = []
        for social in js_content.socials:
            name = social.get("name", "Link")
            url = social.get("url", "")
            if url:
                lines.append(f"- **{name}:** {url}")
        if not lines:
            return None
        return Section("Social Links", "\n".join(lines))

    def _js_bio(self, js_content: "JSContent") -> Section | None:
        """Generate about section from JS content bio."""
        if not js_content.bio:
            return None
        en_bio = js_content.bio.get("en", {})
        if not isinstance(en_bio, dict):
            return None

        bio_text = en_bio.get("bio", "")
        subtitle = en_bio.get("subtitle", "")

        if not (bio_text or subtitle):
            return None

        lines: list[str] = []
        if subtitle:
            lines.append(f"**Role:** {subtitle}")
        if bio_text:
            lines.append(bio_text)
        return Section("About", "\n\n".join(lines))

    def _html_sections(self, content: "ExtractedContent") -> list[Section]:
        """Generate sections extracted from HTML."""
        if not content.sections:
            return []
        return [
            Section(name.title(), text)
            for name, text in content.sections.items()
        ]

    def _fallback_content(
        self,
        content: "ExtractedContent",
        js_content: "JSContent",
    ) -> list[Section]:
        """Use headings/paragraphs if no sections or projects found."""
        if content.sections or js_content.projects:
            return []

        sections: list[Section] = []
        if content.headings:
            lines: list[str] = []
            for heading in content.headings:
                level = int(heading["level"][1])
                prefix = "#" * (level + 1)
                lines.append(f"{prefix} {heading['text']}")
            sections.append(Section("Content Structure", "\n".join(lines)))

        if content.paragraphs:
            text = "\n\n".join(content.paragraphs[: self.MAX_PARAGRAPHS])
            sections.append(Section("Main Content", text))

        return sections

    def _all_links(self, content: "ExtractedContent") -> Section | None:
        """Generate all links section."""
        if not content.links:
            return None

        seen: set[tuple[str, str]] = set()
        lines: list[str] = []
        for link in content.links:
            key = (link["text"], link["href"])
            if key not in seen and link["text"]:
                seen.add(key)
                lines.append(f"- [{link['text']}]({link['href']})")
        if not lines:
            return None
        return Section("All Links", "\n".join(lines))
