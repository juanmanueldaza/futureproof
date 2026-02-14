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

    # Azure OpenAI / AI Foundry
    azure_openai_api_key: str = ""  # https://ai.azure.com/
    azure_openai_endpoint: str = ""  # e.g. https://your-resource.openai.azure.com/
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_chat_deployment: str = ""  # e.g. "gpt-4.1"
    azure_embedding_deployment: str = ""  # e.g. "text-embedding-3-small"

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
    llm_model: str = ""  # Empty = use provider default
    llm_temperature: float = 0.3
    cv_temperature: float = 0.2  # Lower for more consistent CV output

    # MCP (Model Context Protocol) Configuration
    # GitHub MCP Server
    github_personal_access_token: str = ""  # Standard GitHub token env var
    github_mcp_token: str = ""  # Alternative setting name
    github_mcp_use_docker: bool = True
    github_mcp_image: str = "ghcr.io/github/github-mcp-server"
    github_mcp_command: str = "github-mcp-server"  # Native binary if not using Docker

    # GitLab MCP Server
    gitlab_mcp_url: str = ""  # e.g., https://gitlab.com/api/v4/mcp
    gitlab_mcp_token: str = ""  # GitLab OAuth or personal access token

    # Market Intelligence MCP Configuration
    # Tavily Search (1000 free queries/month, no credit card)
    # Get your key at: https://tavily.com/
    tavily_api_key: str = ""

    # JobSpy (no auth required, MIT licensed)
    jobspy_enabled: bool = True

    # Hacker News (no auth required, uses Algolia API)
    hn_mcp_enabled: bool = True

    # Market data caching (hours)
    market_cache_hours: int = 24  # Tech trends
    job_cache_hours: int = 12  # Jobs change faster
    content_cache_hours: int = 12  # Dev.to/SO content trends

    # Knowledge Base Configuration (RAG)
    knowledge_auto_index: bool = True  # Auto-index after gather
    knowledge_chunk_max_tokens: int = 500  # Max tokens per chunk
    knowledge_chunk_min_tokens: int = 50  # Min tokens per chunk (merge if smaller)

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

    @staticmethod
    def _split_csv(value: str) -> list[str]:
        """Split a comma-separated string into a trimmed list."""
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def linkedin_profile_files_list(self) -> list[str]:
        """Get LinkedIn profile files as a list."""
        return self._split_csv(self.linkedin_profile_files)

    @property
    def linkedin_cv_files_list(self) -> list[str]:
        """Get LinkedIn CV files as a list."""
        return self._split_csv(self.linkedin_cv_files)

    @property
    def gitlab_groups_list(self) -> list[str]:
        """Get GitLab groups as a validated list.

        Validates each group name to prevent CLI argument injection.

        Returns:
            List of validated group names

        Raises:
            ValueError: If any group name contains invalid characters
        """
        groups = self._split_csv(self.gitlab_groups)
        for group in groups:
            if not GITLAB_GROUP_PATTERN.match(group):
                raise ValueError(
                    f"Invalid GitLab group name: '{group}'. "
                    "Group names must start with alphanumeric and contain only "
                    "alphanumeric characters, dots, underscores, and hyphens."
                )
        return groups

    @property
    def github_mcp_token_resolved(self) -> str:
        """Get GitHub MCP token from various sources."""
        # Check explicit MCP token setting first
        if self.github_mcp_token:
            return self.github_mcp_token
        # Fall back to standard GitHub token
        if self.github_personal_access_token:
            return self.github_personal_access_token
        return ""

    @property
    def has_github_mcp(self) -> bool:
        """Check if GitHub MCP is configured."""
        return bool(self.github_mcp_token_resolved)

    @property
    def has_gitlab_mcp(self) -> bool:
        """Check if GitLab MCP is configured."""
        return bool(self.gitlab_mcp_url and self.gitlab_mcp_token)

    @property
    def has_azure(self) -> bool:
        """Check if Azure OpenAI is configured."""
        return bool(self.azure_openai_api_key and self.azure_openai_endpoint)

    @property
    def has_tavily_mcp(self) -> bool:
        """Check if Tavily Search MCP is configured."""
        return bool(self.tavily_api_key)

    @property
    def market_cache_dir(self) -> Path:
        """Get the market data cache directory."""
        return self.data_dir / "cache" / "market"

    @property
    def market_output_dir(self) -> Path:
        """Get the market data output directory."""
        return self.processed_dir / "market"

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
