"""Base MCP client interface.

Defines the abstract interface that all MCP clients must implement,
enabling swappable backends through Dependency Inversion.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class MCPToolResult:
    """Standardized MCP tool call result.

    Provides a consistent interface regardless of the underlying MCP server.
    """

    content: str
    raw_response: Any = None
    tool_name: str = ""
    is_error: bool = False


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
