"""Chat client for FutureProof conversational interface.

Combines prompt-toolkit for input handling with Rich for output display.
Provides both sync and async chat loops for different use cases.
"""

from pathlib import Path
from typing import Any, cast

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
    full_response = ""
    shown_tools: set[str] = set()

    with Live(Markdown(""), console=console, refresh_per_second=10) as live:
        for chunk, metadata in agent.stream(
            input_message,
            cast(RunnableConfig, config),
            stream_mode="messages",
        ):
            # Show tool calls in verbose mode
            tool_calls = getattr(chunk, "tool_calls", None)
            if verbose and tool_calls:
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    if tool_name not in shown_tools:
                        shown_tools.add(tool_name)
                        live.stop()
                        console.print(f"[dim]🔧 Using tool: {tool_name}[/dim]")
                        live.start()

            # Only accumulate AI message content, not tool messages
            chunk_type = getattr(chunk, "type", None)
            if chunk_type == "tool":
                continue

            if hasattr(chunk, "content") and chunk.content:  # type: ignore[union-attr]
                content = chunk.content  # type: ignore[union-attr]
                # Handle Gemini's structured content format
                if isinstance(content, list):
                    content = "".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in content
                    )
                full_response += content
                live.update(Markdown(full_response))

    console.print()  # Blank line after response

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

            input_message = {"messages": [{"role": "user", "content": user_input}]}

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

            input_message = {"messages": [{"role": "user", "content": user_input}]}

            full_response = ""

            try:
                with Live(Markdown(""), console=console, refresh_per_second=10) as live:
                    async for chunk, metadata in agent.astream(
                        input_message,
                        cast(RunnableConfig, config),
                        stream_mode="messages",
                    ):
                        # chunk can be AIMessageChunk or str depending on stream mode
                        if hasattr(chunk, "content") and chunk.content:  # type: ignore[union-attr]
                            content = chunk.content  # type: ignore[union-attr]
                            # Handle Gemini's structured content format
                            if isinstance(content, list):
                                content = "".join(
                                    block.get("text", "") if isinstance(block, dict) else str(block)
                                    for block in content
                                )
                            full_response += content
                            live.update(Markdown(full_response))

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

    input_message = {"messages": [{"role": "user", "content": question}]}

    full_response = ""

    with Live(Markdown(""), console=console, refresh_per_second=10) as live:
        for chunk, metadata in agent.stream(
            input_message,
            cast(RunnableConfig, config),
            stream_mode="messages",
        ):
            # chunk can be AIMessageChunk or str depending on stream mode
            if hasattr(chunk, "content") and chunk.content:  # type: ignore[union-attr]
                content = chunk.content  # type: ignore[union-attr]
                # Handle Gemini's structured content format
                if isinstance(content, list):
                    content = "".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in content
                    )
                full_response += content
                live.update(Markdown(full_response))

    console.print()
    return full_response
