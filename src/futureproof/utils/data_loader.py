"""Unified career data loading utilities.

This module consolidates data loading logic to eliminate DRY violations
and provides memoization for improved performance.
"""

import logging
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


class DataContext(Enum):
    """Context for data loading - determines which files to include."""

    ANALYSIS = "analysis"  # Basic profile files
    CV_GENERATION = "cv"  # Extended files for CV


class CareerDataLoader:
    """Centralized career data loading with memoization.

    Removes DRY violation between load_career_data() and load_career_data_for_cv().
    Uses configurable file lists from settings.
    """

    def __init__(self) -> None:
        self._cache: dict[DataContext, dict[str, str]] = {}

    def load(self, context: DataContext = DataContext.ANALYSIS) -> dict[str, str]:
        """Load career data based on context.

        Args:
            context: Determines which files to load

        Returns:
            Dictionary with keys like 'linkedin_data', 'github_data', etc.
        """
        if context in self._cache:
            return self._cache[context]

        data: dict[str, str] = {}

        # LinkedIn
        linkedin_data = self._load_linkedin(context)
        if linkedin_data:
            data["linkedin_data"] = linkedin_data

        # GitHub
        github_data = self._load_file(
            settings.processed_dir / "github" / settings.github_output_filename
        )
        if github_data:
            data["github_data"] = github_data

        # GitLab
        gitlab_data = self._load_file(
            settings.processed_dir / "gitlab" / settings.gitlab_output_filename
        )
        if gitlab_data:
            data["gitlab_data"] = gitlab_data

        # Portfolio
        portfolio_data = self._load_file(
            settings.processed_dir / "portfolio" / settings.portfolio_output_filename
        )
        if portfolio_data:
            data["portfolio_data"] = portfolio_data

        # CliftonStrengths Assessment
        assessment_data = self._load_file(
            settings.processed_dir / "assessment" / "cliftonstrengths.md"
        )
        if assessment_data:
            data["assessment_data"] = assessment_data

        self._cache[context] = data
        return data

    def _load_linkedin(self, context: DataContext) -> str:
        """Load LinkedIn files based on context."""
        linkedin_dir = settings.processed_dir / "linkedin"
        if not linkedin_dir.exists():
            return ""

        linkedin_dir_resolved = linkedin_dir.resolve()

        # Select files based on context
        if context == DataContext.CV_GENERATION:
            filenames = settings.linkedin_cv_files_list
        else:
            filenames = settings.linkedin_profile_files_list

        parts = []
        for filename in filenames:
            filepath = self._safe_path(linkedin_dir, filename, linkedin_dir_resolved)
            if filepath and filepath.exists():
                parts.append(filepath.read_text())

        return "\n\n".join(parts)

    def _safe_path(
        self, base_dir: Path, filename: str, base_resolved: Path | None = None
    ) -> Path | None:
        """Safely resolve a path, preventing traversal attacks.

        Args:
            base_dir: The base directory
            filename: The filename to join
            base_resolved: Pre-resolved base directory (optimization)

        Returns:
            Resolved path if safe, None if path traversal detected
        """
        if base_resolved is None:
            base_resolved = base_dir.resolve()

        filepath = (base_dir / filename).resolve()

        # Prevent path traversal
        if not str(filepath).startswith(str(base_resolved)):
            logger.warning("Path traversal attempt blocked: %s", filename)
            return None

        # Prevent symlink attacks
        if filepath.is_symlink():
            logger.warning("Symlink access blocked: %s", filepath)
            return None

        return filepath

    def _load_file(self, path: Path) -> str:
        """Load a single file if it exists and is safe."""
        resolved = path.resolve()

        # Check it's within processed_dir
        processed_resolved = settings.processed_dir.resolve()
        if not str(resolved).startswith(str(processed_resolved)):
            logger.warning("Path traversal attempt blocked: %s", path)
            return ""

        # Block symlinks
        if path.is_symlink():
            logger.warning("Symlink access blocked: %s", path)
            return ""

        if resolved.exists():
            return resolved.read_text()
        return ""

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()


# Module-level instance for convenience
_loader = CareerDataLoader()


def load_career_data() -> dict[str, str]:
    """Load all processed career data from files.

    Returns:
        Dictionary with keys like 'linkedin_data', 'github_data', etc.
    """
    return _loader.load(DataContext.ANALYSIS)


def load_career_data_for_cv() -> str:
    """Load career data formatted for CV generation.

    Includes additional LinkedIn files relevant for CVs.

    Returns:
        Combined markdown string of all career data
    """
    data = _loader.load(DataContext.CV_GENERATION)
    if not data:
        return ""

    # Format with headers for CV context
    parts = []
    linkedin_dir = settings.processed_dir / "linkedin"

    # LinkedIn files with headers
    if linkedin_dir.exists():
        for filename in settings.linkedin_cv_files_list:
            filepath = linkedin_dir / filename
            if filepath.exists():
                parts.append(f"### LinkedIn {filepath.stem}\n{filepath.read_text()}")

    # Other sources
    github_file = settings.processed_dir / "github" / settings.github_output_filename
    if github_file.exists():
        parts.append(f"### GitHub\n{github_file.read_text()}")

    gitlab_file = settings.processed_dir / "gitlab" / settings.gitlab_output_filename
    if gitlab_file.exists():
        parts.append(f"### GitLab\n{gitlab_file.read_text()}")

    portfolio_file = settings.processed_dir / "portfolio" / settings.portfolio_output_filename
    if portfolio_file.exists():
        parts.append(f"### Portfolio\n{portfolio_file.read_text()}")

    # CliftonStrengths Assessment
    assessment_file = settings.processed_dir / "assessment" / "cliftonstrengths.md"
    if assessment_file.exists():
        parts.append(f"### CliftonStrengths Assessment\n{assessment_file.read_text()}")

    return "\n\n".join(parts) if parts else ""


def combine_career_data(
    data: Mapping[str, Any],
    header_prefix: str = "##",
    include_analysis: bool = False,
) -> str:
    """Combine career data dict into formatted string.

    Args:
        data: Dictionary with career data (linkedin_data, github_data, etc.)
        header_prefix: Markdown header prefix (default "##")
        include_analysis: Whether to include 'analysis' field if present

    Returns:
        Combined markdown string
    """
    parts = []
    source_names = {
        "linkedin_data": "LinkedIn Data",
        "github_data": "GitHub Data",
        "gitlab_data": "GitLab Data",
        "portfolio_data": "Portfolio Data",
        "assessment_data": "CliftonStrengths Assessment",
    }

    if include_analysis:
        source_names["analysis"] = "Previous Analysis"

    for key, name in source_names.items():
        value = data.get(key)
        if value:
            parts.append(f"{header_prefix} {name}\n{value}")

    return "\n\n".join(parts)


def clear_data_cache() -> None:
    """Clear the data loader cache.

    Call this when data files have been updated and need to be reloaded.
    """
    _loader.clear_cache()
