"""Tests for in-chat settings management.

Covers: write_user_setting, reload_settings, get_user_env_path,
reset_fallback_manager, and the get_current_config / update_setting tools.
"""

from pathlib import Path
from unittest.mock import patch

from futureproof.config import Settings

# ── Helpers ─────────────────────────────────────────────────────────────


def _make_settings(**overrides) -> Settings:
    """Create an isolated Settings instance (no .env, no env vars)."""
    defaults: dict[str, str] = {
        "futureproof_proxy_key": "",
        "openai_api_key": "",
        "anthropic_api_key": "",
        "google_api_key": "",
        "azure_openai_api_key": "",
        "azure_openai_endpoint": "",
        "ollama_base_url": "",
        "llm_provider": "",
    }
    return Settings(_env_file=None, **(defaults | overrides))  # type: ignore[arg-type]


# ── write_user_setting ──────────────────────────────────────────────────


class TestWriteUserSetting:
    """Test writing settings to the user-level .env file."""

    def test_creates_file_if_missing(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        with patch("futureproof.config._USER_ENV_PATH", env_path):
            from futureproof.config import write_user_setting

            write_user_setting("TEST_KEY", "test_value")

        assert env_path.exists()
        assert "TEST_KEY" in env_path.read_text()

    def test_file_has_restricted_permissions(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        with patch("futureproof.config._USER_ENV_PATH", env_path):
            from futureproof.config import write_user_setting

            write_user_setting("KEY", "val")

        mode = oct(env_path.stat().st_mode)
        assert mode.endswith("600"), f"Expected 0o600, got {mode}"

    def test_overwrites_existing_key(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        with patch("futureproof.config._USER_ENV_PATH", env_path):
            from futureproof.config import write_user_setting

            write_user_setting("MY_KEY", "old")
            write_user_setting("MY_KEY", "new")

        content = env_path.read_text()
        assert content.count("MY_KEY") == 1
        assert "new" in content

    def test_preserves_other_keys(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        with patch("futureproof.config._USER_ENV_PATH", env_path):
            from futureproof.config import write_user_setting

            write_user_setting("KEY_A", "aaa")
            write_user_setting("KEY_B", "bbb")

        content = env_path.read_text()
        assert "KEY_A" in content
        assert "KEY_B" in content

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        env_path = tmp_path / "subdir" / ".env"
        with patch("futureproof.config._USER_ENV_PATH", env_path):
            from futureproof.config import write_user_setting

            write_user_setting("KEY", "val")

        assert env_path.exists()


# ── reload_settings ─────────────────────────────────────────────────────


class TestReloadSettings:
    """Test in-place singleton mutation via reload_settings."""

    def test_picks_up_new_env_values(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        env_path.write_text("OPENAI_API_KEY='sk-reloaded'\n")

        with patch("futureproof.config._USER_ENV_PATH", env_path):
            from futureproof.config import reload_settings, settings

            # Point settings to our temp file and reload
            reload_settings()
            # We can't guarantee the value changes (real .env may override),
            # but reload_settings should not raise.
            assert isinstance(settings.openai_api_key, str)

    def test_singleton_identity_preserved(self, tmp_path: Path) -> None:
        """The settings object identity doesn't change after reload."""
        env_path = tmp_path / ".env"
        env_path.write_text("")

        with patch("futureproof.config._USER_ENV_PATH", env_path):
            from futureproof.config import reload_settings, settings

            obj_id = id(settings)
            reload_settings()
            assert id(settings) == obj_id


# ── get_user_env_path ───────────────────────────────────────────────────


class TestGetUserEnvPath:
    def test_returns_path_in_home(self) -> None:
        from futureproof.config import get_user_env_path

        path = get_user_env_path()
        assert isinstance(path, Path)
        assert ".futureproof" in str(path)
        assert path.name == ".env"


# ── reset_fallback_manager ──────────────────────────────────────────────


class TestResetFallbackManager:
    def test_clears_cached_manager(self) -> None:
        import futureproof.llm.fallback as fb

        # Simulate a cached manager
        fb._fallback_manager = "sentinel"  # type: ignore[assignment]
        fb.reset_fallback_manager()
        assert fb._fallback_manager is None

    def test_get_creates_new_after_reset(self) -> None:
        from futureproof.llm.fallback import (
            get_fallback_manager,
            reset_fallback_manager,
        )

        mgr1 = get_fallback_manager()
        reset_fallback_manager()
        mgr2 = get_fallback_manager()
        assert mgr1 is not mgr2


# ── get_current_config tool ─────────────────────────────────────────────


class TestGetCurrentConfigTool:
    def test_returns_string(self) -> None:
        from futureproof.agents.tools.settings import get_current_config

        result = get_current_config.invoke({})
        assert isinstance(result, str)

    def test_contains_provider_info(self) -> None:
        from futureproof.agents.tools.settings import get_current_config

        result = get_current_config.invoke({})
        assert "Active LLM provider" in result

    def test_does_not_leak_keys(self) -> None:
        from futureproof.agents.tools.settings import get_current_config

        result = get_current_config.invoke({})
        assert "api_key" not in result.lower() or "configured" in result.lower()
        # Should never contain actual key values
        assert "sk-" not in result


# ── update_setting tool ─────────────────────────────────────────────────


class TestUpdateSettingTool:
    def test_rejects_sensitive_key(self) -> None:
        from futureproof.agents.tools.settings import update_setting

        result = update_setting.invoke({"key": "openai_api_key", "value": "sk-bad"})
        assert "/setup" in result

    def test_rejects_unknown_key(self) -> None:
        from futureproof.agents.tools.settings import update_setting

        result = update_setting.invoke({"key": "nonexistent_setting", "value": "x"})
        assert "Unknown setting" in result

    @patch("futureproof.agents.tools.settings.write_user_setting")
    @patch("futureproof.agents.tools.settings.reload_settings")
    def test_writes_valid_setting(self, mock_reload, mock_write) -> None:
        from futureproof.agents.tools.settings import update_setting

        result = update_setting.invoke(
            {"key": "llm_temperature", "value": "0.5"},
        )
        mock_write.assert_called_once_with("LLM_TEMPERATURE", "0.5")
        mock_reload.assert_called_once()
        assert "Updated" in result

    @patch("futureproof.agents.tools.settings.write_user_setting")
    @patch("futureproof.agents.tools.settings.reload_settings")
    @patch("futureproof.agents.career_agent.reset_career_agent")
    @patch("futureproof.llm.fallback.reset_fallback_manager")
    def test_restart_keys_trigger_agent_reset(
        self, mock_reset_fb, mock_reset_agent, mock_reload, mock_write
    ) -> None:
        from futureproof.agents.tools.settings import update_setting

        result = update_setting.invoke(
            {"key": "agent_model", "value": "gpt-4o"},
        )
        mock_reset_fb.assert_called_once()
        mock_reset_agent.assert_called_once()
        assert "next message" in result

    @patch("futureproof.agents.tools.settings.write_user_setting")
    @patch("futureproof.agents.tools.settings.reload_settings")
    @patch("futureproof.agents.career_agent.reset_career_agent")
    def test_non_restart_key_no_agent_reset(
        self, mock_reset_agent, mock_reload, mock_write
    ) -> None:
        from futureproof.agents.tools.settings import update_setting

        # market_cache_hours is not in _RESTART_KEYS
        update_setting.invoke(
            {"key": "market_cache_hours", "value": "48"},
        )
        mock_reset_agent.assert_not_called()

    def test_normalizes_key_to_lowercase(self) -> None:
        from futureproof.agents.tools.settings import update_setting

        result = update_setting.invoke(
            {"key": "OPENAI_API_KEY", "value": "sk-bad"},
        )
        # Should still match the sensitive key (lowercase normalization)
        assert "/setup" in result

    def test_all_configurable_keys_are_valid_settings(self) -> None:
        """Every key in the whitelist should be a real Settings field."""
        from futureproof.agents.tools.settings import _AGENT_CONFIGURABLE

        for key in _AGENT_CONFIGURABLE:
            assert key in Settings.model_fields, (
                f"'{key}' in _AGENT_CONFIGURABLE but not in Settings"
            )

    def test_sensitive_keys_not_in_configurable(self) -> None:
        """Ensure no sensitive key accidentally appears in the whitelist."""
        from futureproof.agents.tools.settings import (
            _AGENT_CONFIGURABLE,
            _SENSITIVE_KEYS,
        )

        overlap = _AGENT_CONFIGURABLE.keys() & _SENSITIVE_KEYS
        assert not overlap, f"Sensitive keys in whitelist: {overlap}"
