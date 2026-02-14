"""GitHub MCP client implementation.

Uses stdio transport with Docker or native binary to communicate
with the official GitHub MCP server.
"""

import logging
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from ..config import settings
from .base import MCPConnectionError, MCPToolResult, SessionMCPClient

logger = logging.getLogger(__name__)


class GitHubMCPClient(SessionMCPClient):
    """MCP client for GitHub MCP Server.

    Uses stdio transport with Docker (default) or native binary.

    Environment:
        GITHUB_PERSONAL_ACCESS_TOKEN: GitHub PAT for authentication
        GITHUB_MCP_TOKEN: Alternative token setting

    Configuration:
        settings.github_mcp_use_docker: Use Docker container (default: True)
        settings.github_mcp_image: Docker image name
        settings.github_mcp_command: Native binary command
    """

    SERVER_NAME = "GitHub MCP"

    def __init__(self) -> None:
        super().__init__()
        self._stdio_context: Any = None
        self._read_stream: Any = None
        self._write_stream: Any = None

    def _get_server_params(self) -> StdioServerParameters:
        """Build server parameters based on configuration."""
        token = settings.github_mcp_token_resolved
        if not token:
            raise MCPConnectionError(
                "GitHub MCP token not configured. "
                "Set GITHUB_PERSONAL_ACCESS_TOKEN or GITHUB_MCP_TOKEN environment variable."
            )

        if settings.github_mcp_use_docker:
            return StdioServerParameters(
                command="docker",
                args=[
                    "run",
                    "-i",
                    "--rm",
                    "-e",
                    "GITHUB_PERSONAL_ACCESS_TOKEN",
                    settings.github_mcp_image,
                    "stdio",
                    "--log-file",
                    "/dev/null",  # Suppress server logs
                ],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": token},
            )
        else:
            # Native binary
            return StdioServerParameters(
                command=settings.github_mcp_command,
                args=[],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": token},
            )

    async def connect(self) -> None:
        """Connect to GitHub MCP server."""
        if self._session is not None:
            return  # Already connected

        try:
            server_params = self._get_server_params()

            # Enter stdio_client context
            self._stdio_context = stdio_client(server_params)
            self._read_stream, self._write_stream = await self._stdio_context.__aenter__()

            # Create session
            session = ClientSession(self._read_stream, self._write_stream)
            await session.__aenter__()
            await session.initialize()
            self._session = session

            logger.info("Connected to GitHub MCP server")

        except MCPConnectionError:
            await self.disconnect()
            raise
        except Exception as e:
            await self.disconnect()
            raise MCPConnectionError(f"Failed to connect to GitHub MCP server: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from GitHub MCP server."""
        if self._session is not None:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None

        if self._stdio_context is not None:
            try:
                await self._stdio_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._stdio_context = None

        self._read_stream = None
        self._write_stream = None

    # High-level convenience methods for career data gathering

    async def get_user_profile(self) -> MCPToolResult:
        """Get authenticated user's profile."""
        return await self.call_tool("get_me", {})

    async def list_user_repos(
        self,
        owner: str | None = None,
        per_page: int = 30,
    ) -> MCPToolResult:
        """List repositories for a user using search.

        Args:
            owner: Repository owner (username). If None, uses authenticated user.
            per_page: Number of results per page (max 100)

        Returns:
            MCPToolResult with repository list
        """
        # Use search_code or search via the repos toolset
        # The GitHub MCP server uses search_repositories for listing user repos
        query = f"user:{owner}" if owner else ""
        return await self.call_tool("search_repositories", {"query": query, "perPage": per_page})

    async def search_user_pull_requests(self, username: str, per_page: int = 100) -> MCPToolResult:
        """Search for pull requests authored by a user.

        Args:
            username: GitHub username
            per_page: Number of results

        Returns:
            MCPToolResult with PR search results
        """
        return await self.call_tool(
            "search_pull_requests",
            {
                "query": f"author:{username}",
                "perPage": per_page,
            },
        )

    async def search_user_issues(self, username: str, per_page: int = 100) -> MCPToolResult:
        """Search for issues authored by a user.

        Args:
            username: GitHub username
            per_page: Number of results

        Returns:
            MCPToolResult with issue search results
        """
        return await self.call_tool(
            "search_issues",
            {
                "query": f"author:{username}",
                "perPage": per_page,
            },
        )

    async def search_user_reviews(self, username: str, per_page: int = 100) -> MCPToolResult:
        """Search for PRs reviewed by a user.

        Args:
            username: GitHub username
            per_page: Number of results

        Returns:
            MCPToolResult with review search results
        """
        return await self.call_tool(
            "search_pull_requests",
            {
                "query": f"reviewed-by:{username}",
                "perPage": per_page,
            },
        )
