"""Data gatherers for various professional platforms."""

from .base import BaseGatherer, CLIGatherer, MCPGatherer
from .github import GitHubCLIGatherer, GitHubGatherer
from .gitlab import GitLabCLIGatherer, GitLabGatherer
from .linkedin import LinkedInGatherer
from .market import JobMarketGatherer, MarketGatherer, TechTrendsGatherer
from .portfolio import PortfolioGatherer

__all__ = [
    # Base classes
    "BaseGatherer",
    "CLIGatherer",
    "MCPGatherer",
    # Career data gatherers
    "GitHubCLIGatherer",
    "GitHubGatherer",
    "GitLabCLIGatherer",
    "GitLabGatherer",
    "LinkedInGatherer",
    "PortfolioGatherer",
    # Market intelligence gatherers
    "MarketGatherer",
    "JobMarketGatherer",
    "TechTrendsGatherer",
]
