"""Base MCP client interface.

Defines the abstract interface that all MCP clients must implement,
enabling swappable backends through Dependency Inversion.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from mcp import types
from mcp.client.session import ClientSession


@dataclass
class MCPToolResult:
    """Standardized MCP tool call result.

    Provides a consistent interface regardless of the underlying MCP server.
    """

    content: Any
    raw_response: Any = None
    tool_name: str = ""
    is_error: bool = False
    error_message: str = ""


class MCPClientError(Exception):
    """Base exception for MCP client errors."""

    pass


class MCPConnectionError(MCPClientError):
    """Raised when connection to MCP server fails."""

    pass


class MCPToolError(MCPClientError):
    """Raised when MCP tool call fails."""

    pass


class MCPClient(ABC):
    """Abstract base class for MCP clients.

    Implements the Dependency Inversion Principle - high-level modules
    depend on this abstraction, not concrete implementations.

    To add a new MCP server:
    1. Create a new class that extends MCPClient
    2. Implement connect(), disconnect(), call_tool(), list_tools()
    3. Register in MCPClientFactory.CLIENTS
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to MCP server.

        Raises:
            MCPConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as dict

        Returns:
            MCPToolResult with response content

        Raises:
            MCPToolError: If tool call fails
        """
        pass

    @abstractmethod
    async def list_tools(self) -> list[str]:
        """List available tools on the MCP server.

        Returns:
            List of tool names
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if client is connected."""
        pass

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()


class SessionMCPClient(MCPClient):
    """Base for MCP clients that use ClientSession (stdio or HTTP transport).

    Provides shared call_tool/list_tools/is_connected implementations
    used by the GitHub MCP client. Subclasses only need to
    implement connect() and disconnect() for their specific transport.
    """

    SERVER_NAME: str = "MCP"  # Override in subclasses for error messages

    def __init__(self) -> None:
        self._session: ClientSession | None = None

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call an MCP tool via the session."""
        if self._session is None:
            raise MCPConnectionError(f"Not connected to {self.SERVER_NAME} server")

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
            raise MCPToolError(f"{self.SERVER_NAME} tool '{tool_name}' failed: {e}") from e

    async def list_tools(self) -> list[str]:
        """List available MCP tools."""
        if self._session is None:
            raise MCPConnectionError(f"Not connected to {self.SERVER_NAME} server")

        tools = await self._session.list_tools()
        return [tool.name for tool in tools.tools]

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._session is not None
