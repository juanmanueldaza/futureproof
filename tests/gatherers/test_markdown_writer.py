"""Tests for portfolio section generation."""

import pytest

from futureproof.gatherers.portfolio.html_extractor import ExtractedContent
from futureproof.gatherers.portfolio.js_extractor import JSContent
from futureproof.gatherers.portfolio.markdown_writer import PortfolioMarkdownWriter
from futureproof.memory.chunker import Section


def _find(sections: list[Section], name: str) -> Section | None:
    """Find a section by name."""
    return next((s for s in sections if s.name == name), None)


class TestPortfolioMarkdownWriter:
    """Test PortfolioMarkdownWriter class."""

    @pytest.fixture
    def writer(self) -> PortfolioMarkdownWriter:
        return PortfolioMarkdownWriter()

    @pytest.fixture
    def sample_content(self) -> ExtractedContent:
        return ExtractedContent(
            url="https://example.com",
            title="John Doe - Developer",
            meta_description="Full-stack developer portfolio",
            headings=[
                {"level": "h1", "text": "Welcome"},
                {"level": "h2", "text": "About"},
            ],
            paragraphs=["This is a paragraph about my work."],
            links=[{"text": "GitHub", "href": "https://github.com/johndoe"}],
            sections={"about": "About section content"},
            json_ld=[
                {
                    "@type": "Person",
                    "name": "John Doe",
                    "jobTitle": "Developer",
                    "description": "A developer",
                    "email": "john@example.com",
                    "sameAs": ["https://github.com/johndoe"],
                }
            ],
            open_graph={"title": "John Doe", "description": "Portfolio"},
            meta_tags={"author": "John Doe"},
        )

    @pytest.fixture
    def sample_js_content(self) -> JSContent:
        return JSContent(
            projects=[
                {
                    "name": "Project A",
                    "description": "A cool project",
                    "url": "https://project-a.com",
                    "github": "https://github.com/johndoe/project-a",
                }
            ],
            socials=[{"name": "GitHub", "url": "https://github.com/johndoe"}],
            bio={"en": {"bio": "I am a developer", "subtitle": "Senior Engineer"}},
        )

    @pytest.fixture
    def empty_js_content(self) -> JSContent:
        return JSContent()

    def test_returns_section_list(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        sample_js_content: JSContent,
    ) -> None:
        """Test that generate returns a list of Section tuples."""
        result = writer.generate(sample_content, sample_js_content)
        assert isinstance(result, list)
        assert all(isinstance(s, Section) for s in result)

    def test_includes_header_with_title(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test header includes title and URL."""
        result = writer.generate(sample_content, empty_js_content)
        header = _find(result, "Header")
        assert header is not None
        assert "John Doe - Developer" in header.content
        assert "**URL:** https://example.com" in header.content
        assert "**Scraped:**" in header.content

    def test_includes_description(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test meta description is included."""
        result = writer.generate(sample_content, empty_js_content)
        desc = _find(result, "Description")
        assert desc is not None
        assert "Full-stack developer portfolio" in desc.content

    def test_includes_json_ld_person(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test JSON-LD Person data is included."""
        result = writer.generate(sample_content, empty_js_content)
        profile = _find(result, "Professional Profile")
        assert profile is not None
        assert "**Name:** John Doe" in profile.content
        assert "**Job Title:** Developer" in profile.content
        assert "**Email:** john@example.com" in profile.content

    def test_includes_open_graph(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test Open Graph data is included."""
        result = writer.generate(sample_content, empty_js_content)
        og = _find(result, "Open Graph Data")
        assert og is not None
        assert "**title:** John Doe" in og.content

    def test_includes_meta_info(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test meta information is included."""
        result = writer.generate(sample_content, empty_js_content)
        meta = _find(result, "Meta Information")
        assert meta is not None
        assert "**author:** John Doe" in meta.content

    def test_includes_js_projects(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        sample_js_content: JSContent,
    ) -> None:
        """Test JS projects are included."""
        result = writer.generate(sample_content, sample_js_content)
        projects = _find(result, "Featured Projects")
        assert projects is not None
        assert "### Project A" in projects.content
        assert "**Description:** A cool project" in projects.content
        assert "**Live URL:** https://project-a.com" in projects.content
        assert "**GitHub:** https://github.com/johndoe/project-a" in projects.content

    def test_includes_js_socials(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        sample_js_content: JSContent,
    ) -> None:
        """Test JS social links are included."""
        result = writer.generate(sample_content, sample_js_content)
        socials = _find(result, "Social Links")
        assert socials is not None
        assert "**GitHub:** https://github.com/johndoe" in socials.content

    def test_includes_js_bio(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        sample_js_content: JSContent,
    ) -> None:
        """Test JS bio is included."""
        result = writer.generate(sample_content, sample_js_content)
        about = _find(result, "About")
        assert about is not None
        assert "**Role:** Senior Engineer" in about.content
        assert "I am a developer" in about.content

    def test_includes_html_sections(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test HTML sections are included."""
        result = writer.generate(sample_content, empty_js_content)
        about = _find(result, "About")
        assert about is not None
        assert "About section content" in about.content

    def test_includes_all_links(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test all links section is included."""
        result = writer.generate(sample_content, empty_js_content)
        links = _find(result, "All Links")
        assert links is not None
        assert "[GitHub](https://github.com/johndoe)" in links.content

    def test_fallback_content_when_no_sections(self, writer: PortfolioMarkdownWriter) -> None:
        """Test fallback content (headings/paragraphs) when no sections or projects."""
        content = ExtractedContent(
            url="https://example.com",
            title="Simple Site",
            headings=[{"level": "h1", "text": "Main Heading"}],
            paragraphs=["This is a paragraph."],
        )
        js_content = JSContent()

        result = writer.generate(content, js_content)
        names = {s.name for s in result}
        assert "Content Structure" in names
        assert "Main Content" in names

        structure = _find(result, "Content Structure")
        assert structure is not None
        assert "Main Heading" in structure.content

        main = _find(result, "Main Content")
        assert main is not None
        assert "This is a paragraph." in main.content

    def test_handles_empty_content(self, writer: PortfolioMarkdownWriter) -> None:
        """Test handling of completely empty content."""
        content = ExtractedContent(url="https://example.com")
        js_content = JSContent()

        result = writer.generate(content, js_content)
        # Should have at least the header section
        header = _find(result, "Header")
        assert header is not None
        assert "**URL:** https://example.com" in header.content
