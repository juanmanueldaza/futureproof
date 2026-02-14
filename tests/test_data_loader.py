"""Tests for data loading utilities."""

from unittest.mock import patch

from futureproof.utils.data_loader import (
    combine_career_data,
    load_career_data,
    load_career_data_for_cv,
)

_PATCH_TARGET = "futureproof.services.knowledge_service.KnowledgeService"


class TestLoadCareerData:
    """Test load_career_data function (queries ChromaDB via KnowledgeService)."""

    def test_returns_empty_dict_when_no_data(self) -> None:
        """Test returns empty dict when knowledge base is empty."""
        with patch(_PATCH_TARGET) as mock_cls:
            mock_cls.return_value.get_all_content.return_value = {}
            result = load_career_data()
            assert result == {}

    def test_returns_data_from_knowledge_base(self) -> None:
        """Test returns data from knowledge base."""
        expected = {
            "linkedin_data": "# LinkedIn\nSoftware Engineer",
            "portfolio_data": "# Portfolio\nDeveloper",
        }
        with patch(_PATCH_TARGET) as mock_cls:
            mock_cls.return_value.get_all_content.return_value = expected
            result = load_career_data()
            assert result == expected

    def test_only_includes_sources_with_content(self) -> None:
        """Test only includes sources that have indexed content."""
        with patch(_PATCH_TARGET) as mock_cls:
            mock_cls.return_value.get_all_content.return_value = {
                "portfolio_data": "# Portfolio\nContent"
            }
            result = load_career_data()
            assert "portfolio_data" in result
            assert "linkedin_data" not in result


class TestLoadCareerDataForCV:
    """Test load_career_data_for_cv function."""

    def test_returns_empty_string_when_no_data(self) -> None:
        """Test returns empty string when no data exists."""
        with patch(_PATCH_TARGET) as mock_cls:
            mock_cls.return_value.get_all_content.return_value = {}
            result = load_career_data_for_cv()
            assert result == ""

    def test_includes_section_headers(self) -> None:
        """Test includes section headers for each source."""
        with patch(_PATCH_TARGET) as mock_cls:
            mock_cls.return_value.get_all_content.return_value = {
                "linkedin_data": "LinkedIn content",
                "portfolio_data": "Portfolio content",
            }
            result = load_career_data_for_cv()
            assert "### LinkedIn" in result
            assert "### Portfolio" in result

    def test_returns_string_not_dict(self) -> None:
        """Test returns combined string, not dict."""
        with patch(_PATCH_TARGET) as mock_cls:
            mock_cls.return_value.get_all_content.return_value = {
                "portfolio_data": "Portfolio content",
            }
            result = load_career_data_for_cv()
            assert isinstance(result, str)


class TestCombineCareerData:
    """Test combine_career_data function."""

    def test_combines_all_data_sources(self, sample_career_data: dict[str, str]) -> None:
        """Test combines all provided data sources."""
        result = combine_career_data(sample_career_data)

        assert "LinkedIn Data" in result
        assert "Portfolio Data" in result

    def test_uses_custom_header_prefix(self, sample_career_data: dict[str, str]) -> None:
        """Test uses custom header prefix."""
        result = combine_career_data(sample_career_data, header_prefix="###")

        assert "### LinkedIn Data" in result
        assert "### Portfolio Data" in result

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
        data = {"portfolio_data": "Only portfolio data"}
        result = combine_career_data(data)

        assert "Portfolio Data" in result
        assert "LinkedIn Data" not in result

    def test_handles_none_values(self) -> None:
        """Test handles None values in data."""
        data = {
            "linkedin_data": "Has content",
            "portfolio_data": None,
        }
        result = combine_career_data(data)

        assert "LinkedIn Data" in result
        assert "Portfolio Data" not in result

    def test_preserves_content(self, sample_career_data: dict[str, str]) -> None:
        """Test preserves actual content from sources."""
        result = combine_career_data(sample_career_data)

        assert "Software Engineer with 5 years" in result
        assert "passionate about AI" in result
