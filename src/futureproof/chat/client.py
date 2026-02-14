"""Chat client for FutureProof conversational interface.

Combines prompt-toolkit for input handling with Rich for output display.
Provides both sync and async chat loops for different use cases.
"""

import re
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from futureproof.agents.career_agent import (
    create_career_agent,
    get_agent_config,
    reset_career_agent,
)
from futureproof.chat.ui import (
    display_error,
    display_goals,
    display_help,
    display_profile_summary,
    display_welcome,
)
from futureproof.llm.fallback import get_fallback_manager
from futureproof.memory.checkpointer import get_data_dir

console = Console()

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


def get_history_path() -> Path:
    """Get the path for command history file."""
    return get_data_dir() / "chat_history"


def handle_command(command: str) -> bool:
    """Handle slash commands.

    Args:
        command: The command string (including leading /)

    Returns:
        True if the chat should exit, False otherwise
    """
    cmd = command.lower().strip()

    if cmd in ("/quit", "/q", "/exit"):
        console.print("[dim]Goodbye! Your conversation is saved.[/dim]")
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
        from futureproof.memory.checkpointer import clear_thread_history

        clear_thread_history("main")
        console.print("[dim]Conversation history cleared.[/dim]")
        return False

    console.print(f"[yellow]Unknown command: {cmd}. Type /help for available commands.[/yellow]")
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


def _stream_to_live(stream_iter, acc: _ChunkAccumulator, con: Console) -> None:
    """Stream chunks to a Rich Live widget, stripping summary echoes."""
    with Live(Markdown(""), console=con, refresh_per_second=10) as live:
        for chunk, metadata in stream_iter:
            if getattr(chunk, "type", None) == "tool":
                continue
            if acc.accumulate(chunk):
                display_text = _strip_summary_echo(acc.msg_buf)
                if display_text:
                    live.update(Markdown(display_text))
    con.print()


