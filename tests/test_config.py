"""Tests for configuration management."""

import pytest

from futureproof.config import Settings


def make_settings(**overrides) -> Settings:
    """Create a Settings instance with test defaults."""
    defaults = {
        "azure_openai_api_key": "test",
        "azure_openai_endpoint": "https://test.openai.azure.com/",
    }
    return Settings(**(defaults | overrides))  # type: ignore[arg-type]


class TestSettings:
    """Test Settings class."""

    def test_default_values(self) -> None:
        """Test that settings have expected defaults."""
        settings = make_settings(azure_openai_api_key="test-key")
        assert settings.default_language == "en"
        assert settings.azure_openai_api_key == "test-key"

    @pytest.mark.parametrize(
        ("groups_input", "expected"),
        [
            ("group1, group2, group3", ["group1", "group2", "group3"]),
            ("  group1  ,  group2  ", ["group1", "group2"]),
            ("", []),
            ("single-group", ["single-group"]),
        ],
        ids=["csv", "whitespace", "empty", "single"],
    )
    def test_gitlab_groups_list(self, groups_input: str, expected: list[str]) -> None:
        """Test gitlab_groups string is parsed to list."""
        settings = make_settings(gitlab_groups=groups_input)
        assert settings.gitlab_groups_list == expected

    def test_directory_paths_are_paths(self) -> None:
        """Test computed directory paths return Path objects."""
        from pathlib import Path

        settings = make_settings()
        assert isinstance(settings.data_dir, Path)
        assert isinstance(settings.raw_dir, Path)
        assert isinstance(settings.processed_dir, Path)
        assert isinstance(settings.output_dir, Path)

    def test_directory_paths_structure(self) -> None:
        """Test directory paths have correct names."""
        settings = make_settings()
        assert settings.data_dir.name == "data"
        assert settings.raw_dir.name == "raw"
        assert settings.processed_dir.name == "processed"
        assert settings.output_dir.name == "output"

    def test_directory_hierarchy(self) -> None:
        """Test directory paths are correctly nested."""
        settings = make_settings()
        assert settings.raw_dir.parent == settings.data_dir
        assert settings.processed_dir.parent == settings.data_dir
        assert settings.output_dir.parent == settings.data_dir

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

    def test_default_language_options(self) -> None:
        """Test default_language accepts valid options."""
        assert make_settings(default_language="en").default_language == "en"
        assert make_settings(default_language="es").default_language == "es"

    def test_portfolio_url_default(self) -> None:
        """Test portfolio_url has a default value."""
        settings = make_settings()
        assert settings.portfolio_url
        assert settings.portfolio_url.startswith("http")

    def test_username_defaults(self) -> None:
        """Test username fields have defaults."""
        settings = make_settings()
        assert settings.github_username
        assert settings.gitlab_username
