from __future__ import annotations

from fu7ur3pr00f import diagnostics


def _set_async_results(monkeypatch, results: dict[str, object]) -> None:
    def fake_run(coro):
        coro.close()
        return results

    monkeypatch.setattr(diagnostics.asyncio, "run", fake_run)


def test_diagnostics_ignores_missing_gitlab_for_core_install(monkeypatch) -> None:
    monkeypatch.setattr(diagnostics, "get_all_tools", lambda: [])
    _set_async_results(monkeypatch, {"mcp": {}, "gitlab": False, "llm": True})

    assert diagnostics.main() == 0


def test_diagnostics_still_fails_when_required_checks_fail(monkeypatch) -> None:
    monkeypatch.setattr(diagnostics, "get_all_tools", lambda: [])
    _set_async_results(
        monkeypatch,
        {"mcp": {"github": False, "jobspy": True}, "gitlab": False, "llm": False},
    )

    assert diagnostics.main() == 1
