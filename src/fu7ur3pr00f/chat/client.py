"""Chat client for FutureProof conversational interface.

Combines prompt-toolkit for input handling with Rich for output display.
Provides both sync and async chat loops for different use cases.
"""

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style as PTStyle
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from fu7ur3pr00f.agents.career_agent import (
    create_career_agent,
    get_agent_config,
    get_agent_model_name,
    reset_career_agent,
)
from fu7ur3pr00f.agents.multi_agent import (
    handle_query as handle_multi_agent_query,
)
from fu7ur3pr00f.agents.multi_agent import (
    list_agents as list_multi_agents,
)
from fu7ur3pr00f.chat.ui import (
    console,
    display_error,
    display_goals,
    display_help,
    display_model_info,
    display_model_switch,
    display_node_transition,
    display_profile_summary,
    display_timing,
    display_tool_result,
    display_tool_start,
    display_welcome,
)
from fu7ur3pr00f.config import settings
from fu7ur3pr00f.llm.fallback import get_fallback_manager
from fu7ur3pr00f.memory.checkpointer import get_data_dir

logger = logging.getLogger(__name__)

# ── Prompt styling ────────────────────────────────────────────────────────

_PROMPT_STYLE = PTStyle.from_dict({"prompt": "#ffd700 bold"})
_PROMPT_MSG = HTML("<prompt>\u25b6 </prompt>")

# Known section headers from SummarizationMiddleware output.
# The LLM sometimes echoes these verbatim at the start of a response.
_SUMMARY_SECTIONS = (
    "session intent",
    "summary",
    "artifacts",
    "next steps",
    "key context",
)

# Detects period immediately followed by a capital letter (no space) — a sign
# that the LLM concatenated summary content with the real response.
# Matches ".I " (pronoun), ".The", ".However", etc.
_CONCAT_RE = re.compile(r"\.([A-Z](?:[a-z]| ))")

# Patterns that might leak API keys or tokens in error messages
_SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{8})[A-Za-z0-9]+")
_BEARER_RE = re.compile(r"(Bearer\s+)[^\s\"']+", re.IGNORECASE)


def _sanitize_error(msg: str) -> str:
    """Redact API keys and bearer tokens from error messages."""
    msg = _SECRET_RE.sub(r"\1...", msg)
    msg = _BEARER_RE.sub(r"\1[REDACTED]", msg)
    return msg


def _is_tool_call_state_error(error: Exception) -> bool:
    """Check if error is caused by orphaned tool_calls in state.

    This happens when parallel tool execution via the Send API fails to
    merge ToolMessage results back into the messages channel. Azure rejects
    the next model call with "tool_call_ids did not have response messages".
    """
    error_str = str(error).lower()
    return "tool_call_ids" in error_str and "response messages" in error_str


def _might_be_summary_start(text: str) -> bool:
    """Check if partial streaming text could be the start of a summary echo.

    Used during streaming to suppress display of text that might become
    a full summary section header once more chunks arrive. Requires at
    least 4 characters to avoid false positives on common words.
    """
    first_line = text.lower().lstrip().split("\n", 1)[0].strip("#*").strip()
    if len(first_line) < 4:
        return False
    for section in _SUMMARY_SECTIONS:
        if section.startswith(first_line) or first_line.startswith(section):
            return True
    return first_line.startswith(
        ("here is a summ", "here's a summ", "summary of the")
    )


def _is_summary_echo(text: str) -> bool:
    """Detect if text starts with a SummarizationMiddleware echo.

    Matches two patterns:
    1. "Here is a summary of the conversation..." preamble
    2. Direct section headers like "SESSION INTENT" at the start
    """
    lower = text.lower().lstrip()
    # Pattern 1: explicit summary preamble
    if lower.startswith(("here is a summary", "here's a summary", "summary of the conversation")):
        return True
    # Pattern 2: starts with a known summary section header
    first_line = lower.split("\n", 1)[0].strip().strip("#*").strip()
    return first_line in _SUMMARY_SECTIONS


