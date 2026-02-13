"""Shared async helper for running coroutines from sync tool contexts."""

import asyncio
import concurrent.futures


def run_async(coro):
    """Run an async coroutine from a sync context (ToolNode thread pool).

    Handles the case where an event loop is already running by spawning
    a new thread with its own loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)
