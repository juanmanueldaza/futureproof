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
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold blue]FutureProof[/bold blue] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """FutureProof - Know thyself through your data."""
    settings.ensure_directories()


# ============================================================================
# CHAT COMMANDS - Conversational interface
# ============================================================================


@app.command("chat")
def chat_command(
    thread: Annotated[
        str,
        typer.Option("--thread", "-t", help="Conversation thread ID for persistence"),
    ] = "main",
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show tool usage and agent reasoning"),
    ] = False,
) -> None:
    """Start an interactive chat session with the career intelligence agent.

    This is the primary way to interact with FutureProof. The agent can:
    - Gather data from GitHub, GitLab, LinkedIn, portfolio, and CliftonStrengths
    - Analyze your skills, identify gaps, and assess market fit
    - Search for job opportunities and salary data
    - Generate tailored CVs and cover letters
    - Index and search your career knowledge base
    - Provide strategic career advice
    - Check background daemon status and insights
    - Remember your goals and preferences

    Your conversation is automatically saved and persists across sessions.

    Use --verbose to see which tools the agent is using.
    """
    from .chat.client import run_chat

    try:
        run_chat(thread_id=thread, verbose=verbose)
    except KeyboardInterrupt:
        console.print("\n[dim]Chat ended.[/dim]")
    except Exception as e:
        console.print(f"[red]Chat error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("ask")
def ask_command(
    question: Annotated[
        str,
        typer.Argument(help="Question to ask the career agent"),
    ],
    thread: Annotated[
        str,
        typer.Option("--thread", "-t", help="Conversation thread ID"),
    ] = "main",
) -> None:
    """Ask a single question to the career agent.

    This is for quick one-off queries without entering the full chat interface.
    The response still maintains context from previous conversations in the thread.

    Examples:
        futureproof ask "What are my top skills?"
        futureproof ask "Analyze my gaps for ML Engineer role"
    """
    from .chat.client import ask

    try:
        ask(question, thread_id=thread)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("memory")
def memory_command(
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Clear all conversation history"),
    ] = False,
    threads: Annotated[
        bool,
        typer.Option("--threads", help="List all conversation threads"),
    ] = False,
) -> None:
    """Manage conversation memory and history.

    View memory stats, list conversation threads, or clear history.
    """
    from .memory.checkpointer import clear_thread_history, get_data_dir, list_threads
    from .memory.profile import load_profile

    if clear:
        for thread_id in list_threads():
            clear_thread_history(thread_id)
        console.print("[green]All conversation history cleared.[/green]")
        return

    if threads:
        thread_list = list_threads()
        if thread_list:
            console.print("[bold]Conversation threads:[/bold]")
            for t in thread_list:
                console.print(f"  - {t}")
        else:
            console.print("[dim]No conversation threads found.[/dim]")
        return

    # Show memory stats
    data_dir = get_data_dir()
    profile = load_profile()
    thread_list = list_threads()

    console.print("[bold cyan]Memory Status[/bold cyan]\n")
    console.print(f"Data directory: {data_dir}")
    console.print(f"Conversation threads: {len(thread_list)}")
    console.print(f"Profile configured: {'Yes' if profile.name else 'No'}")
    if profile.goals:
        console.print(f"Career goals: {len(profile.goals)}")


if __name__ == "__main__":
    app()
