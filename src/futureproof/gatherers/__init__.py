"""Data gatherers for various professional platforms."""

from .base import BaseGatherer, CLIGatherer
from .linkedin import LinkedInGatherer
from .market import JobMarketGatherer, MarketGatherer, TechTrendsGatherer
from .portfolio import PortfolioGatherer

__all__ = [
    # Base classes
    "BaseGatherer",
    "CLIGatherer",
    # Career data gatherers
    "LinkedInGatherer",
    "PortfolioGatherer",
    # Market intelligence gatherers
    "MarketGatherer",
    "JobMarketGatherer",
    "TechTrendsGatherer",
]
