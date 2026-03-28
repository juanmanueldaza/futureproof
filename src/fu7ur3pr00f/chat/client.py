"""Chat client for FutureProof conversational interface.

Combines prompt-toolkit for input handling with Rich for output display.
Provides both sync and async chat loops for different use cases.
"""

import warnings

# Suppress noisy Pydantic serialization warnings from structured output
# Must be set before third-party imports that trigger model validation.
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import logging  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

from prompt_toolkit import PromptSession  # noqa: E402
from prompt_toolkit.formatted_text import HTML  # noqa: E402
from prompt_toolkit.history import FileHistory  # noqa: E402
from prompt_toolkit.styles import Style as PTStyle  # noqa: E402
from rich.markdown import Markdown  # noqa: E402

from fu7ur3pr00f.agents.blackboard import get_conversation_engine  # noqa: E402
from fu7ur3pr00f.agents.specialists.blackboard_factory import (  # noqa: E402
    get_agent_config,
)
from fu7ur3pr00f.agents.specialists.orchestrator import (  # noqa: E402
    get_orchestrator,
    reset_orchestrator,
)
from fu7ur3pr00f.chat.ui import (  # noqa: E402
    console,
    display_blackboard_result,
    display_error,
    display_goals,
    display_help,
    display_interrupt_confirmation,
    display_model_info,
    display_profile_summary,
    display_specialist_progress,
    display_tool_result,
    display_tool_start,
    display_welcome,
)
from fu7ur3pr00f.config import settings  # noqa: E402
from fu7ur3pr00f.constants import (  # noqa: E402
    COLOR_ACCENT,
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_SUCCESS,
    COLOR_WARNING,
)
from fu7ur3pr00f.memory.checkpointer import get_data_dir  # noqa: E402

logger = logging.getLogger(__name__)

# ── Prompt styling ────────────────────────────────────────────────────────

_PROMPT_STYLE = PTStyle.from_dict({"prompt": f"{COLOR_WARNING} bold"})
_PROMPT_MSG = HTML("<prompt>\u25b6 </prompt>")

# Patterns that might leak API keys or tokens in error messages
# Extended to cover OpenAI, Anthropic, Google, and bearer tokens
_SECRET_RE = re.compile(
    r"(sk-(?:ant-)?[A-Za-z0-9]{8})[A-Za-z0-9-]+|" r"(AIza[A-Za-z0-9]{8})[A-Za-z0-9_-]+"
)
_BEARER_RE = re.compile(r"(Bearer\s+)[^\s\"']+", re.IGNORECASE)

# Thread ID validation (alphanumeric, dash, underscore only, max 64 chars)
_VALID_THREAD_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _sanitize_error(msg: str) -> str:
    """Redact API keys and bearer tokens from error messages."""
    msg = _SECRET_RE.sub(r"\1\2...", msg)
    msg = _BEARER_RE.sub(r"\1[REDACTED]", msg)
    return msg


def get_history_path() -> Path:
    """Get the path for command history file."""
    return get_data_dir() / "chat_history"


