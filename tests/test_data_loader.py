"""Tests for data loading utilities."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from futureproof.utils.data_loader import (
    CareerDataLoader,
    DataContext,
    combine_career_data,
    load_career_data,
    load_career_data_for_cv,
)


@pytest.fixture
def mock_settings(tmp_path: Path) -> MagicMock:
    """Create a mock settings object with all necessary attributes."""
    mock = MagicMock()
    mock.processed_dir = tmp_path / "data" / "processed"
    mock.github_output_filename = "github_profile.md"
    mock.gitlab_output_filename = "gitlab_profile.md"
    mock.portfolio_output_filename = "portfolio.md"
    mock.linkedin_profile_files_list = ["profile.md", "experience.md", "education.md", "skills.md"]
    mock.linkedin_cv_files_list = [
        "profile.md",
        "experience.md",
        "education.md",
        "skills.md",
        "certifications.md",
        "languages.md",
        "projects.md",
        "recommendations.md",
    ]
    return mock


class TestLoadCareerData:
    """Test load_career_data function."""

    def test_returns_empty_dict_when_no_data(self, tmp_project: Path) -> None:
        """Test returns empty dict when no processed data exists."""
        mock = MagicMock()
        mock.processed_dir = tmp_project / "data" / "processed"
        mock.github_output_filename = "github_profile.md"
        mock.gitlab_output_filename = "gitlab_profile.md"
        mock.portfolio_output_filename = "portfolio.md"
        mock.linkedin_profile_files_list = ["profile.md"]

        with patch("futureproof.utils.data_loader.settings", mock):
            # Clear any cached data
            from futureproof.utils.data_loader import _loader

            _loader.clear_cache()
            result = load_career_data()
            assert result == {}

    def test_loads_linkedin_data(self, populated_data_dir: Path, mock_settings: MagicMock) -> None:
        """Test loads LinkedIn data from multiple files."""
        mock_settings.processed_dir = populated_data_dir / "data" / "processed"

        with patch("futureproof.utils.data_loader.settings", mock_settings):
            from futureproof.utils.data_loader import _loader

            _loader.clear_cache()
            result = load_career_data()

            assert "linkedin_data" in result
            assert "John Doe" in result["linkedin_data"]
            assert "Experience" in result["linkedin_data"]
            assert "Education" in result["linkedin_data"]
            assert "Skills" in result["linkedin_data"]

    def test_loads_github_data(self, populated_data_dir: Path, mock_settings: MagicMock) -> None:
        """Test loads GitHub data."""
        mock_settings.processed_dir = populated_data_dir / "data" / "processed"

        with patch("futureproof.utils.data_loader.settings", mock_settings):
            from futureproof.utils.data_loader import _loader

            _loader.clear_cache()
            result = load_career_data()

            assert "github_data" in result
            assert "GitHub Profile" in result["github_data"]

    def test_loads_gitlab_data(self, populated_data_dir: Path, mock_settings: MagicMock) -> None:
        """Test loads GitLab data."""
        mock_settings.processed_dir = populated_data_dir / "data" / "processed"

        with patch("futureproof.utils.data_loader.settings", mock_settings):
            from futureproof.utils.data_loader import _loader

            _loader.clear_cache()
            result = load_career_data()

            assert "gitlab_data" in result
            assert "GitLab Profile" in result["gitlab_data"]

    def test_loads_portfolio_data(self, populated_data_dir: Path, mock_settings: MagicMock) -> None:
        """Test loads portfolio data."""
        mock_settings.processed_dir = populated_data_dir / "data" / "processed"

        with patch("futureproof.utils.data_loader.settings", mock_settings):
            from futureproof.utils.data_loader import _loader

            _loader.clear_cache()
            result = load_career_data()

            assert "portfolio_data" in result
            assert "Portfolio" in result["portfolio_data"]

    def test_handles_missing_files_gracefully(
        self, tmp_project: Path, mock_settings: MagicMock
    ) -> None:
        """Test handles missing individual files gracefully."""
        processed_dir = tmp_project / "data" / "processed"
        # Only create GitHub file
        (processed_dir / "github" / "github_profile.md").write_text("# GitHub")

        mock_settings.processed_dir = processed_dir

        with patch("futureproof.utils.data_loader.settings", mock_settings):
            from futureproof.utils.data_loader import _loader

            _loader.clear_cache()
            result = load_career_data()

            assert "github_data" in result
            assert "linkedin_data" not in result
            assert "gitlab_data" not in result
            assert "portfolio_data" not in result


class TestLoadCareerDataForCV:
    """Test load_career_data_for_cv function."""

    def test_returns_empty_string_when_no_data(
        self, tmp_project: Path, mock_settings: MagicMock
    ) -> None:
        """Test returns empty string when no data exists."""
        mock_settings.processed_dir = tmp_project / "data" / "processed"

        with patch("futureproof.utils.data_loader.settings", mock_settings):
            from futureproof.utils.data_loader import _loader

            _loader.clear_cache()
            result = load_career_data_for_cv()
            assert result == ""

    def test_includes_section_headers(
        self, populated_data_dir: Path, mock_settings: MagicMock
    ) -> None:
        """Test includes section headers for each source."""
        mock_settings.processed_dir = populated_data_dir / "data" / "processed"

        with patch("futureproof.utils.data_loader.settings", mock_settings):
            from futureproof.utils.data_loader import _loader

            _loader.clear_cache()
            result = load_career_data_for_cv()

            assert "### LinkedIn" in result
            assert "### GitHub" in result
            assert "### GitLab" in result
            assert "### Portfolio" in result

    def test_returns_string_not_dict(
        self, populated_data_dir: Path, mock_settings: MagicMock
    ) -> None:
        """Test returns combined string, not dict."""
        mock_settings.processed_dir = populated_data_dir / "data" / "processed"

        with patch("futureproof.utils.data_loader.settings", mock_settings):
            from futureproof.utils.data_loader import _loader

            _loader.clear_cache()
            result = load_career_data_for_cv()

            assert isinstance(result, str)


class TestCombineCareerData:
    """Test combine_career_data function."""

    def test_combines_all_data_sources(self, sample_career_data: dict[str, str]) -> None:
        """Test combines all provided data sources."""
        result = combine_career_data(sample_career_data)

        assert "LinkedIn Data" in result
        assert "GitHub Data" in result
        assert "GitLab Data" in result
        assert "Portfolio Data" in result

    def test_uses_custom_header_prefix(self, sample_career_data: dict[str, str]) -> None:
        """Test uses custom header prefix."""
        result = combine_career_data(sample_career_data, header_prefix="###")

        assert "### LinkedIn Data" in result
        assert "### GitHub Data" in result

    def test_excludes_analysis_by_default(self) -> None:
        """Test excludes analysis field by default."""
        data = {
            "linkedin_data": "LinkedIn content",
            "analysis": "Previous analysis content",
        }
        result = combine_career_data(data)

        assert "LinkedIn Data" in result
        assert "Previous Analysis" not in result

    def test_includes_analysis_when_requested(self) -> None:
        """Test includes analysis when include_analysis=True."""
        data = {
            "linkedin_data": "LinkedIn content",
            "analysis": "Previous analysis content",
        }
        result = combine_career_data(data, include_analysis=True)

        assert "LinkedIn Data" in result
        assert "Previous Analysis" in result

    def test_handles_empty_data(self) -> None:
        """Test handles empty data dict."""
        result = combine_career_data({})
        assert result == ""

    def test_handles_partial_data(self) -> None:
        """Test handles partial data (some sources missing)."""
        data = {"github_data": "Only GitHub data"}
        result = combine_career_data(data)

        assert "GitHub Data" in result
        assert "LinkedIn Data" not in result

    def test_handles_none_values(self) -> None:
        """Test handles None values in data."""
        data = {
            "linkedin_data": "Has content",
            "github_data": None,
        }
        result = combine_career_data(data)

        assert "LinkedIn Data" in result
        assert "GitHub Data" not in result

    def test_preserves_content(self, sample_career_data: dict[str, str]) -> None:
        """Test preserves actual content from sources."""
        result = combine_career_data(sample_career_data)

        assert "Software Engineer with 5 years" in result
        assert "project-a" in result
        assert "internal-tool (Go)" in result
        assert "passionate about AI" in result


class TestCareerDataLoader:
    """Test CareerDataLoader class directly."""

    def test_caches_results(self, populated_data_dir: Path, mock_settings: MagicMock) -> None:
        """Test that loader caches results."""
        mock_settings.processed_dir = populated_data_dir / "data" / "processed"

        with patch("futureproof.utils.data_loader.settings", mock_settings):
            loader = CareerDataLoader()
            result1 = loader.load(DataContext.ANALYSIS)
            result2 = loader.load(DataContext.ANALYSIS)

            # Should be the same cached object
            assert result1 is result2

    def test_clear_cache(self, populated_data_dir: Path, mock_settings: MagicMock) -> None:
        """Test cache clearing."""
        mock_settings.processed_dir = populated_data_dir / "data" / "processed"

        with patch("futureproof.utils.data_loader.settings", mock_settings):
            loader = CareerDataLoader()
            result1 = loader.load(DataContext.ANALYSIS)
            loader.clear_cache()
            result2 = loader.load(DataContext.ANALYSIS)

            # Should be different objects after cache clear
            assert result1 is not result2
            # But should have same content
            assert result1 == result2
