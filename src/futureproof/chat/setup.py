"""Interactive setup wizard for FutureProof configuration.

Handles sensitive settings (API keys, tokens) through direct terminal
input -- never through the LLM agent. Used for:
1. First-run setup when no LLM provider is configured
2. The /setup slash command for reconfiguration at any time
"""

import logging
from collections.abc import Sequence

from prompt_toolkit import PromptSession
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from futureproof.config import reload_settings, settings, write_user_setting

logger = logging.getLogger(__name__)

# ── Provider and integration definitions ────────────────────────────────

_PROVIDERS: dict[str, dict] = {
    "futureproof": {
        "name": "FutureProof Proxy",
        "description": "Zero-config, free starter tokens",
        "keys": [
            ("FUTUREPROOF_PROXY_KEY", "API key (from futureproof.dev/signup)", True),
        ],
    },
    "openai": {
        "name": "OpenAI",
        "description": "GPT-4.1, GPT-5 Mini, GPT-4o",
        "keys": [
            ("OPENAI_API_KEY", "API key (sk-...)", True),
        ],
    },
    "anthropic": {
        "name": "Anthropic",
        "description": "Claude Sonnet 4, Claude Haiku 4.5",
        "keys": [
            ("ANTHROPIC_API_KEY", "API key (sk-ant-...)", True),
        ],
    },
    "google": {
        "name": "Google Gemini",
        "description": "Gemini 2.5 Flash, Gemini 2.5 Pro",
        "keys": [
            ("GOOGLE_API_KEY", "API key", True),
        ],
    },
    "azure": {
        "name": "Azure OpenAI",
        "description": "GPT-4.1, GPT-5 Mini via Azure",
        "keys": [
            ("AZURE_OPENAI_API_KEY", "API key", True),
            ("AZURE_OPENAI_ENDPOINT", "Endpoint (https://...openai.azure.com/)", False),
            ("AZURE_CHAT_DEPLOYMENT", "Chat deployment name (e.g. gpt-4.1)", False),
        ],
    },
    "ollama": {
        "name": "Ollama (local)",
        "description": "Free, offline — requires Ollama installed",
        "keys": [
            ("OLLAMA_BASE_URL", "Base URL (default: http://localhost:11434)", False),
        ],
    },
}

_INTEGRATIONS: dict[str, dict] = {
    "github": {
        "name": "GitHub",
        "description": "Access repos, profile, code search",
        "keys": [
            ("GITHUB_PERSONAL_ACCESS_TOKEN", "Personal access token", True),
        ],
    },
    "tavily": {
        "name": "Tavily Search",
        "description": "Market research (free 1000 queries/month)",
        "keys": [
            ("TAVILY_API_KEY", "API key (from tavily.com)", True),
        ],
    },
}

# Ordered lists for menu display
_PROVIDER_ORDER = ["futureproof", "openai", "anthropic", "google", "azure", "ollama"]
_INTEGRATION_ORDER = ["github", "tavily"]


# ── Helpers ─────────────────────────────────────────────────────────────


def _redact(value: str) -> str:
    """Redact a secret value, showing only first 4 and last 4 chars."""
    if len(value) <= 10:
        return "*" * len(value)
    return value[:4] + "..." + value[-4:]


def _provider_status(provider_id: str) -> bool:
    """Check if a provider has its required keys configured."""
    checks = {
        "futureproof": settings.has_proxy,
        "openai": settings.has_openai,
        "anthropic": settings.has_anthropic,
        "google": settings.has_google,
        "azure": settings.has_azure,
        "ollama": settings.has_ollama,
    }
    return checks.get(provider_id, False)


def _integration_status(integration_id: str) -> bool:
    """Check if an integration has its required keys configured."""
    checks = {
        "github": settings.has_github_mcp,
        "tavily": settings.has_tavily_mcp,
    }
    return checks.get(integration_id, False)


# ── Display ─────────────────────────────────────────────────────────────


def display_config_status(console: Console) -> None:
    """Show current configuration status in a Rich panel."""
    lines: list[Text] = []

    # Active provider
    provider = settings.active_provider
    if provider:
        pname = _PROVIDERS.get(provider, {}).get("name", provider)
        lines.append(Text.assemble(
            ("Active provider: ", "#e0d8c0"),
            (pname, "bold #10b981"),
        ))
    else:
        lines.append(Text("No LLM provider configured", style="bold #ff6b6b"))
    lines.append(Text(""))

    # Providers
    lines.append(Text("LLM Providers", style="bold #ffd700"))
    for pid in _PROVIDER_ORDER:
        info = _PROVIDERS[pid]
        configured = _provider_status(pid)
        icon = "\u2714" if configured else "\u2718"
        color = "#10b981" if configured else "#ff6b6b"
        active = " (active)" if pid == provider else ""
        lines.append(Text.assemble(
            (f"  {icon} ", color),
            (info["name"], "#e0d8c0"),
            (f" — {info['description']}", "#415a77"),
            (active, "bold #ffd700"),
        ))

    lines.append(Text(""))

    # Integrations
    lines.append(Text("Integrations", style="bold #ffd700"))
    for iid in _INTEGRATION_ORDER:
        info = _INTEGRATIONS[iid]
        configured = _integration_status(iid)
        icon = "\u2714" if configured else "\u2718"
        color = "#10b981" if configured else "#ff6b6b"
        lines.append(Text.assemble(
            (f"  {icon} ", color),
            (info["name"], "#e0d8c0"),
            (f" — {info['description']}", "#415a77"),
        ))

    content = Text("\n").join(lines)
    console.print(Panel(
        content,
        title="[bold #ffd700]Configuration[/bold #ffd700]",
        border_style="#ffd700",
        box=box.ROUNDED,
        padding=(1, 2),
    ))
    console.print()