def _stream_response(
    agent: Any,
    input_message: Any,
    config: dict[str, Any],
    verbose: bool,
    console: Console,
    session: PromptSession,  # type: ignore[type-arg]
) -> tuple[str, set[str]]:
    """Stream agent response, handling interrupts for human-in-the-loop.

    Returns:
        Tuple of (full_response_text, shown_tool_names)
    """
    shown_tools: set[str] = set()
    last_node = ""
    acc = _ChunkAccumulator()

    def _verbose_print(chunk, metadata) -> bool:
        """Print verbose tool/node info. Returns True if chunk was consumed."""
        nonlocal last_node
        node = metadata.get("langgraph_node", "")
        if node and node != last_node:
            console.print(f"[dim]@ {node}[/dim]")
            last_node = node
        tool_calls = getattr(chunk, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                name = tc.get("name", "unknown")
                if name not in shown_tools:
                    shown_tools.add(name)
                    args = tc.get("args", {})
                    args_str = ", ".join(f"{k}={v!r}" for k, v in args.items()) if args else ""
                    console.print(f"[dim]> {name}({args_str})[/dim]")
        if getattr(chunk, "type", None) == "tool":
            tool_content = getattr(chunk, "content", "")
            tool_name = getattr(chunk, "name", "tool")
            if tool_content:
                preview = (tool_content[:150] + "...") if len(tool_content) > 150 else tool_content
                console.print(f"[dim]< {tool_name}: {preview}[/dim]")
            return True
        return False

    def _stream_iter():
        return agent.stream(
            input_message,
            cast(RunnableConfig, config),
            stream_mode="messages",
        )

    if verbose:
        # Verbose mode: print tool info directly, no Live widget.
        for chunk, metadata in _stream_iter():
            if _verbose_print(chunk, metadata):
                continue
            acc.accumulate(chunk)
        # Render only the final AI response once
        display_text = _strip_summary_echo(acc.msg_buf)
        if display_text:
            console.print()
            console.print(Markdown(display_text))
        console.print()
    else:
        _stream_to_live(_stream_iter(), acc, console)

    # Use the cleaned version as the final response
    full_response = _strip_summary_echo(acc.full_response) or acc.full_response

    # Check for human-in-the-loop interrupts
    state = agent.get_state(cast(RunnableConfig, config))
    if state.interrupts:
        interrupt_data = state.interrupts[0].value
        question = interrupt_data.get("question", "Proceed?")
        details = interrupt_data.get("details", "")

        console.print(f"[yellow bold]{question}[/yellow bold]")
        if details:
            console.print(f"[dim]{details}[/dim]")

        answer = session.prompt("[Y/n]: ").strip().lower()
        approved = answer in ("", "y", "yes")

        # Resume the graph with the user's decision
        resume_response, resume_tools = _stream_response(
            agent, Command(resume=approved), config, verbose, console, session
        )
        if resume_response:
            full_response += resume_response
        shown_tools |= resume_tools

    return full_response, shown_tools


def run_chat(thread_id: str = "main", verbose: bool = False) -> None:
    """Run the synchronous chat loop.

    Args:
        thread_id: Conversation thread identifier for persistence
        verbose: If True, show tool usage and agent reasoning
    """
    # Set up prompt session with history
    history = FileHistory(str(get_history_path()))
    session = PromptSession(history=history)

    # Display welcome message
    display_welcome()

    # Create agent
    try:
        agent = create_career_agent()
        config = get_agent_config(thread_id=thread_id)

        # Show which model is being used in verbose mode
        if verbose:
            fallback_mgr = get_fallback_manager()
            status = fallback_mgr.get_status()
            if status["current_model"]:
                console.print(f"[dim]🤖 Model: {status['current_model']}[/dim]\n")
    except Exception as e:
        display_error(f"Failed to initialize agent: {e}")
        return

    while True:
        try:
            # Get user input
            user_input = session.prompt("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                if handle_command(user_input):
                    break
                continue

            # Send to agent and stream response
            console.print()  # Blank line before response

            input_message = {"messages": [HumanMessage(content=user_input)]}

            # Collect full response for markdown rendering
            full_response = ""
            shown_tools: set[str] = set()  # Track which tools we've shown

            # Retry loop for automatic fallback on rate limits
            max_retries = 8  # Support full fallback chain
            for attempt in range(max_retries):
                try:
                    full_response, shown_tools = _stream_response(
                        agent, input_message, config, verbose, console, session
                    )
                    break  # Success, exit retry loop

                except Exception as e:
                    # Check if this is an error we can recover from via fallback
                    fallback_mgr = get_fallback_manager()
                    if fallback_mgr.handle_error(e) and attempt < max_retries - 1:
                        # Try with fallback model
                        status = fallback_mgr.get_status()
                        available = status.get("available_models", [])
                        next_model = available[0] if available else "unknown"
                        console.print(
                            f"[yellow]Model unavailable, switching to: {next_model}[/yellow]"
                        )
                        # Recreate agent with new model
                        reset_career_agent()
                        agent = create_career_agent()
                        continue
                    else:
                        display_error(f"Agent error: {e}")
                        break

        except KeyboardInterrupt:
            console.print("\n[dim]Use /quit to exit[/dim]")
            continue
        except EOFError:
            console.print("\n[dim]Goodbye![/dim]")
            break
        except Exception as e:
            # Catch unhandled exceptions from event loop / nest_asyncio
            # to prevent the chat from crashing
            if str(e):
                display_error(f"Unexpected error: {e}")
            else:
                # Bare Exception() with no message — typically from
                # nest_asyncio/prompt_toolkit event loop conflicts
                console.print("\n[dim]Press ENTER to continue...[/dim]")
            continue


async def run_chat_async(thread_id: str = "main") -> None:
    """Run the async chat loop.

    This is the preferred method for integration with async applications.

    Args:
        thread_id: Conversation thread identifier for persistence
    """
    from prompt_toolkit.patch_stdout import patch_stdout

    # Set up prompt session with history
    history = FileHistory(str(get_history_path()))
    session = PromptSession(history=history)

    # Display welcome message
    display_welcome()

    # Create agent
    try:
        agent = create_career_agent()
        config = get_agent_config(thread_id=thread_id)
    except Exception as e:
        display_error(f"Failed to initialize agent: {e}")
        return

    while True:
        try:
            # Get user input (async)
            with patch_stdout():
                user_input = await session.prompt_async("You: ")

            user_input = user_input.strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                if handle_command(user_input):
                    break
                continue

            # Send to agent and stream response
            console.print()

            input_message: Any = {"messages": [HumanMessage(content=user_input)]}

            try:
                acc = _ChunkAccumulator()

                async def _astream():
                    async for item in agent.astream(
                        input_message,
                        cast(RunnableConfig, config),
                        stream_mode="messages",
                    ):
                        yield item

                # Collect chunks async, render via Live
                with Live(Markdown(""), console=console, refresh_per_second=10) as live:
                    async for chunk, metadata in _astream():
                        if getattr(chunk, "type", None) == "tool":
                            continue
                        if acc.accumulate(chunk):
                            display_text = _strip_summary_echo(acc.msg_buf)
                            if display_text:
                                live.update(Markdown(display_text))

                console.print()

            except Exception as e:
                display_error(f"Agent error: {e}")

        except KeyboardInterrupt:
            console.print("\n[dim]Use /quit to exit[/dim]")
            continue
        except EOFError:
            console.print("\n[dim]Goodbye![/dim]")
            break


def ask(question: str, thread_id: str = "main") -> str:
    """Ask a single question and get a response.

    This is for one-shot queries without entering the full chat loop.

    Args:
        question: The question to ask
        thread_id: Conversation thread for context

    Returns:
        The agent's response as a string
    """
    agent = create_career_agent()
    config = get_agent_config(thread_id=thread_id)

    input_message: Any = {"messages": [HumanMessage(content=question)]}
    acc = _ChunkAccumulator()

    stream_iter = agent.stream(
        input_message,
        cast(RunnableConfig, config),
        stream_mode="messages",
    )
    _stream_to_live(stream_iter, acc, console)

    return _strip_summary_echo(acc.full_response) or acc.full_response
