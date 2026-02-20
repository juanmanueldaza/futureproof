"""Portfolio gatherer - coordinator class.

Orchestrates the extraction process using specialized components.
"""

from ...config import settings
from ...memory.chunker import Section
from ...utils.logging import get_logger
from .fetcher import PortfolioFetcher
from .html_extractor import HTMLExtractor
from .js_extractor import JSExtractor
from .markdown_writer import PortfolioMarkdownWriter

logger = get_logger(__name__)


class PortfolioGatherer:
    """Gather data from personal portfolio website.

    This class coordinates the extraction process using specialized components:
    - PortfolioFetcher: HTTP requests
    - HTMLExtractor: HTML parsing
    - JSExtractor: JavaScript content
    - PortfolioMarkdownWriter: Section generation

    Follows Dependency Inversion Principle - components can be injected for testing.
    """

    def __init__(
        self,
        fetcher: PortfolioFetcher | None = None,
        html_extractor: HTMLExtractor | None = None,
        js_extractor: JSExtractor | None = None,
        markdown_writer: PortfolioMarkdownWriter | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._html_extractor = html_extractor or HTMLExtractor()
        self._js_extractor = js_extractor or JSExtractor()
        self._markdown_writer = markdown_writer or PortfolioMarkdownWriter()

    def gather(self, url: str | None = None) -> list[Section]:
        """Gather data from portfolio website.

        Args:
            url: Portfolio URL (defaults to config)

        Returns:
            List of Section(name, content) tuples
        """
        target_url = url or settings.portfolio_url

        logger.info("Gathering portfolio from %s", target_url)

        with (self._fetcher or PortfolioFetcher()) as fetcher:
            html_result = fetcher.fetch(target_url)
            logger.debug("Fetched %d bytes", len(html_result.content))

            content = self._html_extractor.extract(html_result.content, target_url)
            logger.debug("Extracted %d paragraphs, %d sections",
                         len(content.paragraphs), len(content.sections))

            if content.json_ld:
                logger.debug("Found %d JSON-LD blocks", len(content.json_ld))

            js_content = self._js_extractor.extract(
                html_result.content,
                target_url,
                fetcher,
            )
            if js_content.projects:
                logger.debug("Found %d projects from JS", len(js_content.projects))
            if js_content.socials:
                logger.debug("Found %d social links from JS", len(js_content.socials))

        sections = self._markdown_writer.generate(content, js_content)

        logger.info("Portfolio gathered successfully from %s", target_url)
        return sections
