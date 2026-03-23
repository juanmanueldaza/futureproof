"""Diagnostics for fresh install connectivity checks."""

from __future__ import annotations

import asyncio
import contextlib
import shutil
import subprocess
from typing import Any

import httpx

from .agents.tools import get_all_tools
from .config import settings
from .mcp.factory import MCPClientFactory


def _print_result(name: str, ok: bool, detail: str = "") -> None:
    status = "OK" if ok else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" - {detail}"
    print(line)


def _check_llm() -> bool:
    providers = ["fu7ur3pr00f", "openai", "anthropic", "google", "azure", "ollama"]
    configured = [p for p in providers if settings.is_provider_configured(p)]
    active = settings.active_provider or "none"
    _print_result("LLM provider active", bool(settings.active_provider), active)
    _print_result("LLM providers configured", bool(configured), ", ".join(configured) or "none")
    return bool(settings.active_provider)


def _check_gitlab() -> bool:
    glab_path = shutil.which("glab")
    if not glab_path:
        _print_result("GitLab (glab)", False, "glab not installed")
        return False
    try:
        result = subprocess.run(
            [glab_path, "auth", "status"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        _print_result("GitLab (glab)", False, "auth status timed out")
        return False
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "auth status failed").strip()
        _print_result("GitLab (glab)", False, detail)
        return False
    _print_result("GitLab (glab)", True, "authenticated")
    return True


async def _check_mcp_server(server_type: str) -> bool:
    if not MCPClientFactory.is_available(server_type):
        _print_result(f"MCP:{server_type}", False, "missing config")
        return False

    if server_type == "jobspy":
        try:
            import jobspy  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            _print_result("MCP:jobspy", False, "python-jobspy not installed")
            return False

    client = MCPClientFactory.create(server_type)
    try:
        await asyncio.wait_for(client.connect(), timeout=20)
        tools = await asyncio.wait_for(client.list_tools(), timeout=20)
        _print_result(f"MCP:{server_type}", True, f"{len(tools)} tools")
        return True
    except Exception as exc:  # pragma: no cover - diagnostics surface raw failure
        if server_type == "github":
            ok, detail = _check_github_rest()
            if ok:
                _print_result("MCP:github", True, detail)
                return True
            _print_result("MCP:github", False, detail or str(exc))
            return False
        _print_result(f"MCP:{server_type}", False, str(exc))
        return False
    finally:
        with contextlib.suppress(Exception):
            await client.disconnect()


def _check_github_rest() -> tuple[bool, str]:
    token = settings.github_mcp_token_resolved
    if not token:
        return False, "token missing"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        response = httpx.get("https://api.github.com/user", headers=headers, timeout=20)
        if response.status_code >= 400:
            return False, f"REST {response.status_code}"
        return True, "rest fallback"
    except Exception as exc:
        return False, f"REST error: {exc}"


async def _run_async_checks() -> dict[str, Any]:
    results: dict[str, Any] = {"mcp": {}, "gitlab": False, "llm": False}
    results["llm"] = _check_llm()
    results["gitlab"] = _check_gitlab()

    for server_type in MCPClientFactory.AVAILABILITY_CHECKERS.keys():
        ok = await _check_mcp_server(server_type)
        results["mcp"][server_type] = ok
    return results


def main() -> int:
    tools = get_all_tools()
    _print_result("Tool registry", True, f"{len(tools)} tools loaded")

    results = asyncio.run(_run_async_checks())

    failures = 0
    if not results["llm"]:
        failures += 1
    # GitLab CLI integration is optional for the core install.
    failures += sum(1 for ok in results["mcp"].values() if not ok)

    if failures:
        print(f"\nFailures: {failures}")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
