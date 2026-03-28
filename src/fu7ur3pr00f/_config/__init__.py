"""Configuration loader for JSON config files.

Provides cached loading of JSON configuration files with fallback
to default values if files are missing or malformed.

Usage:
    from fu7ur3pr00f._config import load_config
    aliases = load_config("location_aliases")
    keywords = load_config("routing_keywords")
"""

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

# Cache for loaded configs
_config_cache: dict[str, Any] = {}
_config_lock = Lock()

# Default configurations (used if files are missing/malformed)
_DEFAULTS: dict[str, Any] = {}


def _get_config_path(name: str) -> Path:
    """Get the path to a config file by name."""
    return Path(__file__).parent / f"{name}.json"


def load_config(name: str, use_cache: bool = True) -> Any:
    """Load a configuration file by name.

    Args:
        name: Config file name (without .json extension)
        use_cache: Whether to use cached result (default True)

    Returns:
        Parsed config dict or list

    Raises:
        FileNotFoundError: If config file doesn't exist and no default
        json.JSONDecodeError: If config file is malformed and no default
    """
    if use_cache:
        with _config_lock:
            if name in _config_cache:
                return _config_cache[name]

    config_path = _get_config_path(name)

    try:
        content = config_path.read_text(encoding="utf-8")
        data = json.loads(content)

        # Extract the actual data (files have "description" + data key)
        if isinstance(data, dict):
            # Try common data keys
            for key in ("aliases", "keywords", "data", "config"):
                if key in data:
                    result = data[key]
                    break
            else:
                # No known key, return the whole dict minus metadata
                result = {
                    k: v
                    for k, v in data.items()
                    if k not in ("description", "version", "author")
                }
        else:
            result = data

        if use_cache:
            with _config_lock:
                _config_cache[name] = result

        return result

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(
            "Config %s not found or malformed, using defaults: %s",
            name,
            e,
        )
        if name in _DEFAULTS:
            return _DEFAULTS[name]
        raise


def clear_config_cache() -> None:
    """Clear the configuration cache. Useful for testing."""
    with _config_lock:
        _config_cache.clear()


__all__ = [
    "load_config",
    "clear_config_cache",
]
