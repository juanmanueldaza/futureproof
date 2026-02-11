"""Async-to-sync bridge utilities.

Provides a unified way to run async coroutines in sync contexts,
consolidating the previously duplicated implementations from
gatherers/base.py and tools/market.py.
"""

import asyncio
import sys
from collections.abc import Coroutine
from typing import Any

import nest_asyncio

# Apply nest_asyncio to allow nested event loops (needed for sync-to-async bridge in CLI)
nest_asyncio.apply()


# Suppress async generator cleanup errors (sniffio AsyncLibraryNotFoundError).
# These occur when MCP's streamablehttp_client is garbage collected outside async context.
_original_unraisablehook = sys.unraisablehook


def _quiet_unraisablehook(unraisable: Any) -> None:
    """Suppress sniffio errors during async generator GC."""
    exc = getattr(unraisable, "exc_value", None)
    if exc and "AsyncLibraryNotFoundError" in type(exc).__name__:
        return
    _original_unraisablehook(unraisable)


sys.unraisablehook = _quiet_unraisablehook


def run_async_in_sync[T](coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine in a sync context safely."""
    try:
        loop = asyncio.get_running_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
