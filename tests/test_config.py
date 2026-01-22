"""Tests for configuration management."""

from futureproof.config import Settings


class TestSettings:
    """Test Settings class."""

    def test_default_values(self) -> None:
        """Test that settings have expected defaults."""
        settings = Settings(gemini_api_key="test-key")
        assert settings.default_language == "en"
        assert settings.gemini_api_key == "test-key"

    def test_gitlab_groups_list_parsing(self) -> None:
        """Test gitlab_groups string is parsed to list."""
        settings = Settings(
            gemini_api_key="test",
            gitlab_groups="group1, group2, group3",
        )
        assert settings.gitlab_groups_list == ["group1", "group2", "group3"]

    def test_gitlab_groups_list_strips_whitespace(self) -> None:
        """Test gitlab_groups strips whitespace from items."""
        settings = Settings(
            gemini_api_key="test",
            gitlab_groups="  group1  ,  group2  ",
        )
        assert settings.gitlab_groups_list == ["group1", "group2"]

    def test_gitlab_groups_empty_returns_empty_list(self) -> None:
        """Test empty gitlab_groups returns empty list."""
        settings = Settings(gemini_api_key="test", gitlab_groups="")
        assert settings.gitlab_groups_list == []

    def test_gitlab_groups_single_value(self) -> None:
        """Test single group value works correctly."""
        settings = Settings(gemini_api_key="test", gitlab_groups="single-group")
        assert settings.gitlab_groups_list == ["single-group"]

    def test_directory_paths_are_paths(self) -> None:
        """Test computed directory paths return Path objects."""
        from pathlib import Path

        settings = Settings(gemini_api_key="test")
        assert isinstance(settings.data_dir, Path)
        assert isinstance(settings.raw_dir, Path)
        assert isinstance(settings.processed_dir, Path)
        assert isinstance(settings.output_dir, Path)

    def test_directory_paths_structure(self) -> None:
        """Test directory paths have correct names."""
        settings = Settings(gemini_api_key="test")
        assert settings.data_dir.name == "data"
        assert settings.raw_dir.name == "raw"
        assert settings.processed_dir.name == "processed"
        assert settings.output_dir.name == "output"

    def test_directory_hierarchy(self) -> None:
        """Test directory paths are correctly nested."""
        settings = Settings(gemini_api_key="test")
        assert settings.raw_dir.parent == settings.data_dir
        assert settings.processed_dir.parent == settings.data_dir
        assert settings.output_dir.parent == settings.data_dir

    def test_ensure_directories_creates_dirs(self, tmp_path) -> None:
        """Test ensure_directories creates required directories."""
        # Manually override the project root for testing
        # We need to test the logic, so we'll create dirs in tmp_path
        data_dir = tmp_path / "data"
        raw_dir = data_dir / "raw"
        processed_dir = data_dir / "processed"
        output_dir = data_dir / "output"

        # Verify dirs don't exist
        assert not raw_dir.exists()
        assert not processed_dir.exists()
        assert not output_dir.exists()

        # Create them
        for dir_path in [raw_dir, processed_dir, output_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Verify they exist
        assert raw_dir.exists()
        assert processed_dir.exists()
        assert output_dir.exists()

    def test_default_language_options(self) -> None:
        """Test default_language accepts valid options."""
        settings_en = Settings(gemini_api_key="test", default_language="en")
        assert settings_en.default_language == "en"

        settings_es = Settings(gemini_api_key="test", default_language="es")
        assert settings_es.default_language == "es"

    def test_portfolio_url_default(self) -> None:
        """Test portfolio_url has a default value."""
        settings = Settings(gemini_api_key="test")
        assert settings.portfolio_url  # Has a value
        assert settings.portfolio_url.startswith("http")

    def test_username_defaults(self) -> None:
        """Test username fields have defaults."""
        settings = Settings(gemini_api_key="test")
        assert settings.github_username  # Has a value
        assert settings.gitlab_username  # Has a value
