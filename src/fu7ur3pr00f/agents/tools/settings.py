"""Settings tools for the career agent.

Provides read/write access to non-sensitive configuration. API keys and
tokens are excluded — users must use the /setup command for those.
"""

import logging

from langchain_core.tools import tool

from fu7ur3pr00f.config import reload_settings, settings, write_user_setting

logger = logging.getLogger(__name__)

# Settings the agent is allowed to modify (non-sensitive only).
_AGENT_CONFIGURABLE: dict[str, str] = {
    # Model routing
    "agent_model": "Model for agent tool calling (e.g. gpt-5-mini)",
    "analysis_model": "Model for analysis and CV generation (e.g. gpt-4.1)",
    "summary_model": "Model for conversation summarization (e.g. gpt-4o-mini)",
    "synthesis_model": "Model for analysis synthesis (e.g. o4-mini)",
    "embedding_model": "Model for embeddings (e.g. text-embedding-3-small)",
    "llm_provider": "LLM provider override (openai, anthropic, google, azure, ollama)",
    # Feature flags
    "jobspy_enabled": "Enable JobSpy job search (true/false)",
    "hn_mcp_enabled": "Enable Hacker News integration (true/false)",
    # Temperatures
    "llm_temperature": "General LLM temperature (0.0-1.0)",
    "cv_temperature": "CV generation temperature (0.0-1.0)",
    # Cache durations
    "market_cache_hours": "Market data cache duration in hours",
    "job_cache_hours": "Job search cache duration in hours",
    "content_cache_hours": "Content trends cache duration in hours",
    "forex_cache_hours": "Exchange rate cache duration in hours",
    # Knowledge
    "knowledge_auto_index": "Auto-index after data gathering (true/false)",
    "knowledge_chunk_max_tokens": "Max tokens per knowledge chunk",
    "knowledge_chunk_min_tokens": "Min tokens per knowledge chunk",
}

# Keys that require an agent restart to take effect.
_RESTART_KEYS = {
    "agent_model",
    "analysis_model",
    "summary_model",
    "synthesis_model",
    "embedding_model",
    "llm_provider",
}

# Sensitive keys that must go through /setup.
_SENSITIVE_KEYS = {
    "fu7ur3pr00f_proxy_key",
    "openai_api_key",
    "anthropic_api_key",
    "google_api_key",
    "azure_openai_api_key",
    "azure_openai_endpoint",
    "azure_embedding_deployment",
    "github_personal_access_token",
    "github_mcp_token",
    "tavily_api_key",
    "portfolio_url",
    "fu7ur3pr00f_proxy_url",
    "ollama_base_url",
}

# Known valid LLM providers.
_VALID_PROVIDERS = {
    "fu7ur3pr00f",
    "openai",
    "anthropic",
    "google",
    "azure",
    "ollama",
    "",
}


def _validate_setting_value(key: str, value: str) -> str | None:
    """Validate a setting value for type and range. Returns error or None."""
    try:
        if key in ("llm_temperature", "cv_temperature"):
            v = float(value)
            if not (0.0 <= v <= 2.0):
                return f"{key} must be between 0.0 and 2.0, got {value}"

        elif key in (
            "market_cache_hours",
            "job_cache_hours",
            "content_cache_hours",
            "forex_cache_hours",
        ):
            v = int(value)
            if v < 1:
                return f"{key} must be >= 1, got {value}"

        elif key == "knowledge_chunk_max_tokens":
            v = int(value)
            if v < 50:
                return f"{key} must be >= 50, got {value}"

        elif key == "knowledge_chunk_min_tokens":
            v = int(value)
            if v < 10:
                return f"{key} must be >= 10, got {value}"

        elif key in ("jobspy_enabled", "hn_mcp_enabled", "knowledge_auto_index"):
            if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                return f"{key} must be true or false, got {value!r}"

        elif key == "llm_provider":
            if value.lower() not in _VALID_PROVIDERS:
                valid = ", ".join(sorted(_VALID_PROVIDERS - {""}))
                return (
                    f"Unknown provider {value!r}. "
                    f"Valid: {valid} (or empty to auto-detect)"
                )

    except (ValueError, TypeError):
        return f"Invalid value for {key}: {value!r}"

    return None


