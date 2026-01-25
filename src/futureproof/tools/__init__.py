"""LangChain tools for FutureProof.

Tools are LLM-callable functions that can be invoked during analysis
when the model needs more data. This enables dynamic data retrieval
based on analysis context.

Available tools:
- Market data tools: Job search, tech trends, salary research, hiring trends
"""

from .market import (
    ALL_MARKET_TOOLS,
    get_available_tools,
    get_tech_trends,
    search_hiring_trends,
    search_jobs,
    search_salary_data,
)

__all__ = [
    # Individual tools
    "get_tech_trends",
    "search_hiring_trends",
    "search_jobs",
    "search_salary_data",
    # Tool collections
    "ALL_MARKET_TOOLS",
    "get_available_tools",
]
