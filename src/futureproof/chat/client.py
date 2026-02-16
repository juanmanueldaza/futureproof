"""Chat client for FutureProof conversational interface.

Combines prompt-toolkit for input handling with Rich for output display.
Provides both sync and async chat loops for different use cases.
"""

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

from futureproof.agents.career_agent import (
    create_career_agent,
    get_agent_config,
    get_agent_model_name,
    reset_career_agent,
)
from futureproof.chat.ui import (
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
from futureproof.llm.fallback import get_fallback_manager
from futureproof.memory.checkpointer import get_data_dir

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


def _is_tool_call_state_error(error: Exception) -> bool:
    """Check if error is caused by orphaned tool_calls in state.

    This happens when parallel tool execution via the Send API fails to
    merge ToolMessage results back into the messages channel. Azure rejects
    the next model call with "tool_call_ids did not have response messages".
    """
    error_str = str(error).lower()
    return "tool_call_ids" in error_str and "response messages" in error_str


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


def handle_command(command: str) -> bool:
    """Handle slash commands.

    Args:
        command: The command string (including leading /)

    Returns:
        True if the chat should exit, False otherwise
    """
    cmd = command.lower().strip()

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
        from futureproof.memory.checkpointer import clear_thread_history

        clear_thread_history("main")
        console.print("[#415a77]Conversation history cleared.[/#415a77]")
        return False

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


def _update_live_from_chunk(chunk: Any, acc: _ChunkAccumulator, live: Live) -> None:
    """Process a single chunk: accumulate and update the Live widget."""
    if getattr(chunk, "type", None) == "tool":
        return
    if acc.accumulate(chunk):
        display_text = _strip_summary_echo(acc.msg_buf)
        if display_text:
            live.update(Markdown(display_text))


def _stream_to_live(stream_iter, acc: _ChunkAccumulator, con: Console) -> None:
    """Stream chunks to a Rich Live widget, stripping summary echoes."""
    with Live(Markdown(""), console=con, refresh_per_second=10) as live:
        for chunk, metadata in stream_iter:
            _update_live_from_chunk(chunk, acc, live)
    con.print()


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
            tool_name = getattr(chunk, "name", "tool")
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

    stream_start = time.monotonic()
    logger.debug("Stream started")

    for chunk, metadata in _stream_iter():
        if _verbose_print(chunk, metadata):
            continue
        acc.accumulate(chunk)
    # Render only the final AI response once
    display_text = _strip_summary_echo(acc.msg_buf)
    if display_text:
        console.print()
        console.print(Markdown(display_text))
    display_timing(time.monotonic() - stream_start)

    logger.debug("Stream ended (%.1fs)", time.monotonic() - stream_start)

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
            session.prompt(HTML("<prompt>[Y/n]: </prompt>"), style=_PROMPT_STYLE).strip().lower()
        )
        approved = answer in ("", "y", "yes")

        logger.info("HITL resume: approved=%s", approved)
        console.print()  # spacing before resume output

        # Resume the graph with the user's decision
        resume_acc = _ChunkAccumulator()
        resume_start = time.monotonic()
        logger.debug("Resume stream started")

        for chunk, metadata in agent.stream(
            Command(resume=approved),
            cast(RunnableConfig, config),
            stream_mode="messages",
        ):
            if _verbose_print(chunk, metadata):
                continue
            resume_acc.accumulate(chunk)
        display_text = _strip_summary_echo(resume_acc.msg_buf)
        if display_text:
            console.print()
            console.print(Markdown(display_text))
        display_timing(time.monotonic() - resume_start)

        logger.debug("Resume stream ended (%.1fs)", time.monotonic() - resume_start)

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
    history = FileHistory(str(get_history_path()))
    session = PromptSession(history=history)

    # Display welcome message
    display_welcome()

    # Create agent
    try:
        agent = create_career_agent()
        config = get_agent_config(thread_id=thread_id)

        model_name = get_agent_model_name()
        if model_name:
            display_model_info(model_name)
    except Exception as e:
        display_error(f"Failed to initialize agent: {e}")
        return

    while True:
        try:
            # Get user input
            user_input = session.prompt(_PROMPT_MSG, style=_PROMPT_STYLE).strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                if handle_command(user_input):
                    break
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
                        logger.exception("Unrecoverable agent error")
                        display_error(f"Agent error: {e}")
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
                display_error(f"Unexpected error: {e}")
            else:
                # Bare Exception() with no message — typically from
                # nest_asyncio/prompt_toolkit event loop conflicts
                console.print("\n[#415a77]Press ENTER to continue...[/#415a77]")
            continue


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

    input_message = _make_input(question)
    acc = _ChunkAccumulator()

    stream_iter = agent.stream(
        cast(Any, input_message),
        cast(RunnableConfig, config),
        stream_mode="messages",
    )
    _stream_to_live(stream_iter, acc, console)

    return _strip_summary_echo(acc.full_response) or acc.full_response
