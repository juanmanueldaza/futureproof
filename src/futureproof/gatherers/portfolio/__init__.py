"""Portfolio gathering components following Single Responsibility Principle."""

from .fetcher import FetchResult, PortfolioFetcher
from .gatherer import PortfolioGatherer
from .html_extractor import ExtractedContent, HTMLExtractor
from .js_extractor import JSContent, JSExtractor
from .markdown_writer import PortfolioMarkdownWriter

__all__ = [
    "ExtractedContent",
    "FetchResult",
    "HTMLExtractor",
    "JSContent",
    "JSExtractor",
    "PortfolioFetcher",
    "PortfolioGatherer",
    "PortfolioMarkdownWriter",
]
