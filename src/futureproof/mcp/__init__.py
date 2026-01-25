"""MCP (Model Context Protocol) client implementations.

Provides clients for connecting to MCP servers like GitHub and GitLab
for real-time data access instead of CLI-based gathering.

Also provides market intelligence clients:
- Hacker News: Tech trends and job postings
- Brave Search: Web search for salary data and job listings
- JobSpy: Multi-platform job aggregation
"""

from .base import MCPClient, MCPClientError, MCPConnectionError, MCPToolError, MCPToolResult
from .brave_client import BraveSearchMCPClient
from .factory import CareerMCPType, MarketMCPType, MCPClientFactory, MCPServerType
from .github_client import GitHubMCPClient
from .gitlab_client import GitLabMCPClient
from .hn_client import HackerNewsMCPClient
from .jobspy_client import JobSpyMCPClient

__all__ = [
    # Base classes and errors
    "MCPClient",
    "MCPClientError",
    "MCPClientFactory",
    "MCPConnectionError",
    "MCPToolError",
    "MCPToolResult",
    # Type aliases
    "CareerMCPType",
    "MarketMCPType",
    "MCPServerType",
    # Career data clients
    "GitHubMCPClient",
    "GitLabMCPClient",
    # Market intelligence clients
    "BraveSearchMCPClient",
    "HackerNewsMCPClient",
    "JobSpyMCPClient",
]
