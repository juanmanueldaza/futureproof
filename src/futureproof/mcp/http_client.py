"""HTTP-based MCP client base class.

Provides a reusable base class for MCP clients that communicate
with HTTP APIs. Eliminates code duplication across 8+ client
implementations by consolidating:
- Connection lifecycle (connect, disconnect, is_connected)
- HTTP client initialization with configurable headers/timeout
- Tool call error handling wrapper
- Common patterns for JSON response formatting

Usage:
    class MyAPIClient(HTTPMCPClient):
        BASE_URL = "https://api.example.com"
        DEFAULT_HEADERS = {"Accept": "application/json"}

        async def list_tools(self) -> list[str]:
            return ["my_tool"]

        async def _tool_my_tool(self, args: dict[str, Any]) -> MCPToolResult:
            # Implementation
            ...
"""

import json
from abc import abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from .base import MCPClient, MCPConnectionError, MCPToolError, MCPToolResult


class HTTPMCPClient(MCPClient):
    """Base class for HTTP API-based MCP clients.

    Subclasses must:
    1. Set BASE_URL class attribute (optional, for documentation)
    2. Override list_tools() to return available tool names
    3. Implement tool methods named _tool_{tool_name}(args) -> MCPToolResult

    Optional overrides:
    - DEFAULT_TIMEOUT: Request timeout in seconds (default: 30.0)
    - DEFAULT_HEADERS: Headers to include in all requests
    - _get_headers(): For dynamic header generation
    - _validate_connection(): For API key or other pre-connection checks
    """

    BASE_URL: str = ""
    DEFAULT_TIMEOUT: float = 30.0
    DEFAULT_HEADERS: dict[str, str] = {}

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the HTTP MCP client.

        Args:
            api_key: Optional API key for authenticated APIs
        """
        self._api_key = api_key
        self._connected = False
        self._client: httpx.AsyncClient | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get headers for HTTP requests.

        Override in subclasses for custom headers.
        Default implementation returns DEFAULT_HEADERS.

        Returns:
            Headers dict to use for requests
        """
        return self.DEFAULT_HEADERS.copy()

    def _validate_connection(self) -> None:
        """Validate that connection can be established.

        Override in subclasses to check API keys, etc.
        Raise MCPConnectionError if validation fails.
        """
        pass

    async def connect(self) -> None:
        """Initialize HTTP client.

        Raises:
            MCPConnectionError: If initialization fails
        """
        self._validate_connection()

        try:
            self._client = httpx.AsyncClient(
                timeout=self.DEFAULT_TIMEOUT,
                headers=self._get_headers(),
            )
            self._connected = True
        except Exception as e:
            raise MCPConnectionError(f"Failed to initialize HTTP client: {e}") from e

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
        self._connected = False

    def is_connected(self) -> bool:
        """Check if client is connected and ready."""
        return self._connected and self._client is not None

    @abstractmethod
    async def list_tools(self) -> list[str]:
        """List available tools.

        Subclasses must implement this to return their tool names.

        Returns:
            List of tool names
        """
        pass

    def _get_tool_handler(
        self, tool_name: str
    ) -> Callable[[dict[str, Any]], Awaitable[MCPToolResult]] | None:
        """Get the handler method for a tool.

        Looks for a method named _tool_{tool_name} on the class.

        Args:
            tool_name: Name of the tool

        Returns:
            Handler method or None if not found
        """
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is not None and callable(handler):
            # Type assertion: we know _tool_* methods return Awaitable[MCPToolResult]
            return handler  # type: ignore[return-value]
        return None

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call a tool with the given arguments.

        Handles common error patterns and delegates to _tool_{tool_name} methods.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            MCPToolResult with tool output

        Raises:
            MCPToolError: If tool call fails
        """
        if not self.is_connected():
            raise MCPToolError("Client not connected")

        try:
            handler = self._get_tool_handler(tool_name)
            if handler is None:
                raise MCPToolError(f"Unknown tool: {tool_name}")
            return await handler(arguments)
        except MCPToolError:
            raise
        except Exception as e:
            raise MCPToolError(f"Tool call failed: {e}") from e

    def _ensure_client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raising if not initialized.

        Returns:
            The httpx AsyncClient

        Raises:
            MCPToolError: If client is not initialized
        """
        if not self._client:
            raise MCPToolError("Client not initialized")
        return self._client

    def _format_response(
        self,
        output: dict[str, Any],
        raw_response: Any,
        tool_name: str,
    ) -> MCPToolResult:
        """Format response with consistent JSON indentation.

        DRY helper to eliminate repeated json.dumps(indent=2) calls
        across all HTTP MCP clients.

        Args:
            output: Processed output dict to serialize
            raw_response: Original API response for debugging
            tool_name: Name of the tool that was called

        Returns:
            MCPToolResult with formatted JSON content
        """
        return MCPToolResult(
            content=json.dumps(output, indent=2),
            raw_response=raw_response,
            tool_name=tool_name,
        )
