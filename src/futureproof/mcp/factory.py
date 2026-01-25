"""MCP client factory.

Follows the same factory pattern as LLMFactory for consistency.
"""

from typing import Literal

from ..config import settings
from .base import MCPClient

# Career data sources
CareerMCPType = Literal["github", "gitlab"]

# Market intelligence sources
MarketMCPType = Literal["hn", "brave", "jobspy"]

# All MCP server types
MCPServerType = Literal["github", "gitlab", "hn", "brave", "jobspy"]


class MCPClientFactory:
    """Factory for creating MCP clients.

    Mirrors the LLMFactory pattern for consistency across the codebase.
    Supports both career data sources (GitHub, GitLab) and market intelligence
    sources (Hacker News, Brave Search, JobSpy).
    """

    # Lazy-loaded to avoid circular imports
    _clients: dict[str, type[MCPClient]] | None = None

    @classmethod
    def _get_clients(cls) -> dict[str, type[MCPClient]]:
        """Lazy-load client classes to avoid circular imports."""
        if cls._clients is None:
            from .brave_client import BraveSearchMCPClient
            from .github_client import GitHubMCPClient
            from .gitlab_client import GitLabMCPClient
            from .hn_client import HackerNewsMCPClient
            from .jobspy_client import JobSpyMCPClient

            cls._clients = {
                # Career data sources
                "github": GitHubMCPClient,
                "gitlab": GitLabMCPClient,
                # Market intelligence sources
                "hn": HackerNewsMCPClient,
                "brave": BraveSearchMCPClient,
                "jobspy": JobSpyMCPClient,
            }
        return cls._clients

    @classmethod
    def create(cls, server_type: MCPServerType) -> MCPClient:
        """Create an MCP client instance.

        Args:
            server_type: Type of MCP server to connect to

        Returns:
            Configured MCPClient instance

        Raises:
            ValueError: If server type is unknown
        """
        clients = cls._get_clients()
        if server_type not in clients:
            raise ValueError(
                f"Unknown MCP server: {server_type}. Available: {list(clients.keys())}"
            )

        client_class = clients[server_type]
        return client_class()

    @classmethod
    def is_available(cls, server_type: MCPServerType) -> bool:
        """Check if MCP server is configured and available.

        Args:
            server_type: Type of MCP server

        Returns:
            True if server can be used
        """
        # Career data sources
        if server_type == "github":
            return settings.has_github_mcp
        elif server_type == "gitlab":
            return settings.has_gitlab_mcp
        # Market intelligence sources
        elif server_type == "hn":
            return settings.hn_mcp_enabled
        elif server_type == "brave":
            return settings.has_brave_mcp
        elif server_type == "jobspy":
            return settings.jobspy_enabled
        return False

    @classmethod
    def get_available_market_sources(cls) -> list[MarketMCPType]:
        """Get list of available market intelligence sources.

        Returns:
            List of available market MCP types
        """
        available: list[MarketMCPType] = []
        market_types: list[MarketMCPType] = ["hn", "brave", "jobspy"]
        for source in market_types:
            if cls.is_available(source):
                available.append(source)
        return available

    @classmethod
    def get_available_career_sources(cls) -> list[CareerMCPType]:
        """Get list of available career data sources.

        Returns:
            List of available career MCP types
        """
        available: list[CareerMCPType] = []
        career_types: list[CareerMCPType] = ["github", "gitlab"]
        for source in career_types:
            if cls.is_available(source):
                available.append(source)
        return available