def _strip_summary_echo(text: str) -> str:
    """Remove an echoed conversation summary from the start of a response.

    When SummarizationMiddleware compresses history, the LLM sometimes echoes
    the injected summary verbatim before giving its real answer. This function
    detects that pattern and returns only the real answer portion.

    Returns the cleaned text, or empty string if the entire text so far is
    still part of the summary (caller should skip the display update).
    """
    if not _is_summary_echo(text):
        return text

    # Find the position just after the last summary section header in the text.
    # Section headers appear as standalone lines like "SESSION INTENT", "SUMMARY",
    # "NEXT STEPS", etc. (possibly with markdown formatting).
    last_header_end = 0
    for section in _SUMMARY_SECTIONS:
        pattern = re.compile(
            r"^[#*\s]*" + re.escape(section) + r"[*\s]*$",
            re.IGNORECASE | re.MULTILINE,
        )
        for match in pattern.finditer(text):
            if match.end() > last_header_end:
                last_header_end = match.end()

    if last_header_end == 0:
        return text

    # Content after the last section header — this contains the section body
    # and potentially the real response concatenated to it.
    remaining = text[last_header_end:]

    # Check for period-capital concatenation (e.g., "...for each.I can't debug...")
    # This happens when the LLM glues the last summary bullet to the real response.
    concat_match = _CONCAT_RE.search(remaining)
    if concat_match:
        return remaining[concat_match.start() + 1 :]

    # Look for a double-newline boundary: the first paragraph block is section
    # content, subsequent blocks that aren't section headers are the real response.
    blocks = remaining.split("\n\n")
    found_content = False
    for i, block in enumerate(blocks):
        if not block.strip():
            continue
        if not found_content:
            found_content = True
            continue
        # If this block is another summary section header, skip it and its content
        header_text = block.strip().lower().strip("#*").strip()
        if header_text in _SUMMARY_SECTIONS:
            found_content = False  # next non-empty block is this section's content
            continue
        # Real response
        return "\n\n".join(blocks[i:])

    # Everything parsed so far is still summary
    return ""


def _make_input(content: str) -> dict[str, Any]:
    """Build the agent input dict from user text."""
    return {"messages": [HumanMessage(content=content)]}


def get_history_path() -> Path:
    """Get the path for command history file."""
    return get_data_dir() / "chat_history"


