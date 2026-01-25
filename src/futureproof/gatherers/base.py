"""Base class for data gatherers."""

import asyncio
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import nest_asyncio

from ..utils.console import console

logger = logging.getLogger(__name__)

# Apply nest_asyncio to allow nested event loops (needed for sync-to-async bridge in CLI)
nest_asyncio.apply()

# Subprocess timeout in seconds (5 minutes)
SUBPROCESS_TIMEOUT = 300


class BaseGatherer(ABC):
    """Base class for all data gatherers."""

    output_dir: Path

    def gather(self, *args: Any, **kwargs: Any) -> Path:
        """Gather data and return path to output file.

        Returns:
            Path to the generated output file
        """
        raise NotImplementedError


class CLIGatherer(BaseGatherer):
    """Base class for gatherers that use external CLI tools."""

    cli_command: str
    cli_install_hint: str

    def _run_cli(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Run CLI command with error handling.

        Args:
            args: Command arguments (without the CLI command itself)

        Returns:
            CompletedProcess result

        Raises:
            subprocess.CalledProcessError: If command fails
            FileNotFoundError: If CLI tool not found
            subprocess.TimeoutExpired: If command times out
        """
        cmd = [self.cli_command] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=SUBPROCESS_TIMEOUT,
            )
            console.print(f"  [dim]{self.cli_command} completed successfully[/dim]")
            return result
        except subprocess.CalledProcessError as e:
            # Log full error for debugging, show sanitized message to user
            logger.error("%s failed: %s", self.cli_command, e.stderr)
            console.print(f"  [red]{self.cli_command} failed. Check logs for details.[/red]")
            raise
        except subprocess.TimeoutExpired:
            logger.error("%s timed out after %d seconds", self.cli_command, SUBPROCESS_TIMEOUT)
            console.print(f"  [red]{self.cli_command} timed out.[/red]")
            raise
        except FileNotFoundError:
            console.print(f"  [red]{self.cli_command} not found. {self.cli_install_hint}[/red]")
            raise

    def _combine_files(self, filenames: list[str], output_file: Path) -> Path:
        """Combine multiple markdown files into one.

        Args:
            filenames: List of filenames to combine
            output_file: Path to write combined output

        Returns:
            Path to the output file
        """
        parts = []
        for filename in filenames:
            filepath = self.output_dir / filename
            if filepath.exists():
                parts.append(filepath.read_text())

        if parts:
            output_file.write_text("\n\n".join(parts))
            console.print(f"  Saved to: {output_file}")
        else:
            console.print("  [yellow]No output files generated[/yellow]")

        return output_file


class MCPGatherer(BaseGatherer):
    """Base class for gatherers that use MCP servers with CLI fallback.

    Provides async-to-sync bridge and automatic fallback to CLI gatherers
    when MCP is unavailable or fails.
    """

    fallback_gatherer: CLIGatherer | None = None

    def _run_async(self, coro: Any) -> Any:
        """Run async coroutine in sync context.

        Uses nest_asyncio to handle nested event loops safely.

        Args:
            coro: Async coroutine to run

        Returns:
            Result of the coroutine
        """
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, run in the existing loop
            return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop running - create one
            return asyncio.run(coro)

    @abstractmethod
    async def gather_async(self, *args: Any, **kwargs: Any) -> Path:
        """Async gather implementation.

        Subclasses implement this for MCP-based gathering.

        Returns:
            Path to the generated output file
        """
        pass

    @abstractmethod
    def _can_use_mcp(self) -> bool:
        """Check if MCP is available and configured.

        Returns:
            True if MCP can be used
        """
        pass

    def gather(self, *args: Any, **kwargs: Any) -> Path:
        """Sync gather with MCP and fallback support.

        Priority:
        1. Try MCP gathering if configured
        2. Fall back to CLI gatherer if MCP fails or unavailable

        Returns:
            Path to the generated output file
        """
        from ..mcp import MCPClientError

        # Check if MCP is available
        if self._can_use_mcp():
            try:
                console.print("  [dim]Using MCP server...[/dim]")
                return self._run_async(self.gather_async(*args, **kwargs))
            except MCPClientError as e:
                logger.warning("MCP gathering failed, falling back to CLI: %s", e)
                console.print("  [yellow]MCP unavailable, using CLI fallback[/yellow]")

        # Fallback to CLI
        if self.fallback_gatherer:
            return self.fallback_gatherer.gather(*args, **kwargs)

        raise RuntimeError("No gathering method available (MCP not configured, no CLI fallback)")
