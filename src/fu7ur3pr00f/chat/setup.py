"""Interactive setup wizard for FutureProof configuration.

Handles sensitive settings (API keys, tokens) through direct terminal
input -- never through the LLM agent. Used for:
1. First-run setup when no LLM provider is configured
2. The /setup slash command for reconfiguration at any time
"""

import getpass
import logging
from collections.abc import Callable, Sequence

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from fu7ur3pr00f.config import reload_settings, settings, write_user_setting
from fu7ur3pr00f.constants import (
    COLOR_ACCENT,
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_SUCCESS,
    COLOR_WARNING,
)

logger = logging.getLogger(__name__)

# ── Provider and integration definitions ────────────────────────────────

_PROVIDERS: dict[str, dict] = {
    "fu7ur3pr00f": {
        "name": "FutureProof Proxy",
        "description": "Zero-config, free starter tokens (not available yet)",
        "keys": [
            ("FUTUREPROOF_PROXY_KEY", "API key (from fu7ur3pr00f.dev/signup)", True),
        ],
    },
    "openai": {
        "name": "OpenAI",
        "description": "GPT-4.1, GPT-5 Mini, GPT-4o (coming soon)",
        "keys": [
            ("OPENAI_API_KEY", "API key (sk-...)", True),
        ],
    },
    "anthropic": {
        "name": "Anthropic",
        "description": "Claude Sonnet 4, Claude Haiku 4.5 (coming soon)",
        "keys": [
            ("ANTHROPIC_API_KEY", "API key (sk-ant-...)", True),
        ],
    },
    "google": {
        "name": "Google Gemini",
        "description": "Gemini 2.5 Flash, Gemini 2.5 Pro",
        "keys": [
            ("GOOGLE_API_KEY", "API key (from aistudio.google.com)", True),
        ],
    },
    "azure": {
        "name": "Azure OpenAI",
        "description": "GPT-4.1, GPT-5 Mini via Azure ($200 free trial)",
        "keys": [
            ("AZURE_OPENAI_API_KEY", "API key", True),
            ("AZURE_OPENAI_ENDPOINT", "Endpoint URL", False),
        ],
        "guide": "azure",
    },
    "ollama": {
        "name": "Ollama (local)",
        "description": "Free, offline (coming soon)",
        "keys": [
            ("OLLAMA_BASE_URL", "Base URL", False, "http://localhost:11434"),
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
_PROVIDER_ORDER = ["azure", "fu7ur3pr00f", "openai", "anthropic", "google", "ollama"]
_INTEGRATION_ORDER = ["github", "tavily"]

# Providers not yet available for selection
_LOCKED_PROVIDERS = {"fu7ur3pr00f", "openai", "anthropic", "ollama"}


# ── Helpers ─────────────────────────────────────────────────────────────


def _redact(value: str) -> str:
    """Redact a secret value, showing only first 4 and last 4 chars."""
    if len(value) <= 10:
        return "*" * len(value)
    return value[:4] + "..." + value[-4:]


def _provider_status(provider_id: str) -> bool:
    """Check if a provider has its required keys configured."""
    return settings.is_provider_configured(provider_id)


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
        lines.append(
            Text.assemble(
                ("Active provider: ", f"{COLOR_ACCENT}"),
                (pname, f"bold {COLOR_SUCCESS}"),
            )
        )
    else:
        lines.append(Text("No LLM provider configured", style=f"bold {COLOR_ERROR}"))
    lines.append(Text(""))

    # Providers
    lines.append(Text("LLM Providers", style=f"bold {COLOR_WARNING}"))
    for pid in _PROVIDER_ORDER:
        info = _PROVIDERS[pid]
        locked = pid in _LOCKED_PROVIDERS
        if locked:
            lines.append(
                Text.assemble(
                    ("  \u2014 ", "#555555"),
                    (info["name"], "#555555"),
                    (f" — {info['description']}", "#555555"),
                )
            )
            continue
        configured = _provider_status(pid)
        icon = "\u2714" if configured else "\u2718"
        color = f"{COLOR_SUCCESS}" if configured else f"{COLOR_ERROR}"
        active = " (active)" if pid == provider else ""
        lines.append(
            Text.assemble(
                (f"  {icon} ", color),
                (info["name"], f"{COLOR_ACCENT}"),
                (f" — {info['description']}", f"{COLOR_INFO}"),
                (active, f"bold {COLOR_WARNING}"),
            )
        )

    lines.append(Text(""))

    # Integrations
    lines.append(Text("Integrations", style=f"bold {COLOR_WARNING}"))
    for iid in _INTEGRATION_ORDER:
        info = _INTEGRATIONS[iid]
        configured = _integration_status(iid)
        icon = "\u2714" if configured else "\u2718"
        color = f"{COLOR_SUCCESS}" if configured else f"{COLOR_ERROR}"
        lines.append(
            Text.assemble(
                (f"  {icon} ", color),
                (info["name"], f"{COLOR_ACCENT}"),
                (f" — {info['description']}", f"{COLOR_INFO}"),
            )
        )

    content = Text("\n").join(lines)
    console.print(
        Panel(
            content,
            title=f"[bold {COLOR_WARNING}]Configuration[/bold {COLOR_WARNING}]",
            border_style=f"{COLOR_WARNING}",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print()


def _display_menu(console: Console) -> None:
    """Show the setup menu options."""
    console.print(f"[bold {COLOR_WARNING}]LLM Providers[/bold {COLOR_WARNING}]")
    for i, pid in enumerate(_PROVIDER_ORDER, 1):
        info = _PROVIDERS[pid]
        if pid in _LOCKED_PROVIDERS:
            console.print(f"  [#555555]\u2014 [{i}] " f"{info['name']}[/#555555]")
            continue
        configured = _provider_status(pid)
        status = (
            f"[{COLOR_SUCCESS}]\u2714[/{COLOR_SUCCESS}]"
            if configured
            else f"[{COLOR_ERROR}]\u2718[/{COLOR_ERROR}]"
        )
        console.print(f"  {status} [{i}] {info['name']}")

    console.print()
    console.print(f"[bold {COLOR_WARNING}]Integrations[/bold {COLOR_WARNING}]")
    offset = len(_PROVIDER_ORDER)
    for i, iid in enumerate(_INTEGRATION_ORDER, offset + 1):
        info = _INTEGRATIONS[iid]
        configured = _integration_status(iid)
        status = (
            f"[{COLOR_SUCCESS}]\u2714[/{COLOR_SUCCESS}]"
            if configured
            else f"[{COLOR_ERROR}]\u2718[/{COLOR_ERROR}]"
        )
        console.print(f"  {status} [{i}] {info['name']}")

    console.print()
    console.print(f"  [{COLOR_INFO}][0] Done[/{COLOR_INFO}]")
    console.print()


# ── Provider guides ────────────────────────────────────────────────────

_AZURE_MODELS = [
    "gpt-5-mini",
    "gpt-4.1",
    "gpt-4o-mini",
    "o4-mini",
    "text-embedding-3-small",
]


def _show_azure_guide(console: Console) -> None:
    """Show step-by-step Azure OpenAI setup instructions."""
    model_list = "\n".join(
        f"     [bold #5bc0be]{m}[/bold #5bc0be]" for m in _AZURE_MODELS
    )
    console.print(
        Panel(
            (
                f"[bold {COLOR_WARNING}]Step 1[/bold {COLOR_WARNING}]"
                f" [{COLOR_ACCENT}]Create a free Azure account[/{COLOR_ACCENT}]\n"
                "  [#5bc0be]https://azure.microsoft.com/free[/#5bc0be]\n"
                f"  [{COLOR_INFO}]New accounts get $200 free credit"
                f" for 30 days.[/{COLOR_INFO}]\n"
                "\n"
                f"[bold {COLOR_WARNING}]Step 2[/bold {COLOR_WARNING}]"
                f" [{COLOR_ACCENT}]Go to Azure AI Foundry[/{COLOR_ACCENT}]\n"
                "  [#5bc0be]https://ai.azure.com[/#5bc0be]\n"
                f"  [{COLOR_INFO}]Create a new project (this creates"
                f" an OpenAI resource).[/{COLOR_INFO}]\n"
                "\n"
                f"[bold {COLOR_WARNING}]Step 3[/bold {COLOR_WARNING}]"
                f" [{COLOR_ACCENT}]Deploy these models[/{COLOR_ACCENT}]\n"
                f"  [{COLOR_INFO}]Go to Models + endpoints > Deploy"
                f" model.[/{COLOR_INFO}]\n"
                f"  [{COLOR_INFO}]Deploy each of these (use the exact"
                f" name as deployment name):[/{COLOR_INFO}]\n"
                f"{model_list}\n"
                "\n"
                f"[bold {COLOR_WARNING}]Step 4[/bold {COLOR_WARNING}]"
                f" [{COLOR_ACCENT}]Get your credentials[/{COLOR_ACCENT}]\n"
                f"  [{COLOR_INFO}]Go to your project > Overview.[/{COLOR_INFO}]\n"
                f"  [{COLOR_INFO}]Copy the [bold]API key[/bold]"
                f" and [bold]Endpoint URL[/bold].[/{COLOR_INFO}]\n"
                f"  [{COLOR_ERROR}]Use only the base URL"
                " (e.g. https://myresource.openai.azure.com).\n"
                "  Remove /api/projects/... if present."
                f"[/{COLOR_ERROR}]"
            ),
            title=f"[bold {COLOR_WARNING}]Azure OpenAI Setup Guide[/bold {COLOR_WARNING}]",
            border_style=f"{COLOR_WARNING}",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print()


_GUIDES: dict[str, Callable[[Console], None]] = {
    "azure": _show_azure_guide,
}


# ── Core setup flow ─────────────────────────────────────────────────────


def _prompt_keys(
    console: Console,
    name: str,
    keys: Sequence[tuple[str, str, bool] | tuple[str, str, bool, str]],
) -> bool:
    """Prompt the user for each key in a provider/integration.

    Args:
        console: Rich console for output
        name: Display name (e.g. "OpenAI")
        keys: List of (ENV_VAR_NAME, label, is_secret[, default]) tuples

    Returns:
        True if any value was set.
    """
    console.print(f"\n[bold #5bc0be]Configure {name}[/bold #5bc0be]")
    console.print(f"[{COLOR_INFO}]Press Enter to skip a field.[/{COLOR_INFO}]\n")

    changed = False
    is_url_key = frozenset(("ENDPOINT", "URL"))
    for key_entry in keys:
        env_key, label, is_secret = key_entry[0], key_entry[1], key_entry[2]
        default = key_entry[3] if len(key_entry) > 3 else ""
        prompt_label = f"  {label} [{default}]: " if default else f"  {label}: "
        needs_url = not is_secret and any(k in env_key for k in is_url_key)
        while True:
            try:
                if is_secret:
                    value = getpass.getpass(prompt_label).strip()
                else:
                    value = input(prompt_label).strip()
            except (EOFError, KeyboardInterrupt):
                console.print(f"\n[{COLOR_INFO}]Cancelled.[/{COLOR_INFO}]")
                return changed

            if not value and default:
                value = default
            if value and needs_url and not value.startswith(("https://", "http://")):
                console.print(
                    f"  [{COLOR_ERROR}]Must be a URL starting with"
                    f" https:// — please try again.[/{COLOR_ERROR}]"
                )
                continue
            break

        if value:
            write_user_setting(env_key, value)
            display = _redact(value) if is_secret else value
            console.print(
                f"  [{COLOR_SUCCESS}]\u2714 {env_key}[/{COLOR_SUCCESS}] = {display}"
            )
            changed = True

    return changed


def run_setup(  # noqa: C901 - Menu-driven wizard with multiple provider/integration options
    console: Console,
    first_run: bool = False,
) -> bool:
    """Run the interactive setup wizard.

    Args:
        console: Rich console for output
        first_run: If True, requires at least one LLM provider

    Returns:
        True if any settings were changed (caller should restart agent).
    """
    if first_run:
        console.print(
            Panel(
                Text.assemble(
                    ("Welcome to FutureProof!\n\n", f"bold {COLOR_WARNING}"),
                    ("An LLM provider is required to start. ", f"{COLOR_ACCENT}"),
                    ("Let's set one up.\n", f"{COLOR_ACCENT}"),
                    ("Your keys are stored locally at ", f"{COLOR_INFO}"),
                    ("~/.fu7ur3pr00f/.env", f"bold {COLOR_INFO}"),
                    (" and never sent to the agent.", f"{COLOR_INFO}"),
                ),
                border_style=f"{COLOR_WARNING}",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        console.print()

    any_changed = False

    while True:
        display_config_status(console)
        _display_menu(console)

        try:
            choice = input("Select [0-8]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "0" or choice == "":
            # Exit setup — but enforce provider on first run
            if first_run and not settings.active_provider:
                console.print(
                    f"[{COLOR_ERROR}]At least one LLM provider is required. "
                    f"Please configure a provider to continue.[/{COLOR_ERROR}]\n"
                )
                continue
            break

        try:
            idx = int(choice)
        except ValueError:
            console.print(f"[{COLOR_ERROR}]Invalid choice.[/{COLOR_ERROR}]\n")
            continue

        # Map index to provider or integration
        offset = len(_PROVIDER_ORDER)
        if 1 <= idx <= offset:
            pid = _PROVIDER_ORDER[idx - 1]
            if pid in _LOCKED_PROVIDERS:
                console.print(
                    "[#555555]This provider is not available"
                    " yet. Please use Azure OpenAI.[/#555555]\n"
                )
                continue
            info = _PROVIDERS[pid]
            guide_id = info.get("guide")
            if guide_id and guide_id in _GUIDES:
                _GUIDES[guide_id](console)
            changed = _prompt_keys(console, info["name"], info["keys"])
        elif offset < idx <= offset + len(_INTEGRATION_ORDER):
            iid = _INTEGRATION_ORDER[idx - offset - 1]
            info = _INTEGRATIONS[iid]
            changed = _prompt_keys(console, info["name"], info["keys"])
        else:
            console.print(f"[{COLOR_ERROR}]Invalid choice.[/{COLOR_ERROR}]\n")
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
                f"\n[{COLOR_SUCCESS}]\u2714 Settings saved. Active provider: "
                f"[bold]{pname}[/bold][/{COLOR_SUCCESS}]\n"
            )
        logger.info("Settings updated via /setup, active_provider=%s", provider)

    return any_changed
