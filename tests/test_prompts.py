"""Tests for the prompt loader and backward compatibility."""

import pytest

from futureproof.prompts.loader import load_prompt

# All prompt file stems that must exist
ALL_PROMPTS = [
    "system",
    "analyze_career",
    "analyze_gaps",
    "generate_cv",
    "strategic_advice",
    "market_fit",
    "market_skill_gap",
    "trending_skills",
]


class TestLoader:
    """Tests for load_prompt()."""

    @pytest.mark.parametrize("name", ALL_PROMPTS)
    def test_all_prompts_load(self, name: str):
        content = load_prompt(name)
        assert isinstance(content, str)
        assert len(content) > 50

    def test_missing_prompt_raises(self):
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent_prompt")

    def test_path_traversal_blocked(self):
        with pytest.raises(ValueError, match="Invalid prompt name"):
            load_prompt("../../etc/passwd")

    def test_caching(self):
        first = load_prompt("system")
        second = load_prompt("system")
        assert first is second  # same object from cache


class TestVariableSubstitution:
    """Tests for .format() variable substitution in prompt templates."""

    def test_system_prompt_has_user_profile_var(self):
        content = load_prompt("system")
        assert "{user_profile}" in content
        formatted = content.format(user_profile="Test User")
        assert "Test User" in formatted
        assert "{user_profile}" not in formatted

    def test_market_fit_has_variables(self):
        content = load_prompt("market_fit")
        assert "{career_data}" in content
        assert "{market_data}" in content
        formatted = content.format(career_data="my career", market_data="market info")
        assert "my career" in formatted
        assert "market info" in formatted

    def test_analyze_gaps_has_variable(self):
        content = load_prompt("analyze_gaps")
        assert "{career_data}" in content

    def test_analyze_career_has_no_variables(self):
        """analyze_career is appended to data, not formatted."""
        content = load_prompt("analyze_career")
        # Should not raise when format() is called with no args
        # (no {var} placeholders to fill)
        assert "{" not in content or content.format() == content


class TestBackwardCompat:
    """Tests for backward-compatible module-level attribute access."""

    def test_generate_cv_prompt_import(self):
        from futureproof.prompts import GENERATE_CV_PROMPT

        assert isinstance(GENERATE_CV_PROMPT, str)
        assert "ATS" in GENERATE_CV_PROMPT

    def test_system_prompt_import(self):
        from futureproof.prompts import SYSTEM_PROMPT

        assert isinstance(SYSTEM_PROMPT, str)
        assert "FutureProof" in SYSTEM_PROMPT

    def test_unknown_attr_raises(self):
        with pytest.raises(ImportError):
            from futureproof.prompts import NONEXISTENT_PROMPT  # noqa: F401
