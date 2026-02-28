"""MCP connection pool with persistent event loop.

Keeps MCP client connections alive across tool calls, avoiding
the overhead of Docker container spawns (GitHub) and HTTP client
creation (all HTTP-based clients) on every invocation.

Architecture:
- A single background daemon thread runs a persistent asyncio loop
- Connected clients are cached by server type
- Per-server asyncio.Lock serializes concurrent calls (required
  for stdio/session-based protocols like GitHub MCP)
- Automatic reconnection on connection failure
- atexit cleanup disconnects all clients on process exit
"""

import asyncio
import atexit
import logging
import threading
from typing import Any

from .base import MCPClient, MCPClientError, MCPConnectionError, MCPToolResult
from .factory import MCPClientFactory, MCPServerType

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_clients: dict[str, MCPClient] = {}
_client_locks: dict[str, asyncio.Lock] = {}
_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    """Get or create the pool's background event loop."""
    global _loop, _thread
    if _loop is None or not _loop.is_running():
        _loop = asyncio.new_event_loop()
        _thread = threading.Thread(
            target=_loop.run_forever,
            daemon=True,
            name="mcp-pool",
        )
        _thread.start()
    return _loop


async def _get_or_connect(server_type: MCPServerType) -> MCPClient:
    """Get cached client or create and connect a new one."""
    client = _clients.get(server_type)
    if client is not None and client.is_connected():
        return client

    client = MCPClientFactory.create(server_type)
    await client.connect()
    _clients[server_type] = client
    logger.info("Pool: connected %s", server_type)
    return client


async def _call(
    server_type: MCPServerType,
    tool_name: str,
    args: dict[str, Any],
) -> MCPToolResult:
    """Execute tool call with connection reuse and retry."""
    if server_type not in _client_locks:
        _client_locks[server_type] = asyncio.Lock()

    async with _client_locks[server_type]:
        try:
            client = await _get_or_connect(server_type)
            return await client.call_tool(tool_name, args)
        except (MCPConnectionError, MCPClientError):
            # Reconnect once on failure
            old = _clients.pop(server_type, None)
            if old:
                try:
                    await old.disconnect()
                except Exception:
                    pass
            client = await _get_or_connect(server_type)
            return await client.call_tool(tool_name, args)


def call_tool(
    server_type: MCPServerType,
    tool_name: str,
    args: dict[str, Any],
    timeout: float = 60.0,
) -> MCPToolResult:
    """Call an MCP tool using a pooled connection.

    Thread-safe synchronous entry point for use from sync
    tool functions. Keeps connections alive across calls.

    Args:
        server_type: MCP server type (e.g., "github")
        tool_name: Tool to call on the server
        args: Tool arguments
        timeout: Max seconds to wait for result

    Returns:
        MCPToolResult from the tool call

    Raises:
        MCPClientError: On connection or tool failure
    """
    with _lock:
        loop = _get_loop()
    future = asyncio.run_coroutine_threadsafe(
        _call(server_type, tool_name, args), loop,
    )
    return future.result(timeout=timeout)


async def _shutdown_async() -> None:
    """Disconnect all pooled clients."""
    for name, client in list(_clients.items()):
        try:
            await client.disconnect()
            logger.info("Pool: disconnected %s", name)
        except Exception:
            logger.debug(
                "Pool: error disconnecting %s",
                name,
                exc_info=True,
            )
    _clients.clear()
    _client_locks.clear()


def shutdown() -> None:
    """Disconnect all pooled clients. Safe to call at exit."""
    if _loop is not None and _loop.is_running():
        fut = asyncio.run_coroutine_threadsafe(
            _shutdown_async(), _loop,
        )
        try:
            fut.result(timeout=10)
        except Exception:
            logger.debug("Pool shutdown error", exc_info=True)


def reset() -> None:
    """Shutdown and reset pool state. For tests."""
    shutdown()
    global _loop, _thread
    if _loop is not None:
        _loop.call_soon_threadsafe(_loop.stop)
        _loop = None
        _thread = None


atexit.register(shutdown)
