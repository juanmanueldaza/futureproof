"""Base class for market intelligence gatherers.

Provides TTL-based caching to avoid hammering APIs and improve performance.
Also provides helpers to reduce code duplication when gathering from
multiple MCP sources.
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ...config import settings
from ...mcp.factory import MCPClientFactory, MCPServerType

logger = logging.getLogger(__name__)


class MarketGatherer(ABC):
    """Base class for market data gatherers with TTL caching.

    Subclasses should implement:
    - gather(): Collect data from MCP sources
    - _get_cache_key(): Return unique cache key
    - _get_cache_ttl_hours(): Return cache TTL in hours
    """

    def __init__(self) -> None:
        """Initialize gatherer with cache directory."""
        self._cache_dir = settings.market_cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    async def gather(self, **kwargs: Any) -> dict[str, Any]:
        """Gather market data from sources.

        Args:
            **kwargs: Gatherer-specific parameters

        Returns:
            Dictionary with gathered data
        """
        ...

    @abstractmethod
    def _get_cache_key(self, **kwargs: Any) -> str:
        """Generate cache key for the given parameters.

        Args:
            **kwargs: Parameters that affect cache key

        Returns:
            Unique cache key string
        """
        ...

    @abstractmethod
    def _get_cache_ttl_hours(self) -> int:
        """Get cache TTL in hours.

        Returns:
            Number of hours before cache expires
        """
        ...

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get path to cache file for given key.

        Args:
            cache_key: Cache key

        Returns:
            Path to cache file
        """
        # Hash the key to avoid filesystem issues with special characters
        key_hash = hashlib.md5(cache_key.encode()).hexdigest()[:16]
        return self._cache_dir / f"{self.__class__.__name__}_{key_hash}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is not expired.

        Args:
            cache_path: Path to cache file

        Returns:
            True if cache is valid and can be used
        """
        if not cache_path.exists():
            return False

        try:
            with open(cache_path) as f:
                cache_data = json.load(f)

            cached_at = datetime.fromisoformat(cache_data.get("cached_at", ""))
            ttl_hours = self._get_cache_ttl_hours()
            expires_at = cached_at + timedelta(hours=ttl_hours)

            return datetime.now() < expires_at

        except (json.JSONDecodeError, ValueError, KeyError):
            return False

    def _read_cache(self, cache_path: Path) -> dict[str, Any] | None:
        """Read data from cache file.

        Args:
            cache_path: Path to cache file

        Returns:
            Cached data or None if invalid
        """
        try:
            with open(cache_path) as f:
                cache_data = json.load(f)
            return cache_data.get("data")
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cache(self, cache_path: Path, data: dict[str, Any]) -> None:
        """Write data to cache file.

        Args:
            cache_path: Path to cache file
            data: Data to cache
        """
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "ttl_hours": self._get_cache_ttl_hours(),
            "data": data,
        }
        try:
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2, default=str)
        except OSError as e:
            logger.warning(f"Failed to write cache: {e}")

    async def gather_with_cache(
        self,
        refresh: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Gather data with caching support.

        Args:
            refresh: If True, bypass cache and fetch fresh data
            **kwargs: Gatherer-specific parameters

        Returns:
            Dictionary with gathered data (from cache or fresh)
        """
        cache_key = self._get_cache_key(**kwargs)
        cache_path = self._get_cache_path(cache_key)

        # Check cache unless refresh requested
        if not refresh and self._is_cache_valid(cache_path):
            cached_data = self._read_cache(cache_path)
            if cached_data is not None:
                logger.info(f"Using cached data for {self.__class__.__name__}")
                return cached_data

        # Gather fresh data
        logger.info(f"Gathering fresh data for {self.__class__.__name__}")
        data = await self.gather(**kwargs)

        # Cache the results
        self._write_cache(cache_path, data)

        return data

    def clear_cache(self) -> int:
        """Clear all cache files for this gatherer.

        Returns:
            Number of cache files deleted
        """
        pattern = f"{self.__class__.__name__}_*.json"
        deleted = 0
        for cache_file in self._cache_dir.glob(pattern):
            try:
                cache_file.unlink()
                deleted += 1
            except OSError:
                pass
        return deleted

    async def _gather_from_source(
        self,
        source_name: MCPServerType,
        tool_name: str,
        tool_args: dict[str, Any],
        results: dict[str, Any],
        extractor: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
        result_key: str = "job_listings",
        source_label: str | None = None,
    ) -> list[dict[str, Any]]:
        """Generic method to gather from any MCP source.

        This helper eliminates the repeated try/except pattern across
        multiple source gathering blocks. (DRY fix)

        Args:
            source_name: MCP source name (e.g., "jobspy", "remoteok")
            tool_name: Tool to call on the MCP client
            tool_args: Arguments to pass to the tool
            results: Results dict to update with errors
            extractor: Optional function to extract items from response.
                       Default extracts response.get("jobs", [])
            result_key: Key in results to extend with extracted items
            source_label: Optional human-readable label for logging

        Returns:
            List of extracted items (empty if source unavailable or errored)
        """
        label = source_label or source_name.capitalize()

        if not MCPClientFactory.is_available(source_name):
            logger.debug(f"{label} MCP not available, skipping")
            return []

        try:
            logger.info(f"{label}: Gathering data...")
            client = MCPClientFactory.create(source_name)
            async with client:
                result = await client.call_tool(tool_name, tool_args)

                if not result.is_error:
                    content = result.content or "{}"
                    parsed = json.loads(content) if isinstance(content, str) else content

                    # Extract items using provided extractor or default
                    if extractor is not None:
                        items = extractor(parsed)
                    elif isinstance(parsed, dict):
                        items = parsed.get("jobs", [])
                    else:
                        items = parsed if isinstance(parsed, list) else []

                    logger.info(f"{label}: Found {len(items)} items")
                    return items
                else:
                    logger.warning(f"{label}: {result.error_message}")
                    results["errors"].append(f"{label}: {result.error_message}")
                    return []

        except Exception as e:
            logger.exception(f"Error gathering from {label}")
            results["errors"].append(f"{label} error: {e}")
            return []
