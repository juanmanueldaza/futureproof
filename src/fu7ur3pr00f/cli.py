"""FutureProof CLI - Career Intelligence System."""

import logging
from typing import Annotated

import typer

from . import __version__
from .config import settings
from .utils.console import console

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="futureproof",
    help="Career Intelligence System - chat with your career agent",
)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold blue]FutureProof[/bold blue] v{__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
    thread: Annotated[
        str,
        typer.Option("--thread", "-t", help="Conversation thread ID"),
    ] = "main",
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Show debug-level logs in terminal"),
    ] = False,
) -> None:
    """FutureProof - Know thyself through your data."""
    settings.ensure_directories()

    # Initialize logging — file handler always active, console only shows warnings
    from .utils.logging import setup_logging

    setup_logging(
        level="DEBUG",
        log_file=settings.data_dir / "fu7ur3pr00f.log",
        console_level="WARNING",
    )

    # If a subcommand was invoked, let it handle things
    if ctx.invoked_subcommand is not None:
        return

    # No subcommand → launch chat
    if debug:
        fp_logger = logging.getLogger("futureproof")
        for handler in fp_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                handler.setLevel(logging.DEBUG)

    from .chat.client import run_chat

    try:
        run_chat(thread_id=thread)
    except KeyboardInterrupt:
        console.print("\n[dim]Chat ended.[/dim]")
    except Exception as e:
        console.print(f"[red]Chat error: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
