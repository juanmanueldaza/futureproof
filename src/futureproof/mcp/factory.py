"""MCP client factory.

Follows the same factory pattern as LLMFactory for consistency.
"""

from typing import Literal

from ..config import settings
from .base import MCPClient

MCPServerType = Literal["github", "gitlab"]


class MCPClientFactory:
    """Factory for creating MCP clients.

    Mirrors the LLMFactory pattern for consistency across the codebase.
    """

    # Lazy-loaded to avoid circular imports
    _clients: dict[str, type[MCPClient]] | None = None

    @classmethod
    def _get_clients(cls) -> dict[str, type[MCPClient]]:
        """Lazy-load client classes to avoid circular imports."""
        if cls._clients is None:
            from .github_client import GitHubMCPClient
            from .gitlab_client import GitLabMCPClient

            cls._clients = {
                "github": GitHubMCPClient,
                "gitlab": GitLabMCPClient,
            }
        return cls._clients

    @classmethod
    def create(cls, server_type: MCPServerType) -> MCPClient:
        """Create an MCP client instance.

        Args:
            server_type: Type of MCP server to connect to ("github" or "gitlab")

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
        if server_type == "github":
            return settings.has_github_mcp
        elif server_type == "gitlab":
            return settings.has_gitlab_mcp
        return False
