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

from futureproof.config import reload_settings, settings, write_user_setting

logger = logging.getLogger(__name__)

# ── Provider and integration definitions ────────────────────────────────

_PROVIDERS: dict[str, dict] = {
    "futureproof": {
        "name": "FutureProof Proxy",
        "description": "Zero-config, free starter tokens (not available yet)",
        "keys": [
            ("FUTUREPROOF_PROXY_KEY", "API key (from futureproof.dev/signup)", True),
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
        "description": "Gemini 2.5 Flash, Gemini 2.5 Pro (coming soon)",
        "keys": [
            ("GOOGLE_API_KEY", "API key", True),
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
_PROVIDER_ORDER = ["azure", "futureproof", "openai", "anthropic", "google", "ollama"]
_INTEGRATION_ORDER = ["github", "tavily"]

# Providers not yet available for selection
_LOCKED_PROVIDERS = {"futureproof", "openai", "anthropic", "google", "ollama"}


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
        locked = pid in _LOCKED_PROVIDERS
        if locked:
            lines.append(Text.assemble(
                ("  \u2014 ", "#555555"),
                (info["name"], "#555555"),
                (f" — {info['description']}", "#555555"),
            ))
            continue
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
        if pid in _LOCKED_PROVIDERS:
            console.print(
                f"  [#555555]\u2014 [{i}] "
                f"{info['name']}[/#555555]"
            )
            continue
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
    model_list = "\n".join(f"     [bold #5bc0be]{m}[/bold #5bc0be]" for m in _AZURE_MODELS)
    console.print(Panel(
        (
            "[bold #ffd700]Step 1[/bold #ffd700]"
            " [#e0d8c0]Create a free Azure account[/#e0d8c0]\n"
            "  [#5bc0be]https://azure.microsoft.com/free[/#5bc0be]\n"
            "  [#415a77]New accounts get $200 free credit"
            " for 30 days.[/#415a77]\n"
            "\n"
            "[bold #ffd700]Step 2[/bold #ffd700]"
            " [#e0d8c0]Go to Azure AI Foundry[/#e0d8c0]\n"
            "  [#5bc0be]https://ai.azure.com[/#5bc0be]\n"
            "  [#415a77]Create a new project (this creates"
            " an OpenAI resource).[/#415a77]\n"
            "\n"
            "[bold #ffd700]Step 3[/bold #ffd700]"
            " [#e0d8c0]Deploy these models[/#e0d8c0]\n"
            "  [#415a77]Go to Models + endpoints > Deploy"
            " model.[/#415a77]\n"
            "  [#415a77]Deploy each of these (use the exact"
            " name as deployment name):[/#415a77]\n"
            f"{model_list}\n"
            "\n"
            "[bold #ffd700]Step 4[/bold #ffd700]"
            " [#e0d8c0]Get your credentials[/#e0d8c0]\n"
            "  [#415a77]Go to your project > Overview.[/#415a77]\n"
            "  [#415a77]Copy the [bold]API key[/bold]"
            " and [bold]Endpoint URL[/bold].[/#415a77]\n"
            "  [#ff6b6b]Use only the base URL"
            " (e.g. https://myresource.openai.azure.com).\n"
            "  Remove /api/projects/... if present."
            "[/#ff6b6b]"
        ),
        title="[bold #ffd700]Azure OpenAI Setup Guide[/bold #ffd700]",
        border_style="#ffd700",
        box=box.ROUNDED,
        padding=(1, 2),
    ))
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
    console.print("[#415a77]Press Enter to skip a field.[/#415a77]\n")

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
                console.print("\n[#415a77]Cancelled.[/#415a77]")
                return changed

            if not value and default:
                value = default
            if value and needs_url and not value.startswith(("https://", "http://")):
                console.print(
                    "  [#ff6b6b]Must be a URL starting with"
                    " https:// — please try again.[/#ff6b6b]"
                )
                continue
            break

        if value:
            write_user_setting(env_key, value)
            display = _redact(value) if is_secret else value
            console.print(f"  [#10b981]\u2714 {env_key}[/#10b981] = {display}")
            changed = True

    return changed


def run_setup(
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
            choice = input("Select [0-8]: ").strip()
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
