"""Portfolio gatherer - coordinator class.

Orchestrates the extraction process using specialized components.
"""

import os
from pathlib import Path

from ...config import settings
from ...utils.console import console
from ...utils.logging import get_logger
from ..base import BaseGatherer
from .fetcher import PortfolioFetcher
from .html_extractor import HTMLExtractor
from .js_extractor import JSExtractor
from .markdown_writer import PortfolioMarkdownWriter

logger = get_logger(__name__)


class PortfolioGatherer(BaseGatherer):
    """Gather data from personal portfolio website.

    This class coordinates the extraction process using specialized components:
    - PortfolioFetcher: HTTP requests
    - HTMLExtractor: HTML parsing
    - JSExtractor: JavaScript content
    - PortfolioMarkdownWriter: Output generation

    Follows Dependency Inversion Principle - components can be injected for testing.
    """

    def __init__(
        self,
        fetcher: PortfolioFetcher | None = None,
        html_extractor: HTMLExtractor | None = None,
        js_extractor: JSExtractor | None = None,
        markdown_writer: PortfolioMarkdownWriter | None = None,
    ) -> None:
        """Initialize gatherer with optional dependency injection.

        Args:
            fetcher: HTTP fetcher (created if not provided)
            html_extractor: HTML parser (created if not provided)
            js_extractor: JS parser (created if not provided)
            markdown_writer: Markdown generator (created if not provided)
        """
        self.output_dir = settings.processed_dir / "portfolio"
        self._fetcher = fetcher
        self._html_extractor = html_extractor or HTMLExtractor()
        self._js_extractor = js_extractor or JSExtractor()
        self._markdown_writer = markdown_writer or PortfolioMarkdownWriter()

    def gather(self, url: str | None = None) -> Path:
        """Gather data from portfolio website.

        Args:
            url: Portfolio URL (defaults to config)

        Returns:
            Path to the generated markdown file
        """
        target_url = url or settings.portfolio_url
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Gathering portfolio from %s", target_url)
        console.print(f"  Fetching: {target_url}")

        with PortfolioFetcher() as fetcher:
            # Fetch HTML
            html_result = fetcher.fetch(target_url)
            console.print(f"  [dim]Fetched {len(html_result.content)} bytes[/dim]")

            # Extract HTML content
            content = self._html_extractor.extract(html_result.content, target_url)
            console.print(f"  [dim]Extracted {len(content.paragraphs)} paragraphs[/dim]")
            console.print(f"  [dim]Found {len(content.sections)} sections[/dim]")

            if content.json_ld:
                console.print(f"  [dim]Found {len(content.json_ld)} JSON-LD blocks[/dim]")

            # Extract JS content
            js_content = self._js_extractor.extract(
                html_result.content,
                target_url,
                fetcher,
            )
            if js_content.projects:
                console.print(f"  [dim]Found {len(js_content.projects)} projects from JS[/dim]")
            if js_content.socials:
                console.print(f"  [dim]Found {len(js_content.socials)} social links from JS[/dim]")

        # Generate markdown
        markdown = self._markdown_writer.generate(content, js_content)

        # Save outputs with secure permissions (owner read/write only)
        output_file = self.output_dir / "portfolio.md"
        output_file.write_text(markdown)
        os.chmod(output_file, 0o600)
        console.print(f"  Saved to: {output_file}")

        # Note: Raw JSON debug file removed for security (contained PII)
        # If debugging needed, use logging instead

        logger.info("Portfolio gathered successfully: %s", output_file)
        return output_file
