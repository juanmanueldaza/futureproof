"""Market intelligence gatherers.

These gatherers collect market data from various MCP sources and cache
the results for performance. Each gatherer has its own TTL based on
how frequently the data changes.

Gatherers:
- TechTrendsGatherer: Tech trends from HN (24h cache)
- JobMarketGatherer: Job listings from JobSpy, RemoteOK, Himalayas, Jobicy (12h cache)
- ContentTrendsGatherer: Content trends from Dev.to and Stack Overflow (12h cache)
"""

from .base import MarketGatherer
from .content_trends_gatherer import ContentTrendsGatherer
from .job_market_gatherer import JobMarketGatherer
from .source_registry import JOB_SOURCE_REGISTRY, SALARY_SOURCE, JobSourceConfig
from .tech_trends_gatherer import TechTrendsGatherer

__all__ = [
    "ContentTrendsGatherer",
    "JOB_SOURCE_REGISTRY",
    "JobMarketGatherer",
    "JobSourceConfig",
    "MarketGatherer",
    "SALARY_SOURCE",
    "TechTrendsGatherer",
]
