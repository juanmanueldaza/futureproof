"""MCP client factory.

OCP-compliant: availability checking uses configuration dict instead of if-chain.
"""

from collections.abc import Callable
from typing import Literal

from ..config import settings
from .base import MCPClient

# All MCP server types
MCPServerType = Literal[
    "github",
    "gitlab",
    "hn",
    "tavily",
    "jobspy",
    "remoteok",
    "himalayas",
    "jobicy",
    "devto",
    "stackoverflow",
    "weworkremotely",
    "remotive",
]


class MCPClientFactory:
    """Factory for creating MCP clients.

    Supports both career data sources (GitHub, GitLab) and market intelligence
    sources (Hacker News, Brave Search, JobSpy).

    OCP-compliant: add new sources by updating AVAILABILITY_CHECKERS dict.
    """

    # Lazy-loaded to avoid circular imports
    _clients: dict[str, type[MCPClient]] | None = None

    # Availability checkers registry (OCP: add entries here, no code changes to is_available)
    # Maps server type to a callable that returns whether the server is available
    AVAILABILITY_CHECKERS: dict[str, Callable[[], bool]] = {
        # Career data sources (require authentication)
        "github": lambda: settings.has_github_mcp,
        "gitlab": lambda: settings.has_gitlab_mcp,
        # Market intelligence sources with auth
        "tavily": lambda: settings.has_tavily_mcp,
        "hn": lambda: settings.hn_mcp_enabled,
        "jobspy": lambda: settings.jobspy_enabled,
        # Sources that are always available (no auth required)
        "remoteok": lambda: True,
        "himalayas": lambda: True,
        "jobicy": lambda: True,
        "devto": lambda: True,
        "weworkremotely": lambda: True,
        "remotive": lambda: True,
        "stackoverflow": lambda: True,  # 300/day without key
    }

    @classmethod
    def _get_clients(cls) -> dict[str, type[MCPClient]]:
        """Lazy-load client classes to avoid circular imports."""
        if cls._clients is None:
            from .devto_client import DevToMCPClient
            from .github_client import GitHubMCPClient
            from .gitlab_client import GitLabMCPClient
            from .himalayas_client import HimalayasMCPClient
            from .hn_client import HackerNewsMCPClient
            from .jobicy_client import JobicyMCPClient
            from .jobspy_client import JobSpyMCPClient
            from .remoteok_client import RemoteOKMCPClient
            from .remotive_client import RemotiveMCPClient
            from .stackoverflow_client import StackOverflowMCPClient
            from .tavily_client import TavilyMCPClient
            from .weworkremotely_client import WeWorkRemotelyMCPClient

            cls._clients = {
                # Career data sources
                "github": GitHubMCPClient,
                "gitlab": GitLabMCPClient,
                # Market intelligence sources
                "hn": HackerNewsMCPClient,
                "tavily": TavilyMCPClient,
                "jobspy": JobSpyMCPClient,
                "remoteok": RemoteOKMCPClient,
                # Additional market intelligence sources
                "himalayas": HimalayasMCPClient,
                "jobicy": JobicyMCPClient,
                "devto": DevToMCPClient,
                "stackoverflow": StackOverflowMCPClient,
                # RSS-based job sources (better salary data)
                "weworkremotely": WeWorkRemotelyMCPClient,
                "remotive": RemotiveMCPClient,
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

        OCP-compliant: uses AVAILABILITY_CHECKERS registry instead of if-chain.

        Args:
            server_type: Type of MCP server

        Returns:
            True if server can be used
        """
        checker = cls.AVAILABILITY_CHECKERS.get(server_type)
        if checker is None:
            return False
        return checker()
