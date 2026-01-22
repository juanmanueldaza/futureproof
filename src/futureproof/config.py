"""Configuration management using pydantic-settings."""

import re
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Validation pattern for GitLab group names
# GitLab groups: alphanumeric, underscores, dots, hyphens, must start with alphanumeric
GITLAB_GROUP_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys
    gemini_api_key: str = ""

    # User profiles
    github_username: str = "juanmanueldaza"
    gitlab_username: str = "juanmanueldaza"
    portfolio_url: str = "https://daza.ar"

    # GitLab groups to include (comma-separated)
    # These are groups where you contributed but may not be a direct member
    gitlab_groups: str = "colmena-project"

    # Defaults
    default_language: Literal["en", "es"] = "en"

    # LLM Configuration
    llm_provider: Literal["gemini"] = "gemini"
    llm_model: str = ""  # Empty = use provider default
    llm_temperature: float = 0.3
    cv_temperature: float = 0.2  # Lower for more consistent CV output

    # Output file names (removes magic strings from code)
    github_output_filename: str = "github_profile.md"
    gitlab_output_filename: str = "gitlab_profile.md"
    portfolio_output_filename: str = "portfolio.md"

    # LinkedIn files to load for different purposes
    linkedin_profile_files: str = "profile.md,experience.md,education.md,skills.md"
    linkedin_cv_files: str = (
        "profile.md,experience.md,education.md,skills.md,"
        "certifications.md,languages.md,projects.md,recommendations.md"
    )

    @property
    def linkedin_profile_files_list(self) -> list[str]:
        """Get LinkedIn profile files as a list."""
        return [f.strip() for f in self.linkedin_profile_files.split(",") if f.strip()]

    @property
    def linkedin_cv_files_list(self) -> list[str]:
        """Get LinkedIn CV files as a list."""
        return [f.strip() for f in self.linkedin_cv_files.split(",") if f.strip()]

    @property
    def gitlab_groups_list(self) -> list[str]:
        """Get GitLab groups as a validated list.

        Validates each group name to prevent CLI argument injection.

        Returns:
            List of validated group names

        Raises:
            ValueError: If any group name contains invalid characters
        """
        if not self.gitlab_groups:
            return []
        groups = [g.strip() for g in self.gitlab_groups.split(",") if g.strip()]
        for group in groups:
            if not GITLAB_GROUP_PATTERN.match(group):
                raise ValueError(
                    f"Invalid GitLab group name: '{group}'. "
                    "Group names must start with alphanumeric and contain only "
                    "alphanumeric characters, dots, underscores, and hyphens."
                )
        return groups

    # Paths (computed from project root)
    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        # config.py is at src/futureproof/config.py, so go up 3 levels
        return Path(__file__).parent.parent.parent

    @property
    def data_dir(self) -> Path:
        """Get the data directory."""
        return self.project_root / "data"

    @property
    def raw_dir(self) -> Path:
        """Get the raw data directory."""
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        """Get the processed data directory."""
        return self.data_dir / "processed"

    @property
    def output_dir(self) -> Path:
        """Get the output directory."""
        return self.data_dir / "output"

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        for dir_path in [self.raw_dir, self.processed_dir, self.output_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
