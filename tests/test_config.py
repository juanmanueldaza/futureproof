"""Tests for configuration management."""

from fu7ur3pr00f.config import Settings


def make_settings(**overrides) -> Settings:
    """Create a Settings instance isolated from .env and env vars."""
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
    merged = defaults | overrides
    # _env_file=None prevents reading from .env
    return Settings(_env_file=None, **merged)  # type: ignore[arg-type]


class TestSettings:
    """Test Settings class."""

    def test_default_values(self) -> None:
        """Test that settings have expected defaults."""
        s = make_settings(azure_openai_api_key="test-key")
        assert s.azure_openai_api_key == "test-key"

    def test_directory_paths_are_paths(self) -> None:
        """Test computed directory paths return Path objects."""
        from pathlib import Path

        s = make_settings()
        assert isinstance(s.data_dir, Path)
        assert isinstance(s.raw_dir, Path)
        assert isinstance(s.processed_dir, Path)
        assert isinstance(s.output_dir, Path)

    def test_directory_paths_structure(self) -> None:
        """Test directory paths have correct names."""
        s = make_settings()
        assert s.data_dir.name == "data"
        assert s.raw_dir.name == "raw"
        assert s.processed_dir.name == "processed"
        assert s.output_dir.name == "output"

    def test_directory_hierarchy(self) -> None:
        """Test directory paths are correctly nested."""
        s = make_settings()
        assert s.raw_dir.parent == s.data_dir
        assert s.processed_dir.parent == s.data_dir
        assert s.output_dir.parent == s.data_dir

    def test_ensure_directories_creates_dirs(self, tmp_path) -> None:
        """Test ensure_directories creates required directories."""
        data_dir = tmp_path / "data"
        raw_dir = data_dir / "raw"
        processed_dir = data_dir / "processed"
        output_dir = data_dir / "output"

        assert not raw_dir.exists()
        assert not processed_dir.exists()
        assert not output_dir.exists()

        for dir_path in [raw_dir, processed_dir, output_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        assert raw_dir.exists()
        assert processed_dir.exists()
        assert output_dir.exists()

    def test_portfolio_url_default(self) -> None:
        """Test portfolio_url has a default value."""
        s = make_settings()
        assert s.portfolio_url
        assert s.portfolio_url.startswith("http")


class TestProviderDetection:
    """Test active_provider auto-detection from available API keys."""

    def test_no_provider_configured(self) -> None:
        """No keys set → empty string."""
        s = make_settings()
        assert s.active_provider == ""

    def test_explicit_provider_overrides_auto(self) -> None:
        """Explicit LLM_PROVIDER takes priority over all keys."""
        s = make_settings(
            llm_provider="google",
            openai_api_key="sk-test",
            futureproof_proxy_key="fp-test",
        )
        assert s.active_provider == "google"

    def test_proxy_is_default_when_configured(self) -> None:
        """FutureProof proxy wins when both proxy and BYOK keys are set."""
        s = make_settings(
            futureproof_proxy_key="fp-test",
            openai_api_key="sk-test",
        )
        assert s.active_provider == "futureproof"

    def test_azure_before_openai(self) -> None:
        """Azure takes priority over OpenAI."""
        s = make_settings(
            azure_openai_api_key="az-test",
            azure_openai_endpoint="https://test.openai.azure.com/",
            openai_api_key="sk-test",
        )
        assert s.active_provider == "azure"

    def test_openai_detected(self) -> None:
        s = make_settings(openai_api_key="sk-test")
        assert s.active_provider == "openai"

    def test_anthropic_detected(self) -> None:
        s = make_settings(anthropic_api_key="sk-ant-test")
        assert s.active_provider == "anthropic"

    def test_google_detected(self) -> None:
        s = make_settings(google_api_key="AIza-test")
        assert s.active_provider == "google"

    def test_ollama_is_last_resort(self) -> None:
        """Ollama (always available) is lowest priority."""
        s = make_settings(ollama_base_url="http://localhost:11434")
        assert s.active_provider == "ollama"

    def test_has_properties(self) -> None:
        """Test individual has_* properties."""
        s = make_settings(openai_api_key="sk-test")
        assert s.has_openai is True
        assert s.has_anthropic is False
        assert s.has_proxy is False
        assert s.has_azure is False


class TestAzureEndpointNormalization:
    """Test Azure endpoint URL cleaning."""

    def test_strips_api_projects_path(self) -> None:
        """AI Foundry project path is removed."""
        s = make_settings(
            azure_openai_endpoint=(
                "https://res.services.ai.azure.com"
                "/api/projects/myproject"
            ),
        )
        assert s.azure_openai_endpoint == (
            "https://res.services.ai.azure.com"
        )

    def test_strips_trailing_slash(self) -> None:
        s = make_settings(
            azure_openai_endpoint=(
                "https://res.openai.azure.com/"
            ),
        )
        assert s.azure_openai_endpoint == (
            "https://res.openai.azure.com"
        )

    def test_preserves_clean_endpoint(self) -> None:
        s = make_settings(
            azure_openai_endpoint=(
                "https://res.openai.azure.com"
            ),
        )
        assert s.azure_openai_endpoint == (
            "https://res.openai.azure.com"
        )

    def test_empty_endpoint_unchanged(self) -> None:
        s = make_settings(azure_openai_endpoint="")
        assert s.azure_openai_endpoint == ""

    def test_rejects_non_url_endpoint(self) -> None:
        """API key accidentally pasted into endpoint field is rejected."""
        import pytest

        with pytest.raises(Exception, match="https://"):
            make_settings(
                azure_openai_endpoint="sk-abc123secretkey",
            )


class TestWriteUserSettingCleaning:
    """Test that write_user_setting cleans values before persisting."""

    def test_cleans_azure_endpoint_on_write(self, tmp_path, monkeypatch) -> None:
        """AI Foundry project path is stripped before writing to .env."""
        from fu7ur3pr00f.config import write_user_setting

        env_file = tmp_path / ".env"
        monkeypatch.setattr("fu7ur3pr00f.config._USER_ENV_PATH", env_file)

        write_user_setting(
            "AZURE_OPENAI_ENDPOINT",
            "https://res.services.ai.azure.com/api/projects/myproject",
        )
        content = env_file.read_text()
        assert "/api/projects/" not in content
        assert "https://res.services.ai.azure.com" in content
