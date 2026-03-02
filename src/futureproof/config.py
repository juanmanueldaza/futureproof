"""Configuration management using pydantic-settings."""

from pathlib import Path

from dotenv import set_key
from pydantic_settings import BaseSettings, SettingsConfigDict

# User-level config lives alongside profile and memory data.
_USER_ENV_PATH = Path.home() / ".futureproof" / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", str(_USER_ENV_PATH)),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Provider (auto-detected from available keys if empty)
    llm_provider: str = ""  # "futureproof", "openai", "anthropic", "google", "azure", "ollama"

    # FutureProof Proxy (default for new users — zero-config with starter tokens)
    futureproof_proxy_url: str = "https://llm.futureproof.dev"
    futureproof_proxy_key: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Google Gemini
    google_api_key: str = ""

    # Azure OpenAI / AI Foundry
    azure_openai_api_key: str = ""  # https://ai.azure.com/
    azure_openai_endpoint: str = ""  # e.g. https://your-resource.openai.azure.com/
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_chat_deployment: str = ""  # e.g. "gpt-4.1"
    azure_embedding_deployment: str = ""  # e.g. "text-embedding-3-small"

    # Ollama (local models)
    ollama_base_url: str = "http://localhost:11434"

    # Purpose-specific models (provider-agnostic, optional)
    agent_model: str = ""      # e.g. "gpt-5-mini", "claude-sonnet-4-20250514"
    analysis_model: str = ""   # e.g. "gpt-4.1", "claude-sonnet-4-20250514"
    summary_model: str = ""    # e.g. "gpt-4o-mini", "claude-haiku-4-5-20251001"
    synthesis_model: str = ""  # e.g. "o4-mini"
    embedding_model: str = ""  # e.g. "text-embedding-3-small", "nomic-embed-text"

    # Legacy Azure purpose-specific deployments (backward compat, prefer above)
    azure_agent_deployment: str = ""
    azure_analysis_deployment: str = ""
    azure_summary_deployment: str = ""
    azure_synthesis_deployment: str = ""

    # User profiles
    portfolio_url: str = "https://daza.ar"

    # LLM Configuration
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
    forex_cache_hours: int = 4  # Exchange rates (updated daily)

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
    def has_proxy(self) -> bool:
        """Check if FutureProof proxy is configured."""
        return bool(self.futureproof_proxy_key)

    @property
    def has_openai(self) -> bool:
        """Check if OpenAI is configured (key must start with sk-)."""
        return bool(self.openai_api_key and self.openai_api_key.startswith("sk-"))

    @property
    def has_anthropic(self) -> bool:
        """Check if Anthropic is configured."""
        return bool(self.anthropic_api_key)

    @property
    def has_google(self) -> bool:
        """Check if Google Gemini is configured."""
        return bool(self.google_api_key)

    @property
    def has_azure(self) -> bool:
        """Check if Azure OpenAI is configured."""
        return bool(self.azure_openai_api_key and self.azure_openai_endpoint)

    @property
    def has_ollama(self) -> bool:
        """Check if Ollama is configured."""
        return bool(self.ollama_base_url)

    @property
    def active_provider(self) -> str:
        """Determine the active LLM provider.

        Priority: explicit setting > proxy > Azure > OpenAI >
        Anthropic > Google > Ollama.
        """
        if self.llm_provider:
            return self.llm_provider
        if self.has_proxy:
            return "futureproof"
        if self.has_azure:
            return "azure"
        if self.has_openai:
            return "openai"
        if self.has_anthropic:
            return "anthropic"
        if self.has_google:
            return "google"
        if self.has_ollama:
            return "ollama"
        return ""

    @property
    def has_tavily_mcp(self) -> bool:
        """Check if Tavily Search MCP is configured."""
        return bool(self.tavily_api_key)

    @property
    def market_cache_dir(self) -> Path:
        """Get the market data cache directory."""
        return self.data_dir / "cache" / "market"

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


def get_user_env_path() -> Path:
    """Path to the user-level .env file (~/.futureproof/.env)."""
    return _USER_ENV_PATH


def write_user_setting(key: str, value: str) -> None:
    """Write a key=value pair to the user-level .env file.

    Creates the file with 0o600 permissions if it doesn't exist.
    Uses python-dotenv's set_key() for safe read-modify-write.
    """
    env_path = get_user_env_path()
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.touch(mode=0o600)
    set_key(str(env_path), key, value)
    env_path.chmod(0o600)


def reload_settings() -> None:
    """Reload settings from env files, updating the global singleton in-place.

    All modules that imported ``settings`` by name keep their reference to
    the same object, so mutating it ensures everyone sees the new values.
    """
    new = Settings()
    for field_name in Settings.model_fields:
        setattr(settings, field_name, getattr(new, field_name))
