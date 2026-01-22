"""Centralized logging configuration for FutureProof."""

import logging
import sys
from pathlib import Path
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Module-level logger cache
_loggers: dict[str, logging.Logger] = {}
_initialized: bool = False


def setup_logging(
    level: LogLevel = "INFO",
    log_file: Path | None = None,
    console_level: LogLevel = "WARNING",
) -> logging.Logger:
    """Configure application logging.

    Args:
        level: Root logging level
        log_file: Optional file path for logging
        console_level: Level for console output (default WARNING to keep CLI clean)

    Returns:
        Configured root logger instance
    """
    global _initialized

    logger = logging.getLogger("futureproof")
    logger.setLevel(getattr(logging, level))

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler - only warnings and above to keep CLI output clean
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, console_level))
    console_format = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    _initialized = True
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a named logger under the futureproof namespace.

    Args:
        name: Logger name (will be prefixed with 'futureproof.')

    Returns:
        Logger instance
    """
    full_name = f"futureproof.{name}" if not name.startswith("futureproof.") else name

    if full_name not in _loggers:
        _loggers[full_name] = logging.getLogger(full_name)

    return _loggers[full_name]


def set_log_level(level: LogLevel) -> None:
    """Set the logging level for all futureproof loggers.

    Args:
        level: New logging level
    """
    root_logger = logging.getLogger("futureproof")
    root_logger.setLevel(getattr(logging, level))
