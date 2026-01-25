"""Market intelligence gatherers.

These gatherers collect market data from various MCP sources and cache
the results for performance. Each gatherer has its own TTL based on
how frequently the data changes.

Gatherers:
- TechTrendsGatherer: Tech trends from HN and GitHub (24h cache)
- JobMarketGatherer: Job listings from JobSpy and Brave (12h cache)
"""

from .base import MarketGatherer
from .job_market_gatherer import JobMarketGatherer
from .tech_trends_gatherer import TechTrendsGatherer

__all__ = [
    "JobMarketGatherer",
    "MarketGatherer",
    "TechTrendsGatherer",
]
