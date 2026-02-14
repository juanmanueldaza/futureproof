"""Base class for data gatherers."""

import logging
import subprocess
from abc import ABC
from pathlib import Path
from typing import Any

from ..utils.console import console

logger = logging.getLogger(__name__)

# Subprocess timeout in seconds (5 minutes)
SUBPROCESS_TIMEOUT = 300


class BaseGatherer(ABC):
    """Base class for all data gatherers."""

    output_dir: Path

    def gather(self, *args: Any, **kwargs: Any) -> str | Path:
        """Gather data and return content or path to output file.

        Returns:
            Content string (portfolio, assessment) or Path (LinkedIn CLI)
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
