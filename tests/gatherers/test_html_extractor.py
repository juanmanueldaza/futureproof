"""Tests for HTML content extraction."""

import pytest

from futureproof.gatherers.portfolio.html_extractor import ExtractedContent, HTMLExtractor


class TestHTMLExtractor:
    """Test HTMLExtractor class."""

    @pytest.fixture
    def extractor(self) -> HTMLExtractor:
        return HTMLExtractor()

    @pytest.fixture
    def sample_html(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>John Doe - Developer</title>
            <meta name="description" content="Full-stack developer with 5 years experience">
            <meta property="og:title" content="John Doe Portfolio">
            <meta property="og:description" content="My portfolio site">
            <meta name="twitter:card" content="summary">
            <meta name="twitter:title" content="John Doe">
            <meta name="author" content="John Doe">
            <meta name="keywords" content="developer, python, javascript">
            <script type="application/ld+json">
            {"@type": "Person", "name": "John Doe", "jobTitle": "Developer"}
            </script>
        </head>
        <body>
            <h1>Welcome to my portfolio</h1>
            <h2>About Me</h2>
            <p>This is a long enough paragraph to be included in the extraction process.</p>
            <p>Short</p>
            <section id="about">About section content goes here with some details.</section>
            <section class="projects-section">Projects content here.</section>
            <a href="https://github.com/johndoe">GitHub Profile</a>
            <a href="#top">Back to top</a>
        </body>
        </html>
        """

    def test_returns_extracted_content(self, extractor: HTMLExtractor, sample_html: str) -> None:
        """Test that extract returns ExtractedContent dataclass."""
        result = extractor.extract(sample_html, "https://example.com")
        assert isinstance(result, ExtractedContent)

    def test_extracts_url(self, extractor: HTMLExtractor, sample_html: str) -> None:
        """Test URL is stored in result."""
        result = extractor.extract(sample_html, "https://example.com")
        assert result.url == "https://example.com"

    def test_extracts_title(self, extractor: HTMLExtractor, sample_html: str) -> None:
        """Test title extraction."""
        result = extractor.extract(sample_html, "https://example.com")
        assert result.title == "John Doe - Developer"

    def test_extracts_meta_description(self, extractor: HTMLExtractor, sample_html: str) -> None:
        """Test meta description extraction."""
        result = extractor.extract(sample_html, "https://example.com")
        assert result.meta_description == "Full-stack developer with 5 years experience"

    def test_extracts_json_ld(self, extractor: HTMLExtractor, sample_html: str) -> None:
        """Test JSON-LD structured data extraction."""
        result = extractor.extract(sample_html, "https://example.com")
        assert len(result.json_ld) == 1
        assert result.json_ld[0]["@type"] == "Person"
        assert result.json_ld[0]["name"] == "John Doe"

    def test_extracts_open_graph(self, extractor: HTMLExtractor, sample_html: str) -> None:
        """Test Open Graph meta tag extraction."""
        result = extractor.extract(sample_html, "https://example.com")
        assert result.open_graph["title"] == "John Doe Portfolio"
        assert result.open_graph["description"] == "My portfolio site"

    def test_extracts_other_meta(self, extractor: HTMLExtractor, sample_html: str) -> None:
        """Test other meta tag extraction (author, keywords)."""
        result = extractor.extract(sample_html, "https://example.com")
        assert result.meta_tags["author"] == "John Doe"
        assert result.meta_tags["keywords"] == "developer, python, javascript"

    def test_extracts_headings(self, extractor: HTMLExtractor, sample_html: str) -> None:
        """Test heading extraction."""
        result = extractor.extract(sample_html, "https://example.com")
        assert len(result.headings) >= 2
        h1_headings = [h for h in result.headings if h["level"] == "h1"]
        assert any("Welcome" in h["text"] for h in h1_headings)

    def test_extracts_paragraphs_with_min_length(
        self, extractor: HTMLExtractor, sample_html: str
    ) -> None:
        """Test paragraph extraction filters short paragraphs."""
        result = extractor.extract(sample_html, "https://example.com")
        # "Short" paragraph should be filtered out
        assert all(len(p) > 20 for p in result.paragraphs)
        assert any("long enough" in p for p in result.paragraphs)

    def test_extracts_links_excluding_anchors(
        self, extractor: HTMLExtractor, sample_html: str
    ) -> None:
        """Test link extraction excludes anchor links."""
        result = extractor.extract(sample_html, "https://example.com")
        # GitHub link should be included
        github_links = [link for link in result.links if "github" in link["href"]]
        assert len(github_links) == 1
        # Anchor link (#top) should be excluded
        anchor_links = [link for link in result.links if link["href"].startswith("#")]
        assert len(anchor_links) == 0

    def test_extracts_sections_by_id(self, extractor: HTMLExtractor, sample_html: str) -> None:
        """Test section extraction by id pattern."""
        result = extractor.extract(sample_html, "https://example.com")
        assert "about" in result.sections
        assert "About section content" in result.sections["about"]

    def test_extracts_sections_by_class(self, extractor: HTMLExtractor, sample_html: str) -> None:
        """Test section extraction by class pattern."""
        result = extractor.extract(sample_html, "https://example.com")
        assert "projects" in result.sections
        assert "Projects content" in result.sections["projects"]

    def test_handles_missing_elements_gracefully(self, extractor: HTMLExtractor) -> None:
        """Test handling of minimal HTML without optional elements."""
        minimal_html = "<html><body><p>Hello world</p></body></html>"
        result = extractor.extract(minimal_html, "https://example.com")

        assert result.title == ""
        assert result.meta_description == ""
        assert result.json_ld == []
        assert result.open_graph == {}
        assert result.sections == {}

    def test_handles_malformed_json_ld(self, extractor: HTMLExtractor) -> None:
        """Test handling of malformed JSON-LD."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {invalid json here}
            </script>
        </head>
        <body></body>
        </html>
        """
        result = extractor.extract(html, "https://example.com")
        assert result.json_ld == []  # Should gracefully handle parse error
