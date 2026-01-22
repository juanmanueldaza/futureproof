"""Tests for markdown generation."""

import pytest

from futureproof.gatherers.portfolio.html_extractor import ExtractedContent
from futureproof.gatherers.portfolio.js_extractor import JSContent
from futureproof.gatherers.portfolio.markdown_writer import PortfolioMarkdownWriter


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
            twitter_card={"card": "summary"},
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

    def test_generates_markdown_string(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        sample_js_content: JSContent,
    ) -> None:
        """Test that generate returns a string."""
        result = writer.generate(sample_content, sample_js_content)
        assert isinstance(result, str)

    def test_includes_header_with_title(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test header includes title and URL."""
        result = writer.generate(sample_content, empty_js_content)
        assert "# Portfolio: John Doe - Developer" in result
        assert "**URL:** https://example.com" in result
        assert "**Scraped:**" in result

    def test_includes_description(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test meta description is included."""
        result = writer.generate(sample_content, empty_js_content)
        assert "## Description" in result
        assert "Full-stack developer portfolio" in result

    def test_includes_json_ld_person(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test JSON-LD Person data is included."""
        result = writer.generate(sample_content, empty_js_content)
        assert "## Professional Profile" in result
        assert "**Name:** John Doe" in result
        assert "**Job Title:** Developer" in result
        assert "**Email:** john@example.com" in result

    def test_includes_open_graph(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test Open Graph data is included."""
        result = writer.generate(sample_content, empty_js_content)
        assert "## Open Graph Data" in result
        assert "**title:** John Doe" in result

    def test_includes_meta_info(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test meta information is included."""
        result = writer.generate(sample_content, empty_js_content)
        assert "## Meta Information" in result
        assert "**author:** John Doe" in result

    def test_includes_js_projects(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        sample_js_content: JSContent,
    ) -> None:
        """Test JS projects are included."""
        result = writer.generate(sample_content, sample_js_content)
        assert "## Featured Projects" in result
        assert "### Project A" in result
        assert "**Description:** A cool project" in result
        assert "**Live URL:** https://project-a.com" in result
        assert "**GitHub:** https://github.com/johndoe/project-a" in result

    def test_includes_js_socials(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        sample_js_content: JSContent,
    ) -> None:
        """Test JS social links are included."""
        result = writer.generate(sample_content, sample_js_content)
        assert "## Social Links" in result
        assert "**GitHub:** https://github.com/johndoe" in result

    def test_includes_js_bio(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        sample_js_content: JSContent,
    ) -> None:
        """Test JS bio is included."""
        result = writer.generate(sample_content, sample_js_content)
        assert "## About (from content)" in result
        assert "**Role:** Senior Engineer" in result
        assert "I am a developer" in result

    def test_includes_html_sections(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test HTML sections are included."""
        result = writer.generate(sample_content, empty_js_content)
        assert "## About" in result
        assert "About section content" in result

    def test_includes_all_links(
        self,
        writer: PortfolioMarkdownWriter,
        sample_content: ExtractedContent,
        empty_js_content: JSContent,
    ) -> None:
        """Test all links section is included."""
        result = writer.generate(sample_content, empty_js_content)
        assert "## All Links" in result
        assert "[GitHub](https://github.com/johndoe)" in result

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
        assert "## Content Structure" in result
        assert "## Main Heading" in result
        assert "## Main Content" in result
        assert "This is a paragraph." in result

    def test_handles_empty_content(self, writer: PortfolioMarkdownWriter) -> None:
        """Test handling of completely empty content."""
        content = ExtractedContent(url="https://example.com")
        js_content = JSContent()

        result = writer.generate(content, js_content)
        assert "# Portfolio:" in result
        assert "**URL:** https://example.com" in result
