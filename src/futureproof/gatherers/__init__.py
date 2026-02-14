"""Data gatherers for various professional platforms."""

from .base import BaseGatherer
from .linkedin import LinkedInGatherer
from .market import JobMarketGatherer, MarketGatherer, TechTrendsGatherer
from .portfolio import PortfolioGatherer

__all__ = [
    # Base classes
    "BaseGatherer",
    # Career data gatherers
    "LinkedInGatherer",
    "PortfolioGatherer",
    # Market intelligence gatherers
    "MarketGatherer",
    "JobMarketGatherer",
    "TechTrendsGatherer",
]
