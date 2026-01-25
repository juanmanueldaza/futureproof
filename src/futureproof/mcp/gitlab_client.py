"""GitLab MCP client implementation.

Uses streamable HTTP transport to communicate with the GitLab MCP server.
"""

import logging
from typing import Any

from mcp import types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from ..config import settings
from .base import MCPClient, MCPConnectionError, MCPToolError, MCPToolResult

logger = logging.getLogger(__name__)


class GitLabMCPClient(MCPClient):
    """MCP client for GitLab MCP Server.

    Uses streamable HTTP transport as recommended by GitLab.

    Configuration:
        settings.gitlab_mcp_url: GitLab MCP server URL (e.g., https://gitlab.com/api/v4/mcp)
        settings.gitlab_mcp_token: GitLab OAuth or personal access token
    """

    def __init__(self) -> None:
        self._session: ClientSession | None = None
        self._http_context: Any = None
        self._read_stream: Any = None
        self._write_stream: Any = None

    async def connect(self) -> None:
        """Connect to GitLab MCP server via HTTP."""
        if self._session is not None:
            return  # Already connected

        if not settings.gitlab_mcp_url:
            raise MCPConnectionError(
                "GitLab MCP URL not configured. Set GITLAB_MCP_URL environment variable."
            )

        if not settings.gitlab_mcp_token:
            raise MCPConnectionError(
                "GitLab MCP token not configured. Set GITLAB_MCP_TOKEN environment variable."
            )

        try:
            # Use streamable HTTP transport for GitLab
            self._http_context = streamablehttp_client(
                settings.gitlab_mcp_url,
                headers={"Authorization": f"Bearer {settings.gitlab_mcp_token}"},
            )
            # streamablehttp_client returns (read, write, session_id)
            self._read_stream, self._write_stream, _ = await self._http_context.__aenter__()

            session = ClientSession(self._read_stream, self._write_stream)
            await session.__aenter__()
            await session.initialize()
            self._session = session

            logger.info("Connected to GitLab MCP server")

        except MCPConnectionError:
            await self.disconnect()
            raise
        except Exception as e:
            await self.disconnect()
            raise MCPConnectionError(f"Failed to connect to GitLab MCP server: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from GitLab MCP server."""
        if self._session is not None:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None

        if self._http_context is not None:
            try:
                await self._http_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._http_context = None

        self._read_stream = None
        self._write_stream = None

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call a GitLab MCP tool."""
        if self._session is None:
            raise MCPConnectionError("Not connected to GitLab MCP server")

        try:
            result = await self._session.call_tool(tool_name, arguments)

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
            raise MCPToolError(f"GitLab MCP tool '{tool_name}' failed: {e}") from e

    async def list_tools(self) -> list[str]:
        """List available GitLab MCP tools."""
        if self._session is None:
            raise MCPConnectionError("Not connected to GitLab MCP server")

        tools = await self._session.list_tools()
        return [tool.name for tool in tools.tools]

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._session is not None

    # High-level convenience methods for career data gathering

    async def search_merge_requests(self, username: str) -> MCPToolResult:
        """Search for user's merge requests.

        Args:
            username: GitLab username

        Returns:
            MCPToolResult with merge request list
        """
        return await self.call_tool(
            "search",
            {
                "search_type": "merge_requests",
                "query": f"author:{username}",
            },
        )

    async def search_issues(self, username: str) -> MCPToolResult:
        """Search for user's issues.

        Args:
            username: GitLab username

        Returns:
            MCPToolResult with issue list
        """
        return await self.call_tool(
            "search",
            {
                "search_type": "issues",
                "query": f"author:{username}",
            },
        )

    async def search_projects(self, query: str) -> MCPToolResult:
        """Search for projects.

        Args:
            query: Search query

        Returns:
            MCPToolResult with project list
        """
        return await self.call_tool(
            "search",
            {
                "search_type": "projects",
                "query": query,
            },
        )

    async def get_merge_request(self, project_id: str, mr_iid: int) -> MCPToolResult:
        """Get details of a specific merge request.

        Args:
            project_id: Project ID or path
            mr_iid: Merge request internal ID

        Returns:
            MCPToolResult with merge request details
        """
        return await self.call_tool(
            "get_merge_request",
            {
                "project_id": project_id,
                "merge_request_iid": mr_iid,
            },
        )

    async def get_issue(self, project_id: str, issue_iid: int) -> MCPToolResult:
        """Get details of a specific issue.

        Args:
            project_id: Project ID or path
            issue_iid: Issue internal ID

        Returns:
            MCPToolResult with issue details
        """
        return await self.call_tool(
            "get_issue",
            {
                "project_id": project_id,
                "issue_iid": issue_iid,
            },
        )
