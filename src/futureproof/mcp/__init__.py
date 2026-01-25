"""MCP (Model Context Protocol) client implementations.

Provides clients for connecting to MCP servers like GitHub and GitLab
for real-time data access instead of CLI-based gathering.
"""

from .base import MCPClient, MCPClientError, MCPConnectionError, MCPToolError, MCPToolResult
from .factory import MCPClientFactory

__all__ = [
    "MCPClient",
    "MCPClientError",
    "MCPClientFactory",
    "MCPConnectionError",
    "MCPToolError",
    "MCPToolResult",
]