def handle_command(command: str, *, chat_state: dict) -> bool:
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
        console.print("[#415a77]Goodbye! Your conversation is saved.[/#415a77]")
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
        console.print("[#415a77]Conversation history cleared.[/#415a77]")
        return False

    if cmd == "/thread":
        if not arg:
            console.print(
                f"[#415a77]Current thread: [bold]{chat_state['thread_id']}[/bold][/#415a77]"
            )
        else:
            chat_state["thread_id"] = arg
            chat_state["config"] = get_agent_config(thread_id=arg)
            console.print(f"[#10b981]Switched to thread: [bold]{arg}[/bold][/#10b981]")
        return False

    if cmd == "/threads":
        from fu7ur3pr00f.memory.checkpointer import list_threads

        thread_list = list_threads()
        if thread_list:
            console.print("[bold #e0d8c0]Conversation threads:[/bold #e0d8c0]")
            for t in thread_list:
                marker = " (active)" if t == chat_state["thread_id"] else ""
                console.print(f"  - {t}[bold #ffd700]{marker}[/bold #ffd700]")
        else:
            console.print("[#415a77]No conversation threads found.[/#415a77]")
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
            
            console.print(f"\n[#10b981]✓ Gathered {len(sections)} sections from all sources[/#10b981]")
            console.print("[#10b981]✓ Data indexed to knowledge base[/#10b981]\n")
        except ImportError as e:
            # Fallback: run gatherers directly
            console.print(f"[dim]Fallback mode (ImportError: {e})[/dim]\n")
            
            from fu7ur3pr00f.gatherers.linkedin import LinkedInGatherer
            from fu7ur3pr00f.gatherers.cliftonstrengths import CliftonStrengthsGatherer
            from fu7ur3pr00f.gatherers.cv import CVGatherer
            from fu7ur3pr00f.gatherers.portfolio import PortfolioGatherer
            from fu7ur3pr00f.config import settings
            from pathlib import Path
            
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
                    console.print(f"  [#10b981]✓ {len(sections)} sections in {elapsed:.1f}s[/#10b981]")
            else:
                console.print("  [#ff6b6b]No LinkedIn ZIP found[/#ff6b6b]")
            console.print()
            
            # CliftonStrengths
            pdf_files = [f for f in data_dir.glob("*.pdf") if 'strength' in f.name.lower()]
            if pdf_files:
                console.print("[bold]CliftonStrengths:[/bold]")
                gatherer = CliftonStrengthsGatherer()
                console.print(f"  [dim]Processing {len(pdf_files)} PDF files...[/dim]")
                start = time.time()
                sections = gatherer.gather(data_dir)
                elapsed = time.time() - start
                total += len(sections)
                console.print(f"  [#10b981]✓ {len(sections)} sections in {elapsed:.1f}s[/#10b981]")
            else:
                console.print("  [#ff6b6b]No CliftonStrengths PDFs found[/#ff6b6b]")
            console.print()
            
            # CV
            cv_files = list(data_dir.glob("*.md")) + list(data_dir.glob("*.pdf")) + list(data_dir.glob("*.txt"))
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
                        console.print(f"  [#10b981]✓ {len(sections)} sections in {elapsed:.1f}s[/#10b981]")
                    except Exception as e:
                        console.print(f"  [#ff6b6b]✗ Skip: {cv_file.name} ({e})[/#ff6b6b]")
            else:
                console.print("  [#ff6b6b]No CV files found[/#ff6b6b]")
            console.print()
            
            # Portfolio
            if settings.portfolio_url:
                console.print(f"[bold]Portfolio:[/bold]")
                console.print(f"  [dim]Fetching {settings.portfolio_url}...[/dim]")
                gatherer = PortfolioGatherer()
                start = time.time()
                sections = gatherer.gather(settings.portfolio_url)
                elapsed = time.time() - start
                total += len(sections)
                console.print(f"  [#10b981]✓ {len(sections)} sections in {elapsed:.1f}s[/#10b981]")
            else:
                console.print("[bold]Portfolio:[/bold] [#ff6b6b]No PORTFOLIO_URL configured[/#ff6b6b]")
            console.print()
            
            if total > 0:
                console.print(f"\n[bold #10b981]═══════════════════════════════════════[/bold #10b981]")
                console.print(f"[bold #10b981]  Total: {total} sections indexed[/bold #10b981]")
                console.print(f"[bold #10b981]═══════════════════════════════════════[/bold #10b981]\n")
            else:
                console.print("\n[#ff6b6b]No data files found. Add files to data/raw/[/#ff6b6b]\n")
                console.print("Expected files:")
                console.print("  - LinkedIn: linkedin.zip (from LinkedIn export)")
                console.print("  - CliftonStrengths: *.pdf (Gallup PDF reports)")
                console.print("  - CV: *.md, *.pdf, or *.txt")
                console.print(f"  - Portfolio: configured in .env (PORTFOLIO_URL)\n")
        except Exception as e:
            import traceback
            console.print(f"\n[#ff6b6b]Gather failed:[/#ff6b6b] {e}")
            console.print(f"[dim]{traceback.format_exc()}[/dim]\n")
        return False

    if cmd == "/multi":
        # Multi-agent system command
        if arg == "agents":
            # List available specialist agents
            try:
                agents = asyncio.run(list_multi_agents())
                console.print("[bold #5bc0be]Specialist Agents[/bold #5bc0be]\n")
                for agent in agents:
                    agent_line = (
                        f"  [bold #ffd700]{agent['name']}[/bold #ffd700]: "
                        f"{agent['description']}"
                    )
                    console.print(agent_line)
                console.print()
            except Exception as e:
                display_error(f"Failed to list agents: {e}")
        elif arg == "test":
            # Test multi-agent system
            console.print("[bold #5bc0be]Testing multi-agent system...[/bold #5bc0be]")
            try:
                response = asyncio.run(handle_multi_agent_query("What agents are available?"))
                console.print("[#10b981]Multi-agent system is working![/#10b981]")
                console.print(f"Response preview: {response[:200]}...")
            except Exception as e:
                display_error(f"Multi-agent test failed: {e}")
        else:
            console.print("[bold #5bc0be]Multi-Agent System[/bold #5bc0be]\n")
            console.print("Usage: /multi [command]\n")
            console.print("Commands:")
            console.print("  /multi agents  - List available specialist agents")
            console.print("  /multi test    - Test multi-agent system\n")
            console.print("The multi-agent system provides specialized agents for:")
            console.print("  - Career growth (Coach)")
            console.print("  - Skill development (Learning)")
            console.print("  - Job search (Jobs)")
            console.print("  - Code projects (Code)")
            console.print("  - Startups (Founder)\n")
        return False

    if cmd == "/debug":
        # Toggle debug/verbose mode
        current_level = logging.getLogger().level
        if current_level <= logging.DEBUG:
            logging.getLogger().setLevel(logging.WARNING)
            console.print("[#ff6b6b]Debug mode OFF[/#ff6b6b]\n")
        else:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger("fu7ur3pr00f").setLevel(logging.DEBUG)
            console.print("[#10b981]Debug mode ON[/#10b981]\n")
            console.print("[dim]You will now see:[/dim]")
            console.print("  - LLM API calls and responses")
            console.print("  - Tool execution details")
            console.print("  - Agent routing decisions")
            console.print("  - ChromaDB operations\n")
        return False

    if cmd == "/verbose":
        # Show detailed system info
        from fu7ur3pr00f.memory.checkpointer import get_data_dir
        
        console.print("[bold #5bc0be]System Information[/bold #5bc0be]\n")
        console.print(f"Data directory: {get_data_dir()}")
        console.print(f"LLM Provider: {settings.llm_provider or 'auto-detect'}")
        console.print(f"Model: {get_agent_model_name()}")
        console.print(f"Portfolio URL: {settings.portfolio_url or 'Not configured'}")
        console.print(f"GitHub MCP: {'Enabled' if settings.has_github_mcp else 'Disabled'}")
        console.print(f"Tavily MCP: {'Enabled' if settings.has_tavily_mcp else 'Disabled'}")
        console.print(f"Debug level: {logging.getLevelName(logging.getLogger().level)}\n")
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

        console.print("[bold #ff6b6b]Factory Reset[/bold #ff6b6b]\n")
        console.print("This will delete:")
        for label, path in targets:
            exists = path.exists()
            status = "" if exists else " [dim](not found)[/dim]"
            console.print(f"  - {label}: {path}{status}")
        console.print("\n[#10b981]Preserved:[/#10b981] data/raw/ (LinkedIn ZIPs, PDFs)")

        try:
            confirm = chat_state["session"].prompt("\nProceed? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = ""

        if confirm not in ("y", "yes"):
            console.print("[#415a77]Reset cancelled.[/#415a77]")
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
        console.print(f"\n[#10b981]Factory reset complete.[/#10b981] Cleared {deleted} items.")
        console.print("[#415a77]Restart FutureProof to start fresh.[/#415a77]")
        return True

    console.print(f"[#ffd700]Unknown command: {cmd}. Type /help for available commands.[/#ffd700]")
    return False


class _ChunkAccumulator:
    """Accumulates streamed chunks, tracking the latest AI message buffer."""

    __slots__ = ("full_response", "msg_id", "msg_buf")

    def __init__(self) -> None:
        self.full_response = ""
        self.msg_id: str | None = None
        self.msg_buf = ""

    def accumulate(self, chunk: Any) -> str:
        """Extract text from a chunk and append to buffers.

        Returns the extracted content string (empty if chunk had no text).
        """
        if not (hasattr(chunk, "content") and chunk.content):  # type: ignore[union-attr]
            return ""
        content = chunk.content  # type: ignore[union-attr]
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        chunk_id = getattr(chunk, "id", None)
        if chunk_id and chunk_id != self.msg_id:
            self.msg_id = chunk_id
            self.msg_buf = ""
        self.full_response += content
        self.msg_buf += content
        return content


def _stream_to_live(
    stream_iter,
    acc: _ChunkAccumulator,
    con: Console,
    verbose_fn=None,
) -> None:
    """Stream chunks to a Rich Live widget, stripping summary echoes.

    Args:
        stream_iter: Iterable of (chunk, metadata) pairs
        acc: Chunk accumulator for the stream
        con: Rich console for display
        verbose_fn: Optional callback(chunk, metadata) -> bool.
            If it returns True, the chunk is considered consumed
            (tool display) and won't be accumulated.
    """
    start = time.monotonic()
    with Live(Markdown(""), console=con, refresh_per_second=10) as live:
        for chunk, metadata in stream_iter:
            if verbose_fn and verbose_fn(chunk, metadata):
                continue
            if acc.accumulate(chunk):
                buf = acc.msg_buf
                if _might_be_summary_start(buf):
                    if "\n" in buf:
                        stripped = _strip_summary_echo(buf)
                        # Strip returns buf unchanged when preamble is
                        # detected but section headers haven't arrived —
                        # still in echo territory, suppress display.
                        if stripped and stripped != buf:
                            live.update(Markdown(stripped))
                            continue
                    live.update(Markdown(""))
                    continue
                live.update(Markdown(buf))
    display_timing(time.monotonic() - start)


def _stream_response(
    agent: Any,
    input_message: Any,
    config: dict[str, Any],
    console: Console,
    session: PromptSession,  # type: ignore[type-arg]
) -> tuple[str, set[str]]:
    """Stream agent response, handling interrupts for human-in-the-loop.

    Returns:
        Tuple of (full_response_text, shown_tool_names)
    """
    shown_tools: set[str] = set()
    tool_start_times: dict[str, float] = {}
    last_node = ""
    acc = _ChunkAccumulator()

    def _verbose_print(chunk, metadata) -> bool:
        """Print verbose tool/node info. Returns True if chunk was consumed."""
        nonlocal last_node
        node = metadata.get("langgraph_node", "")
        if node and node != last_node:
            display_node_transition(node)
            last_node = node
        tool_calls = getattr(chunk, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                name = tc.get("name", "unknown")
                if name not in shown_tools:
                    shown_tools.add(name)
                    tool_start_times[name] = time.monotonic()
                    args = tc.get("args", {})
                    display_tool_start(name, args)
        if getattr(chunk, "type", None) == "tool":
            tool_content = getattr(chunk, "content", "")
            tool_name = getattr(chunk, "name", None)
            # Skip synthetic repair messages (no name, injected by ToolCallRepairMiddleware)
            if not tool_name:
                return True
            elapsed: float | None = None
            if tool_name in tool_start_times:
                elapsed = time.monotonic() - tool_start_times.pop(tool_name)
            if tool_content:
                display_tool_result(tool_name, tool_content, elapsed)
            return True
        return False

    def _stream_iter():
        return agent.stream(
            input_message,
            cast(RunnableConfig, config),
            stream_mode="messages",
        )

    logger.debug("Stream started")
    _stream_to_live(_stream_iter(), acc, console, _verbose_print)
    logger.debug("Stream ended")

    # Use the cleaned version as the final response
    full_response = _strip_summary_echo(acc.full_response) or acc.full_response

    # Handle human-in-the-loop interrupts (loop instead of recursion to avoid
    # deep stacks when multiple HITL tools fire in sequence)
    while True:
        logger.debug("Checking for HITL interrupts...")
        state = agent.get_state(cast(RunnableConfig, config))
        logger.debug("State retrieved, interrupts=%d", len(state.interrupts))
        if not state.interrupts:
            break

        interrupt_data = state.interrupts[0].value
        question = interrupt_data.get("question", "Proceed?")
        details = interrupt_data.get("details", "")

        console.print(f"[bold #ffd700]{question}[/bold #ffd700]")
        if details:
            console.print(f"[#415a77]{details}[/#415a77]")

        answer = (
            session.prompt(
                HTML("<prompt>[Y/n]: </prompt>"),
                style=_PROMPT_STYLE,
                is_password=False,
            ).strip().lower()
        )
        approved = answer in ("", "y", "yes")

        logger.info("HITL resume: approved=%s", approved)
        console.print()  # spacing before resume output

        # Resume the graph with the user's decision
        resume_acc = _ChunkAccumulator()
        logger.debug("Resume stream started")

        resume_iter = agent.stream(
            Command(resume=approved),
            cast(RunnableConfig, config),
            stream_mode="messages",
        )
        _stream_to_live(resume_iter, resume_acc, console, _verbose_print)

        logger.debug("Resume stream ended")

        resume_text = _strip_summary_echo(resume_acc.full_response) or resume_acc.full_response
        if resume_text:
            full_response += resume_text

    return full_response, shown_tools


def run_chat(thread_id: str = "main") -> None:
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

    # Create agent
    try:
        agent = create_career_agent()
        config = get_agent_config(thread_id=thread_id)

        model_name = get_agent_model_name()
        if model_name:
            display_model_info(model_name)
    except Exception as e:
        from pydantic import ValidationError

        if isinstance(e, ValidationError) or isinstance(e.__cause__, ValidationError):
            display_error(
                "Configuration error — check your settings.\n"
                f"{e}\n\nLaunching /setup to fix..."
            )
            from fu7ur3pr00f.chat.setup import run_setup

            run_setup(console, first_run=True)
            try:
                agent = create_career_agent()
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
                _PROMPT_MSG, style=_PROMPT_STYLE, is_password=False,
            ).strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                if user_input.strip().lower() == "/setup":
                    from fu7ur3pr00f.chat.setup import run_setup

                    changed = run_setup(console)
                    if changed:
                        reset_career_agent()
                        agent = create_career_agent()
                        model_name = get_agent_model_name()
                        if model_name:
                            display_model_info(model_name)
                    continue
                if handle_command(user_input, chat_state=chat_state):
                    break
                # Pick up thread changes from /thread command
                config = chat_state["config"]
                continue

            # Send to agent and stream response
            console.print()  # Blank line before response

            input_message = _make_input(user_input)

            # Collect full response for markdown rendering
            full_response = ""
            shown_tools: set[str] = set()  # Track which tools we've shown

            # Retry loop for automatic fallback on rate limits
            max_retries = 8  # Support full fallback chain
            for attempt in range(max_retries):
                try:
                    full_response, shown_tools = _stream_response(
                        agent, input_message, config, console, session
                    )
                    break  # Success, exit retry loop

                except Exception as e:
                    # Tool call state error: retry with same model — the
                    # ToolCallRepairMiddleware will fix state on next attempt
                    if _is_tool_call_state_error(e) and attempt < max_retries - 1:
                        logger.warning(
                            "Tool state error (attempt %d/%d), retrying", attempt + 1, max_retries
                        )
                        console.print(
                            "[#ffd700]Recovering from tool state error, retrying...[/#ffd700]"
                        )
                        continue

                    # Check if this is an error we can recover from via fallback
                    fallback_mgr = get_fallback_manager()
                    if fallback_mgr.handle_error(e) and attempt < max_retries - 1:
                        # Try with fallback model
                        status = fallback_mgr.get_status()
                        available = status.get("available_models", [])
                        next_model = available[0] if available else "unknown"
                        logger.warning(
                            "Model error (attempt %d/%d): %s — switching to %s",
                            attempt + 1,
                            max_retries,
                            e,
                            next_model,
                        )
                        display_model_switch(next_model)
                        # Recreate agent with new model
                        reset_career_agent()
                        agent = create_career_agent()
                        continue
                    else:
                        # Log full traceback to file only, show user-friendly message
                        logger.exception("Unrecoverable agent error")
                        error_msg = _sanitize_error(f"Agent error: {e}")

                        # Provide helpful context for common errors
                        if "Connection error" in str(e) or "ConnectError" in str(type(e).__name__):
                            error_msg = (
                                "Cannot connect to LLM provider. "
                                "Check your internet connection and API credentials. "
                                "Run '/setup' to reconfigure."
                            )
                        elif "APIConnectionError" in str(type(e).__name__):
                            error_msg = (
                                "Cannot connect to LLM provider. "
                                "Check your internet connection and API credentials. "
                                "Run '/setup' to reconfigure."
                            )

                        display_error(error_msg)
                        break

        except KeyboardInterrupt:
            console.print("\n[#415a77]Use /quit to exit[/#415a77]")
            continue
        except EOFError:
            console.print("\n[#415a77]Goodbye![/#415a77]")
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
                console.print("\n[#415a77]Press ENTER to continue...[/#415a77]")
            continue


