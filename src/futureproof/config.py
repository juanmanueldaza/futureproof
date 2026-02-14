"""Configuration management using pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Purpose-specific model deployments (optional, empty = use default chain)
    azure_agent_deployment: str = ""  # Tool calling (e.g. "gpt-5")
    azure_analysis_deployment: str = ""  # Analysis/CV generation (e.g. "gpt-4.1")
    azure_summary_deployment: str = ""  # Summarization (e.g. "gpt-4.1-mini")

    # User profiles
    portfolio_url: str = "https://daza.ar"

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
