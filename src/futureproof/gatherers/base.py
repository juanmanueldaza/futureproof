"""Base class for data gatherers."""

import asyncio
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..utils.async_bridge import run_async_in_sync
from ..utils.console import console

logger = logging.getLogger(__name__)

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

        Uses the centralized async bridge utility for consistent behavior.

        Args:
            coro: Async coroutine to run

        Returns:
            Result of the coroutine
        """
        return run_async_in_sync(coro)

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
                return self._run_async(self.gather_async(*args, **kwargs))
            except MCPClientError as e:
                console.print(f"  [yellow]⚠ MCP error: {e}[/yellow]")
                console.print("  [dim]Using CLI fallback...[/dim]")
            except (asyncio.CancelledError, ConnectionError, TimeoutError, OSError):
                # Server-side issues (connection reset, timeout, cancelled)
                console.print("  [yellow]⚠ MCP server unavailable[/yellow]")
                console.print("  [dim]Using CLI fallback...[/dim]")
            except Exception as e:
                console.print(f"  [yellow]⚠ MCP error: {type(e).__name__}: {e}[/yellow]")
                console.print("  [dim]Using CLI fallback...[/dim]")

        # Fallback to CLI
        if self.fallback_gatherer:
            return self.fallback_gatherer.gather(*args, **kwargs)

        raise RuntimeError("No gathering method available (MCP not configured, no CLI fallback)")