@tool
def get_current_config() -> str:
    """Get current FutureProof configuration settings.

    Shows active LLM provider, model routing, feature flags, cache durations,
    and integration status. API keys are redacted for security.

    Use this when the user asks about their current settings or configuration.
    """
    lines: list[str] = []

    # Active provider
    provider = settings.active_provider
    lines.append(f"Active LLM provider: {provider or 'none'}")
    lines.append("")

    # Provider availability
    providers = []
    if settings.has_proxy:
        providers.append("fu7ur3pr00f")
    if settings.has_azure:
        providers.append("azure")
    if settings.has_openai:
        providers.append("openai")
    if settings.has_anthropic:
        providers.append("anthropic")
    if settings.has_google:
        providers.append("google")
    if settings.has_ollama:
        providers.append("ollama")
    lines.append(
        f"Configured providers: {', '.join(providers) if providers else 'none'}"
    )
    lines.append("")

    # Model routing
    lines.append("Model routing:")
    lines.append(f"  agent_model: {settings.agent_model or '(default)'}")
    lines.append(f"  analysis_model: {settings.analysis_model or '(default)'}")
    lines.append(f"  summary_model: {settings.summary_model or '(default)'}")
    lines.append(f"  synthesis_model: {settings.synthesis_model or '(default)'}")
    lines.append(f"  embedding_model: {settings.embedding_model or '(default)'}")
    lines.append("")

    # Temperatures
    lines.append("Temperatures:")
    lines.append(f"  llm_temperature: {settings.llm_temperature}")
    lines.append(f"  cv_temperature: {settings.cv_temperature}")
    lines.append("")

    # Feature flags
    lines.append("Feature flags:")
    lines.append(f"  jobspy_enabled: {settings.jobspy_enabled}")
    lines.append(f"  hn_mcp_enabled: {settings.hn_mcp_enabled}")
    lines.append("")

    # Integrations
    lines.append("Integrations:")
    lines.append(
        f"  GitHub: {'configured' if settings.has_github_mcp else 'not configured'}"
    )
    lines.append(
        f"  Tavily: {'configured' if settings.has_tavily_mcp else 'not configured'}"
    )
    lines.append("")

    # Cache
    lines.append("Cache durations (hours):")
    lines.append(f"  market: {settings.market_cache_hours}")
    lines.append(f"  jobs: {settings.job_cache_hours}")
    lines.append(f"  content: {settings.content_cache_hours}")
    lines.append(f"  forex: {settings.forex_cache_hours}")
    lines.append("")

    # Knowledge
    lines.append("Knowledge base:")
    lines.append(f"  auto_index: {settings.knowledge_auto_index}")
    lines.append(f"  chunk_max_tokens: {settings.knowledge_chunk_max_tokens}")
    lines.append(f"  chunk_min_tokens: {settings.knowledge_chunk_min_tokens}")
    lines.append("")

    lines.append("To configure API keys, tell the user to run /setup.")

    return "\n".join(lines)


@tool
def update_setting(key: str, value: str) -> str:
    """Update a FutureProof configuration setting.

    Args:
        key: Setting name (e.g. 'agent_model', 'llm_temperature')
        value: New value for the setting

    Use this to change model routing, feature flags, temperatures, cache
    durations, and other non-sensitive settings. For API keys, tell the
    user to run /setup instead.

    Available settings: agent_model, analysis_model, summary_model,
    synthesis_model, embedding_model, llm_provider, llm_temperature,
    cv_temperature, jobspy_enabled, hn_mcp_enabled, market_cache_hours,
    job_cache_hours, content_cache_hours, forex_cache_hours,
    knowledge_auto_index, knowledge_chunk_max_tokens,
    knowledge_chunk_min_tokens.
    """
    key = key.lower()

    if key in _SENSITIVE_KEYS:
        return (
            f"{key!r} is a sensitive setting (API key/token). "
            "Ask the user to run /setup to configure it securely."
        )

    if key not in _AGENT_CONFIGURABLE:
        available = ", ".join(sorted(_AGENT_CONFIGURABLE))
        return f"Unknown setting: {key!r}. Available settings: {available}"

    # Validate value type and range
    error = _validate_setting_value(key, value)
    if error:
        return f"Invalid value: {error}"

    env_key = key.upper()
    write_user_setting(env_key, value)
    reload_settings()

    result = f"Updated {key} = {value}"

    if key in _RESTART_KEYS:
        from fu7ur3pr00f.agents.specialists.orchestrator import reset_orchestrator
        from fu7ur3pr00f.llm.fallback import reset_fallback_manager

        reset_fallback_manager()
        reset_orchestrator()
        result += ". New model will be used on the next message."

    logger.info("Setting updated via agent tool: %s=%s", key, value)
    return result
