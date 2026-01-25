"""GitHub MCP client implementation.

Uses stdio transport with Docker or native binary to communicate
with the official GitHub MCP server.
"""

import logging
from typing import Any

from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from ..config import settings
from .base import MCPClient, MCPConnectionError, MCPToolError, MCPToolResult

logger = logging.getLogger(__name__)


class GitHubMCPClient(MCPClient):
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

    def __init__(self) -> None:
        self._session: ClientSession | None = None
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

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call a GitHub MCP tool."""
        if self._session is None:
            raise MCPConnectionError("Not connected to GitHub MCP server")

        try:
            result = await self._session.call_tool(tool_name, arguments)

            # Extract text content from result
            content_parts = []
            for content in result.content:
                if isinstance(content, types.TextContent):
                    content_parts.append(content.text)

            is_error = getattr(result, "isError", False)

            return MCPToolResult(
                content="\n".join(content_parts),
                raw_response=result,
                tool_name=tool_name,
                is_error=is_error,
            )

        except Exception as e:
            raise MCPToolError(f"GitHub MCP tool '{tool_name}' failed: {e}") from e

    async def list_tools(self) -> list[str]:
        """List available GitHub MCP tools."""
        if self._session is None:
            raise MCPConnectionError("Not connected to GitHub MCP server")

        tools = await self._session.list_tools()
        return [tool.name for tool in tools.tools]

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._session is not None

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

    async def get_repo_commits(
        self,
        owner: str,
        repo: str,
        per_page: int = 100,
    ) -> MCPToolResult:
        """Get recent commits for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            per_page: Number of commits to fetch

        Returns:
            MCPToolResult with commit list
        """
        return await self.call_tool(
            "list_commits",
            {
                "owner": owner,
                "repo": repo,
                "perPage": per_page,
            },
        )

    async def search_user_repos(self, username: str, per_page: int = 100) -> MCPToolResult:
        """Search for repositories by a specific user.

        Args:
            username: GitHub username
            per_page: Number of results

        Returns:
            MCPToolResult with search results
        """
        return await self.call_tool(
            "search_repositories",
            {
                "query": f"user:{username}",
                "perPage": per_page,
            },
        )

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
