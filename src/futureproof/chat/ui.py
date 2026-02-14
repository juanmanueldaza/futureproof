"""Rich-based terminal UI components for FutureProof chat.

Provides beautiful terminal output using the Rich library:
- Markdown rendering for agent responses
- Panels for structured information
- Live display for streaming responses
- Syntax highlighting for code blocks
- Styled verbose output for developer observability
"""

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

# Global console instance
console = Console()

# ── Tool category styling ────────────────────────────────────────────────

_TOOL_CATEGORIES: dict[str, tuple[str, str]] = {
    # category: (icon, color)
    "profile": ("\u2139", "bright_cyan"),  # ℹ
    "gathering": ("\u2b07", "bright_green"),  # ⬇
    "github": ("\u2b22", "bright_white"),  # ⬢
    "gitlab": ("\u2b22", "bright_magenta"),  # ⬢
    "knowledge": ("\u25c6", "bright_yellow"),  # ◆
    "analysis": ("\u25b2", "bright_blue"),  # ▲
    "generation": ("\u2605", "bright_red"),  # ★
    "market": ("\u25cf", "bright_green"),  # ●
    "memory": ("\u25a0", "bright_magenta"),  # ■
}

_TOOL_TO_CATEGORY: dict[str, str] = {
    # Profile
    "get_user_profile": "profile",
    "update_user_name": "profile",
    "update_current_role": "profile",
    "update_user_skills": "profile",
    "set_target_roles": "profile",
    "update_user_goal": "profile",
    # Gathering
    "gather_portfolio_data": "gathering",
    "gather_linkedin_data": "gathering",
    "gather_assessment_data": "gathering",
    "gather_all_career_data": "gathering",
    "get_stored_career_data": "gathering",
    # GitHub
    "search_github_repos": "github",
    "get_github_repo": "github",
    "get_github_profile": "github",
    # GitLab
    "search_gitlab_projects": "gitlab",
    "get_gitlab_project": "gitlab",
    "get_gitlab_file": "gitlab",
    # Knowledge
    "search_career_knowledge": "knowledge",
    "get_knowledge_stats": "knowledge",
    "index_career_knowledge": "knowledge",
    "clear_career_knowledge": "knowledge",
    # Analysis
    "analyze_skill_gaps": "analysis",
    "analyze_career_alignment": "analysis",
    "get_career_advice": "analysis",
    # Generation
    "generate_cv": "generation",
    "generate_cv_draft": "generation",
    # Market
    "search_jobs": "market",
    "get_tech_trends": "market",
    "get_salary_insights": "market",
    "gather_market_data": "market",
    "analyze_market_fit": "market",
    "analyze_market_skills": "market",
    # Memory
    "remember_decision": "memory",
    "remember_job_application": "memory",
    "recall_memories": "memory",
    "get_memory_stats": "memory",
}


def _tool_style(tool_name: str) -> tuple[str, str]:
    """Get icon and color for a tool name."""
    cat = _TOOL_TO_CATEGORY.get(tool_name, "")
    return _TOOL_CATEGORIES.get(cat, ("\u2022", "dim"))  # default: bullet, dim


def _badge(label: str, style: str) -> Text:
    """Create a styled badge like  MODEL  or  DONE ."""
    return Text(f" {label} ", style=f"bold reverse {style}")


def display_model_info(model_name: str) -> None:
    """Show which LLM model is active at session start."""
    console.print(
        Text.assemble(
            _badge("MODEL", "bright_blue"),
            (" ", ""),
            (model_name, "bold bright_blue"),
        )
    )
    console.print()


def display_tool_start(tool_name: str, args: dict) -> None:
    """Display a styled tool invocation with full arguments."""
    _icon, color = _tool_style(tool_name)
    cat = _TOOL_TO_CATEGORY.get(tool_name, "tool")

    # Header line: badge + tool name
    header = Text.assemble(
        _badge(cat.upper(), color),
        (" ", ""),
        (tool_name, f"bold {color}"),
    )
    console.print(header)

    # Show arguments on separate lines for readability
    if args:
        for k, v in args.items():
            val_str = str(v)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            console.print(Text(f"       {k}: {val_str}", style="dim"))


def display_tool_result(tool_name: str, content: str, elapsed: float | None = None) -> None:
    """Display tool result in a bordered panel with full content."""
    _icon, color = _tool_style(tool_name)

    # Build subtitle with timing
    subtitle = ""
    if elapsed is not None:
        subtitle = f"{elapsed:.1f}s"

    # Show full tool output in a panel — trim only truly massive outputs
    display_content = content
    max_len = 2000
    if len(display_content) > max_len:
        display_content = display_content[:max_len] + f"\n\n... ({len(content)} chars total)"

    console.print(
        Panel(
            Text(display_content, style="dim"),
            title=f"[{color}]{tool_name}[/{color}]",
            subtitle=f"[dim italic]{subtitle}[/dim italic]" if subtitle else None,
            border_style=color,
            box=box.SIMPLE_HEAVY,
            padding=(0, 1),
        )
    )


def display_node_transition(node_name: str) -> None:
    """Show when the agent graph transitions to a new node."""
    # Map internal node names to human-readable descriptions
    labels = {
        "model": "LLM thinking...",
        "tools": "executing tools",
    }
    label = labels.get(node_name, node_name)
    console.print(
        Text.assemble(
            ("  >> ", "dim"),
            (label, "dim italic"),
        )
    )


def display_timing(elapsed: float) -> None:
    """Show total response time."""
    console.print(
        Text.assemble(
            _badge("DONE", "green"),
            (f" {elapsed:.1f}s", "green"),
        )
    )
    console.print()


def display_model_switch(model_name: str) -> None:
    """Show when the fallback manager switches to a different model."""
    console.print(
        Text.assemble(
            _badge("FALLBACK", "yellow"),
            (" ", ""),
            (model_name, "bold yellow"),
        )
    )


def display_indexing_result(source: str, chunks: int, elapsed: float) -> None:
    """Show indexing progress for a knowledge source."""
    console.print(
        Text.assemble(
            _badge("INDEX", "bright_yellow"),
            (f" {source}", "bold bright_yellow"),
            (f" -- {chunks} chunks indexed", ""),
            (f" ({elapsed:.1f}s)", "dim italic"),
        )
    )


def display_gather_result(source: str, elapsed: float, success: bool = True) -> None:
    """Show gather timing for a data source."""
    if success:
        console.print(
            Text.assemble(
                _badge("GATHER", "bright_green"),
                (f" {source}", "bold bright_green"),
                (f" ({elapsed:.1f}s)", "dim italic"),
            )
        )
    else:
        console.print(
            Text.assemble(
                _badge("FAILED", "red"),
                (f" {source}", "bold red"),
                (f" ({elapsed:.1f}s)", "dim italic"),
            )
        )


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