def handle_command(  # noqa: C901 - Command dispatcher with 15+ slash commands
    command: str, *, chat_state: dict
) -> bool:
    """Handle slash commands.

    Args:
        command: The command string (including leading /)
        chat_state: Mutable dict with ``thread_id`` (updated by /thread)

    Returns:
        True if the chat should exit, False otherwise
    """
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/quit", "/q", "/exit"):
        console.print(
            f"[{COLOR_INFO}]Goodbye! Your conversation is saved.[/{COLOR_INFO}]"
        )
        return True

    if cmd in ("/help", "/h"):
        display_help()
        return False

    if cmd == "/profile":
        display_profile_summary()
        return False

    if cmd == "/goals":
        display_goals()
        return False

    if cmd == "/clear":
        from fu7ur3pr00f.memory.checkpointer import clear_thread_history

        clear_thread_history(chat_state["thread_id"])
        console.print(f"[{COLOR_INFO}]Conversation history cleared.[/{COLOR_INFO}]")
        return False

    if cmd == "/thread":
        if not arg:
            console.print(
                f"[{COLOR_INFO}]Current thread: [bold]{chat_state['thread_id']}[/bold][/{COLOR_INFO}]"  # noqa: E501
            )
        else:
            # Validate thread ID to prevent injection attacks
            if not _VALID_THREAD_ID_RE.match(arg):
                console.print(
                    f"[{COLOR_ERROR}]Invalid thread ID: use alphanumeric characters, "
                    f"dashes, and underscores only (max 64 chars).[/{COLOR_ERROR}]"
                )
                return False
            chat_state["thread_id"] = arg
            chat_state["config"] = get_agent_config(thread_id=arg)
            console.print(
                f"[{COLOR_SUCCESS}]Switched to thread: [bold]{arg}[/bold][/{COLOR_SUCCESS}]"
            )
        return False

    if cmd == "/threads":
        from fu7ur3pr00f.memory.checkpointer import list_threads

        thread_list = list_threads()
        if thread_list:
            console.print(
                f"[bold {COLOR_ACCENT}]Conversation threads:[/bold {COLOR_ACCENT}]"
            )
            for t in thread_list:
                marker = " (active)" if t == chat_state["thread_id"] else ""
                console.print(
                    f"  - {t}[bold {COLOR_WARNING}]{marker}[/bold {COLOR_WARNING}]"
                )
        else:
            console.print(
                f"[{COLOR_INFO}]No conversation threads found.[/{COLOR_INFO}]"
            )
        return False

    if cmd == "/memory":
        from fu7ur3pr00f.memory.checkpointer import get_data_dir, list_threads
        from fu7ur3pr00f.memory.profile import load_profile

        data_dir = get_data_dir()
        profile = load_profile()
        thread_list = list_threads()

        console.print("[bold #5bc0be]Memory Status[/bold #5bc0be]\n")
        console.print(f"  Data directory: {data_dir}")
        console.print(f"  Conversation threads: {len(thread_list)}")
        console.print(f"  Profile configured: {'Yes' if profile.name else 'No'}")
        if profile.goals:
            console.print(f"  Career goals: {len(profile.goals)}")
        console.print()
        return False

    if cmd == "/gather":
        # Gather career data from all sources
        console.print("[bold #5bc0be]Gathering career data...[/bold #5bc0be]\n")

        # Enable verbose logging during gather
        logging.getLogger("fu7ur3pr00f.gatherers").setLevel(logging.INFO)

        try:
            from fu7ur3pr00f.services.gatherer_service import GathererService

            console.print("[dim]Using GathererService...[/dim]\n")
            service = GathererService()
            sections = service.gather_all()

            console.print(
                f"\n[{COLOR_SUCCESS}]✓ Gathered {len(sections)} sections[/{COLOR_SUCCESS}]"
            )
            console.print(
                f"[{COLOR_SUCCESS}]✓ Data indexed to knowledge base[/{COLOR_SUCCESS}]\n"
            )
        except ImportError as e:
            # Fallback: run gatherers directly
            console.print(f"[dim]Fallback mode (ImportError: {e})[/dim]\n")

            from fu7ur3pr00f.gatherers.cliftonstrengths import CliftonStrengthsGatherer
            from fu7ur3pr00f.gatherers.cv import CVGatherer
            from fu7ur3pr00f.gatherers.linkedin import LinkedInGatherer
            from fu7ur3pr00f.gatherers.portfolio import PortfolioGatherer

            data_dir = settings.data_dir / "raw"
            total = 0

            console.print(f"[dim]Scanning {data_dir} for data files...[/dim]\n")

            # LinkedIn
            zip_files = list(data_dir.glob("*.zip"))
            if zip_files:
                console.print("[bold]LinkedIn:[/bold]")
                gatherer = LinkedInGatherer()
                for zip_file in zip_files:
                    console.print(f"  [dim]Processing {zip_file.name}...[/dim]")
                    start = time.time()
                    sections = gatherer.gather(zip_file)
                    elapsed = time.time() - start
                    total += len(sections)
                    console.print(
                        f"  [{COLOR_SUCCESS}]✓ {len(sections)} sections[/{COLOR_SUCCESS}]"
                    )
            else:
                console.print(f"  [{COLOR_ERROR}]No LinkedIn ZIP found[/{COLOR_ERROR}]")
            console.print()

            # CliftonStrengths
            pdf_files = [
                f for f in data_dir.glob("*.pdf") if "strength" in f.name.lower()
            ]
            if pdf_files:
                console.print("[bold]CliftonStrengths:[/bold]")
                gatherer = CliftonStrengthsGatherer()
                console.print(f"  [dim]Processing {len(pdf_files)} PDF files...[/dim]")
                start = time.time()
                sections = gatherer.gather(data_dir)
                elapsed = time.time() - start
                total += len(sections)
                console.print(
                    f"  [{COLOR_SUCCESS}]✓ {len(sections)} sections in {elapsed:.1f}s[/{COLOR_SUCCESS}]"
                )
            else:
                console.print(
                    f"  [{COLOR_ERROR}]No CliftonStrengths PDFs found[/{COLOR_ERROR}]"
                )
            console.print()

            # CV
            cv_files = (
                list(data_dir.glob("*.md"))
                + list(data_dir.glob("*.pdf"))
                + list(data_dir.glob("*.txt"))
            )
            if cv_files:
                console.print("[bold]CV/Resume:[/bold]")
                gatherer = CVGatherer()
                for cv_file in cv_files:
                    try:
                        console.print(f"  [dim]Processing {cv_file.name}...[/dim]")
                        start = time.time()
                        sections = gatherer.gather(cv_file)
                        elapsed = time.time() - start
                        total += len(sections)
                        console.print(
                            f"  [{COLOR_SUCCESS}]✓ {len(sections)} sections[/{COLOR_SUCCESS}]"
                        )
                    except Exception as e:
                        console.print(
                            f"  [{COLOR_ERROR}]✗ Skip: {cv_file.name} ({e})[/{COLOR_ERROR}]"
                        )
            else:
                console.print(f"  [{COLOR_ERROR}]No CV files found[/{COLOR_ERROR}]")
            console.print()

            # Portfolio
            if settings.portfolio_url:
                console.print("[bold]Portfolio:[/bold]")
                console.print(f"  [dim]Fetching {settings.portfolio_url}...[/dim]")
                gatherer = PortfolioGatherer()
                start = time.time()
                sections = gatherer.gather(settings.portfolio_url)
                elapsed = time.time() - start
                total += len(sections)
                console.print(
                    f"  [{COLOR_SUCCESS}]✓ {len(sections)} sections in {elapsed:.1f}s[/{COLOR_SUCCESS}]"
                )
            else:
                console.print(
                    f"[bold]Portfolio:[/bold] [{COLOR_ERROR}]No URL configured[/{COLOR_ERROR}]"
                )
            console.print()

            if total > 0:
                console.print(
                    f"\n[bold {COLOR_SUCCESS}]═══════════════════════════════════════[/bold {COLOR_SUCCESS}]"  # noqa: E501
                )
                console.print(
                    f"[bold {COLOR_SUCCESS}]  Total: {total} sections indexed[/bold {COLOR_SUCCESS}]"
                )
                console.print(
                    f"[bold {COLOR_SUCCESS}]═══════════════════════════════════════[/bold {COLOR_SUCCESS}]\n"  # noqa: E501
                )
            else:
                console.print(
                    f"\n[{COLOR_ERROR}]No data files found. Add files to data/raw/[/{COLOR_ERROR}]\n"
                )
                console.print("Expected files:")
                console.print("  - LinkedIn: linkedin.zip (from LinkedIn export)")
                console.print("  - CliftonStrengths: *.pdf (Gallup PDF reports)")
                console.print("  - CV: *.md, *.pdf, or *.txt")
                console.print("  - Portfolio: configured in .env (PORTFOLIO_URL)\n")
        except Exception as e:
            import traceback

            console.print(f"\n[{COLOR_ERROR}]Gather failed:[/{COLOR_ERROR}] {e}")
            console.print(f"[dim]{traceback.format_exc()}[/dim]\n")
        return False

    if cmd == "/agents":
        # List available specialist agents
        orchestrator = get_orchestrator()
        agents = orchestrator.list_agents()
        console.print("[bold #5bc0be]Specialist Agents[/bold #5bc0be]\n")
        for a in agents:
            console.print(
                f"  [bold {COLOR_WARNING}]{a['namef']}[/bold {COLOR_WARNING}]: {a['description']}"
            )
        console.print()
        return False

    if cmd == "/debug":
        # Toggle debug/verbose mode
        current_level = logging.getLogger().level
        if current_level <= logging.DEBUG:
            logging.getLogger().setLevel(logging.WARNING)
            console.print(f"[{COLOR_ERROR}]Debug mode OFF[/{COLOR_ERROR}]\n")
        else:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger("fu7ur3pr00f").setLevel(logging.DEBUG)
            console.print(f"[{COLOR_SUCCESS}]Debug mode ON[/{COLOR_SUCCESS}]\n")
            console.print("[dim]You will now see:[/dim]")
            console.print("  - LLM API calls and responses")
            console.print("  - Tool execution details")
            console.print("  - Agent routing decisions")
            console.print("  - ChromaDB operations\n")
        return False

    if cmd == "/verbose":
        # Show detailed system info
        from fu7ur3pr00f.memory.checkpointer import get_data_dir

        model_name = get_orchestrator().get_model_name() or "unknown"
        console.print("[bold #5bc0be]System Information[/bold #5bc0be]\n")
        console.print(f"Data directory: {get_data_dir()}")
        console.print(f"LLM Provider: {settings.llm_provider or 'auto-detect'}")
        console.print(f"Model: {model_name}")
        console.print(f"Portfolio URL: {settings.portfolio_url or 'Not configured'}")
        console.print(
            f"GitHub MCP: {'Enabled' if settings.has_github_mcp else 'Disabled'}"
        )
        console.print(
            f"Tavily MCP: {'Enabled' if settings.has_tavily_mcp else 'Disabled'}"
        )
        console.print(
            f"Debug level: {logging.getLevelName(logging.getLogger().level)}\n"
        )
        return False

    if cmd == "/reset":
        import shutil

        from fu7ur3pr00f.memory.checkpointer import get_data_dir

        home_dir = get_data_dir()
        data_dir = settings.data_dir

        targets = [
            ("Conversations & checkpoints", home_dir / "memory.db"),
            ("User profile", home_dir / "profile.yaml"),
            ("Knowledge base & episodic memory", home_dir / "episodic"),
            ("Log file", home_dir / "fu7ur3pr00f.log"),
            ("Generated CVs", data_dir / "output"),
            ("Processed data", data_dir / "processed"),
            ("Market cache", data_dir / "cache"),
        ]

        console.print(f"[bold {COLOR_ERROR}]Factory Reset[/bold {COLOR_ERROR}]\n")
        console.print("This will delete:")
        for label, path in targets:
            exists = path.exists()
            status = "" if exists else " [dim](not found)[/dim]"
            console.print(f"  - {label}: {path}{status}")
        console.print(
            f"\n[{COLOR_SUCCESS}]Preserved:[/{COLOR_SUCCESS}] data/raw/ (LinkedIn ZIPs, PDFs)"
        )

        try:
            confirm = chat_state["session"].prompt("\nProceed? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = ""

        if confirm not in ("y", "yes"):
            console.print(f"[{COLOR_INFO}]Reset cancelled.[/{COLOR_INFO}]")
            return False

        deleted = 0
        for _label, path in targets:
            if not path.exists():
                continue
            if path.is_dir():
                if path.name in ("output", "processed"):
                    for item in path.iterdir():
                        if item.name == ".gitkeep":
                            continue
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink()
                else:
                    shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink()
            deleted += 1

        settings.ensure_directories()
        console.print(
            f"\n[{COLOR_SUCCESS}]Factory reset complete.[/{COLOR_SUCCESS}] Cleared {deleted} items."
        )
        console.print(
            f"[{COLOR_INFO}]Restart FutureProof to start fresh.[/{COLOR_INFO}]"
        )
        return True

    console.print(
        f"[{COLOR_WARNING}]Unknown command: {cmd}. Type /help for available commands.[/{COLOR_WARNING}]"
    )
    return False


def run_chat(
    thread_id: str = "main",
) -> None:  # noqa: C901 - Main chat loop with command/tool handling
    """Run the synchronous chat loop.

    Args:
        thread_id: Conversation thread identifier for persistence
    """
    # Set up prompt session with history
    history_path = get_history_path()
    history = FileHistory(str(history_path))
    session = PromptSession(history=history)
    if history_path.exists():
        history_path.chmod(0o600)

    # Display welcome message
    display_welcome()

    # First-run: if no LLM provider configured, launch setup wizard
    if not settings.active_provider:
        from fu7ur3pr00f.chat.setup import run_setup

        run_setup(console, first_run=True)

    # Initialise the orchestrator and display which model is active
    try:
        orchestrator = get_orchestrator()
        config = get_agent_config(thread_id=thread_id)

        model_name = orchestrator.get_model_name()
        if model_name:
            display_model_info(model_name)
    except Exception as e:
        from pydantic import ValidationError

        if isinstance(e, ValidationError) or isinstance(e.__cause__, ValidationError):
            display_error(
                f"Configuration error — check your settings.\n{e}\n\nRun /setup..."
            )
            from fu7ur3pr00f.chat.setup import run_setup

            run_setup(console, first_run=True)
            try:
                orchestrator = get_orchestrator()
                config = get_agent_config(thread_id=thread_id)
            except Exception as retry_err:
                display_error(_sanitize_error(f"Still failing: {retry_err}"))
                return
        else:
            display_error(_sanitize_error(f"Failed to initialize agent: {e}"))
            return

    # Mutable state shared with handle_command for /thread switching
    chat_state: dict = {
        "thread_id": thread_id,
        "config": config,
        "session": session,
    }

    while True:
        try:
            # Get user input
            user_input = session.prompt(
                _PROMPT_MSG,
                style=_PROMPT_STYLE,
                is_password=False,
            ).strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                if user_input.strip().lower() == "/setup":
                    from fu7ur3pr00f.chat.setup import run_setup

                    changed = run_setup(console)
                    if changed:
                        reset_orchestrator()
                        orchestrator = get_orchestrator()
                        model_name = orchestrator.get_model_name()
                        if model_name:
                            display_model_info(model_name)
                    continue
                if handle_command(user_input, chat_state=chat_state):
                    break
                # Pick up thread changes from /thread command
                config = chat_state["config"]
                continue

            # All queries go through conversation engine (outer graph)
            console.print()  # Blank line before response

            engine = get_conversation_engine()
            tool_start_times: dict[str, float] = {}

            def _on_specialist_start(name: str) -> None:
                display_specialist_progress(name, "working")

            def _on_specialist_complete(name: str, finding: dict) -> None:
                display_specialist_progress(name, "done")
                reasoning = finding.get("reasoning", "")
                if reasoning:
                    console.print(Markdown(reasoning))
                    console.print()

            def _on_tool_start(specialist: str, tool_name: str, args: dict) -> None:
                tool_start_times[f"{specialist}:{tool_name}"] = time.monotonic()
                display_tool_start(tool_name, args)

            def _on_tool_result(specialist: str, tool_name: str, result: str) -> None:
                key = f"{specialist}:{tool_name}"
                elapsed_t = time.monotonic() - tool_start_times.pop(
                    key, time.monotonic()
                )
                display_tool_result(tool_name, result, elapsed_t)

            def _confirm(question: str, details: str) -> bool:
                display_interrupt_confirmation(question, details)
                try:
                    resp = session.prompt("Approve? [y/N] ").strip().lower()
                    return resp in ("y", "yes")
                except (EOFError, KeyboardInterrupt):
                    return False

            try:
                result = engine.invoke_turn(
                    query=user_input,
                    thread_id=chat_state["thread_id"],
                    on_specialist_start=_on_specialist_start,
                    on_specialist_complete=_on_specialist_complete,
                    on_tool_start=_on_tool_start,
                    on_tool_result=_on_tool_result,
                    confirm_fn=_confirm,
                )
                # Display synthesis result
                display_blackboard_result(
                    synthesis=result.synthesis,
                    specialists_contributed=result.specialists,
                    elapsed=result.elapsed,
                )
                # Display suggestions if any
                if result.suggested_next:
                    console.print()
                    console.print("[dim]Suggested next:[/dim]")
                    for i, suggestion in enumerate(result.suggested_next, 1):
                        console.print(f"  {i}. {suggestion}")
            except Exception as e:
                logger.exception("Conversation execution failed")
                display_error(_sanitize_error(f"Analysis failed: {e}"))

        except KeyboardInterrupt:
            console.print(f"\n[{COLOR_INFO}]Use /quit to exit[/{COLOR_INFO}]")
            continue
        except EOFError:
            console.print(f"\n[{COLOR_INFO}]Goodbye![/{COLOR_INFO}]")
            break
        except Exception as e:
            # Catch unhandled exceptions from event loop / nest_asyncio
            # to prevent the chat from crashing
            logger.exception("Unhandled error in chat loop")
            if str(e):
                display_error(_sanitize_error(f"Unexpected error: {e}"))
            else:
                # Bare Exception() with no message — typically from
                # nest_asyncio/prompt_toolkit event loop conflicts
                console.print(
                    f"\n[{COLOR_INFO}]Press ENTER to continue...[/{COLOR_INFO}]"
                )
            continue
