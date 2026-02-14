"""GitLab MCP client implementation.

Uses streamable HTTP transport to communicate with the GitLab MCP server.
"""

import asyncio
import logging
import warnings
from typing import Any

from mcp import types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from ..config import settings
from .base import MCPClient, MCPConnectionError, MCPToolError, MCPToolResult

logger = logging.getLogger(__name__)

# Connection timeout for GitLab MCP (seconds)
GITLAB_MCP_TIMEOUT = 30


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

    async def _cleanup_http_context(self, http_context: Any, entered: bool = True) -> None:
        """Safely cleanup HTTP context, suppressing sniffio errors.

        The streamablehttp_client async generator can fail during cleanup
        when running in a sync-to-async bridged context because sniffio
        can't detect the async library during garbage collection.

        Args:
            http_context: The async context manager to clean up
            entered: True if __aenter__ completed, False if it was interrupted
        """
        if http_context is None:
            return

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ResourceWarning)
            try:
                if entered:
                    await http_context.__aexit__(None, None, None)
                else:
                    # If __aenter__ was interrupted, close the generator directly
                    await http_context.aclose()
            except Exception:
                # Cleanup errors are expected in edge cases - ignore silently
                pass

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

        http_context_entered = False
        session_entered = False
        http_context = None
        session = None
        try:
            # Use streamable HTTP transport for GitLab with timeout
            http_context = streamablehttp_client(
                settings.gitlab_mcp_url,
                headers={"Authorization": f"Bearer {settings.gitlab_mcp_token}"},
            )

            # Apply timeout to connection
            try:
                read_stream, write_stream, _ = await asyncio.wait_for(
                    http_context.__aenter__(),
                    timeout=GITLAB_MCP_TIMEOUT,
                )
            except (TimeoutError, asyncio.CancelledError) as e:
                # Connection was interrupted - close generator before it gets GC'd
                await self._cleanup_http_context(http_context, entered=False)
                if isinstance(e, TimeoutError):
                    raise MCPConnectionError(
                        f"GitLab MCP connection timed out after {GITLAB_MCP_TIMEOUT}s"
                    )
                raise  # Re-raise CancelledError
            http_context_entered = True

            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            session_entered = True
            await session.initialize()

            # Only assign to instance after successful initialization
            self._http_context = http_context
            self._read_stream = read_stream
            self._write_stream = write_stream
            self._session = session

            logger.info("Connected to GitLab MCP server")

        except MCPConnectionError:
            # Clean up local references before re-raising
            if session_entered and session is not None:
                try:
                    await session.__aexit__(None, None, None)
                except Exception:
                    pass
            if http_context is not None:
                await self._cleanup_http_context(http_context, entered=http_context_entered)
            raise
        except Exception as e:
            # Clean up local references before re-raising
            if session_entered and session is not None:
                try:
                    await session.__aexit__(None, None, None)
                except Exception:
                    pass
            if http_context is not None:
                await self._cleanup_http_context(http_context, entered=http_context_entered)
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
            await self._cleanup_http_context(self._http_context)
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