def _display_menu(console: Console) -> None:
    """Show the setup menu options."""
    console.print("[bold #ffd700]LLM Providers[/bold #ffd700]")
    for i, pid in enumerate(_PROVIDER_ORDER, 1):
        info = _PROVIDERS[pid]
        configured = _provider_status(pid)
        status = "[#10b981]\u2714[/#10b981]" if configured else "[#ff6b6b]\u2718[/#ff6b6b]"
        console.print(f"  {status} [{i}] {info['name']}")

    console.print()
    console.print("[bold #ffd700]Integrations[/bold #ffd700]")
    offset = len(_PROVIDER_ORDER)
    for i, iid in enumerate(_INTEGRATION_ORDER, offset + 1):
        info = _INTEGRATIONS[iid]
        configured = _integration_status(iid)
        status = "[#10b981]\u2714[/#10b981]" if configured else "[#ff6b6b]\u2718[/#ff6b6b]"
        console.print(f"  {status} [{i}] {info['name']}")

    console.print()
    console.print("  [#415a77][0] Done[/#415a77]")
    console.print()


# ── Core setup flow ─────────────────────────────────────────────────────


def _prompt_keys(
    session: PromptSession,  # type: ignore[type-arg]
    console: Console,
    name: str,
    keys: Sequence[tuple[str, str, bool]],
) -> bool:
    """Prompt the user for each key in a provider/integration.

    Args:
        session: prompt_toolkit session for input
        console: Rich console for output
        name: Display name (e.g. "OpenAI")
        keys: List of (ENV_VAR_NAME, label, is_secret) tuples

    Returns:
        True if any value was set.
    """
    console.print(f"\n[bold #5bc0be]Configure {name}[/bold #5bc0be]")
    console.print("[#415a77]Press Enter to skip a field.[/#415a77]\n")

    changed = False
    for env_key, label, is_secret in keys:
        try:
            value = session.prompt(
                f"  {label}: ",
                is_password=is_secret,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[#415a77]Cancelled.[/#415a77]")
            return changed

        if value:
            write_user_setting(env_key, value)
            display = _redact(value) if is_secret else value
            console.print(f"  [#10b981]\u2714 {env_key}[/#10b981] = {display}")
            changed = True

    return changed


def run_setup(
    console: Console,
    session: PromptSession,  # type: ignore[type-arg]
    first_run: bool = False,
) -> bool:
    """Run the interactive setup wizard.

    Args:
        console: Rich console for output
        session: prompt_toolkit session for input
        first_run: If True, requires at least one LLM provider

    Returns:
        True if any settings were changed (caller should restart agent).
    """
    if first_run:
        console.print(Panel(
            Text.assemble(
                ("Welcome to FutureProof!\n\n", "bold #ffd700"),
                ("An LLM provider is required to start. ", "#e0d8c0"),
                ("Let's set one up.\n", "#e0d8c0"),
                ("Your keys are stored locally at ", "#415a77"),
                ("~/.futureproof/.env", "bold #415a77"),
                (" and never sent to the agent.", "#415a77"),
            ),
            border_style="#ffd700",
            box=box.ROUNDED,
            padding=(1, 2),
        ))
        console.print()

    any_changed = False

    while True:
        display_config_status(console)
        _display_menu(console)

        try:
            choice = session.prompt("Select [0-8]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "0" or choice == "":
            # Exit setup — but enforce provider on first run
            if first_run and not settings.active_provider:
                console.print(
                    "[#ff6b6b]At least one LLM provider is required. "
                    "Please configure a provider to continue.[/#ff6b6b]\n"
                )
                continue
            break

        try:
            idx = int(choice)
        except ValueError:
            console.print("[#ff6b6b]Invalid choice.[/#ff6b6b]\n")
            continue

        # Map index to provider or integration
        offset = len(_PROVIDER_ORDER)
        if 1 <= idx <= offset:
            pid = _PROVIDER_ORDER[idx - 1]
            info = _PROVIDERS[pid]
            changed = _prompt_keys(session, console, info["name"], info["keys"])
        elif offset < idx <= offset + len(_INTEGRATION_ORDER):
            iid = _INTEGRATION_ORDER[idx - offset - 1]
            info = _INTEGRATIONS[iid]
            changed = _prompt_keys(session, console, info["name"], info["keys"])
        else:
            console.print("[#ff6b6b]Invalid choice.[/#ff6b6b]\n")
            continue

        if changed:
            any_changed = True
            reload_settings()
            console.print()

    if any_changed:
        reload_settings()
        provider = settings.active_provider
        if provider:
            pname = _PROVIDERS.get(provider, {}).get("name", provider)
            console.print(
                f"\n[#10b981]\u2714 Settings saved. Active provider: "
                f"[bold]{pname}[/bold][/#10b981]\n"
            )
        logger.info("Settings updated via /setup, active_provider=%s", provider)

    return any_changed
