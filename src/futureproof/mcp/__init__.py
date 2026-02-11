"""MCP (Model Context Protocol) client implementations.

Provides clients for connecting to MCP servers like GitHub and GitLab
for real-time data access instead of CLI-based gathering.

Also provides market intelligence clients:
- Hacker News: Tech trends and job postings
- Tavily: Web search for salary data and market research
- JobSpy: Multi-platform job aggregation (LinkedIn, Indeed, Glassdoor, ZipRecruiter)
- RemoteOK: Remote-only job listings
- Dice: Tech-focused job database
- WeWorkRemotely: RSS-based remote jobs with salary data
- Remotive: Remote jobs API with tags and location data
"""

from .base import MCPClient, MCPClientError, MCPConnectionError, MCPToolError, MCPToolResult
from .devto_client import DevToMCPClient
from .dice_client import DiceMCPClient
from .factory import CareerMCPType, MarketMCPType, MCPClientFactory, MCPServerType
from .github_client import GitHubMCPClient
from .gitlab_client import GitLabMCPClient
from .hn_client import HackerNewsMCPClient
from .http_client import HTTPMCPClient
from .job_schema import (
    JobNormalizer,
    NormalizedJob,
    SalaryInfo,
    attach_salary,
    clean_html_description,
    clean_html_entities,
    generate_job_id,
    parse_company_title,
)
from .jobspy_client import JobSpyMCPClient
from .remoteok_client import RemoteOKMCPClient
from .remotive_client import RemotiveMCPClient
from .tavily_client import TavilyMCPClient
from .weworkremotely_client import WeWorkRemotelyMCPClient

__all__ = [
    # Base classes and errors
    "HTTPMCPClient",
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
    # Job schema and normalizers
    "JobNormalizer",
    "NormalizedJob",
    "SalaryInfo",
    "attach_salary",
    "clean_html_description",
    "clean_html_entities",
    "generate_job_id",
    "parse_company_title",
    # Career data clients
    "GitHubMCPClient",
    "GitLabMCPClient",
    # Market intelligence clients
    "DevToMCPClient",
    "DiceMCPClient",
    "HackerNewsMCPClient",
    "JobSpyMCPClient",
    "RemoteOKMCPClient",
    "RemotiveMCPClient",
    "TavilyMCPClient",
    "WeWorkRemotelyMCPClient",
]
