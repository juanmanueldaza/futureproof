"""Rich-based terminal UI components for FutureProof chat.

Provides beautiful terminal output using the Rich library:
- Markdown rendering for agent responses
- Panels for structured information
- Live display for streaming responses
- Syntax highlighting for code blocks
"""

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

# Global console instance
console = Console()


def display_welcome() -> None:
    """Display welcome message when starting a chat session."""
    welcome_text = """
# FutureProof

Your AI career intelligence assistant. I can help you:

- **Analyze** your skills and identify gaps
- **Search** for relevant job opportunities
- **Generate** tailored CVs and cover letters
- **Advise** on career strategy and decisions

Type your message below, or use these commands:
- `/help` - Show available commands
- `/profile` - View/edit your profile
- `/quit` or `/q` - Exit chat
"""

    console.print(
        Panel(
            Markdown(welcome_text),
            title="[bold cyan]Welcome[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )
    console.print()


def display_response(content: str, streaming: bool = False) -> None:
    """Display an agent response with markdown formatting.

    Args:
        content: The response content (supports markdown)
        streaming: If True, content is being streamed (no panel wrapper)
    """
    if streaming:
        # During streaming, just print raw content (caller handles live display)
        console.print(content, end="")
    else:
        # Complete response - render as markdown
        console.print(Markdown(content))
        console.print()


def display_insights(insights: list[str]) -> None:
    """Display queued insights from background jobs.

    Args:
        insights: List of insight messages to display
    """
    if not insights:
        return

    insight_text = "\n".join(f"• {insight}" for insight in insights)

    console.print(
        Panel(
            insight_text,
            title="[bold yellow]Since you've been away[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )
    console.print()


def display_error(message: str) -> None:
    """Display an error message.

    Args:
        message: The error message to display
    """
    console.print(
        Panel(
            Text(message, style="red"),
            title="[bold red]Error[/bold red]",
            border_style="red",
            box=box.ROUNDED,
        )
    )
    console.print()


def display_tool_call(tool_name: str, status: str = "running") -> None:
    """Display a tool call notification.

    Args:
        tool_name: Name of the tool being called
        status: Status of the tool call (running, complete, error)
    """
    icons = {
        "running": "⏳",
        "complete": "✓",
        "error": "✗",
    }
    colors = {
        "running": "yellow",
        "complete": "green",
        "error": "red",
    }

    icon = icons.get(status, "•")
    color = colors.get(status, "white")

    console.print(f"[{color}]{icon} {tool_name}[/{color}]", end="\r")


def display_help() -> None:
    """Display help message with available commands."""
    help_text = """
## Commands

| Command | Description |
|---------|-------------|
| `/help` or `/h` | Show this help message |
| `/profile` | View your career profile |
| `/goals` | View your career goals |
| `/clear` | Clear conversation history |
| `/quit` or `/q` | Exit chat |

## Tips

- Just type naturally - I understand conversational requests
- Ask me to remember things like "remember I prefer remote work"
- Request specific actions like "analyze my skill gaps for ML Engineer"
- I maintain context across your conversation
"""

    console.print(
        Panel(
            Markdown(help_text),
            title="[bold cyan]Help[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )
    console.print()


def display_profile_summary() -> None:
    """Display the user's profile summary."""
    from futureproof.memory.profile import load_profile

    profile = load_profile()

    if not profile.name:
        console.print(
            Panel(
                "No profile configured yet. Tell me about yourself to get started!",
                title="[bold cyan]Your Profile[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )
        return

    profile_parts = []

    if profile.name:
        profile_parts.append(f"**Name:** {profile.name}")
    if profile.current_role:
        profile_parts.append(f"**Current Role:** {profile.current_role}")
    if profile.years_experience:
        profile_parts.append(f"**Experience:** {profile.years_experience} years")
    if profile.technical_skills:
        profile_parts.append(f"**Technical Skills:** {', '.join(profile.technical_skills[:10])}")
    if profile.target_roles:
        profile_parts.append(f"**Target Roles:** {', '.join(profile.target_roles)}")
    if profile.preferred_work_style:
        profile_parts.append(f"**Work Style:** {profile.preferred_work_style}")
    if profile.deal_breakers:
        profile_parts.append(f"**Deal Breakers:** {', '.join(profile.deal_breakers)}")

    console.print(
        Panel(
            Markdown("\n".join(profile_parts)),
            title="[bold cyan]Your Profile[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )
    console.print()


def display_goals() -> None:
    """Display the user's career goals."""
    from futureproof.memory.profile import load_profile

    profile = load_profile()

    if not profile.goals:
        console.print(
            Panel(
                "No goals set yet. Tell me about your career aspirations!",
                title="[bold cyan]Your Goals[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )
        return

    goal_parts = []
    for i, goal in enumerate(profile.goals, 1):
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(goal.priority, "⚪")
        status_text = f" ({goal.status})" if goal.status != "active" else ""
        goal_parts.append(f"{i}. {priority_icon} {goal.description}{status_text}")

    console.print(
        Panel(
            "\n".join(goal_parts),
            title="[bold cyan]Your Goals[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )
    console.print()
