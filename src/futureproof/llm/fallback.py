"""LLM fallback chain with multi-provider support.

Provides automatic fallback between LLM models when rate limits
or other errors are encountered. Supports multiple providers:
FutureProof proxy, OpenAI, Anthropic, Google, Azure OpenAI, and Ollama.
"""

import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from futureproof.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for a single model in the fallback chain."""

    provider: str  # "futureproof", "openai", "anthropic", "google", "azure", "ollama"
    model: str
    description: str
    reasoning: bool = False  # Reasoning models don't support temperature


# Reasoning model prefixes — these don't accept temperature/top_p
_REASONING_PREFIXES = ("o1", "o3", "o4")

# LangChain model_provider strings for each provider
_PROVIDER_MAP: dict[str, str] = {
    "futureproof": "openai",  # Proxy is OpenAI-compatible
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google_genai",
    "azure": "azure_openai",
    "ollama": "ollama",
}

# Default fallback chains per provider
_PROVIDER_CHAINS: dict[str, list[ModelConfig]] = {
    "futureproof": [
        ModelConfig("futureproof", "gpt-4.1", "FutureProof GPT-4.1"),
        ModelConfig("futureproof", "gpt-5-mini", "FutureProof GPT-5 Mini"),
        ModelConfig("futureproof", "gpt-4o", "FutureProof GPT-4o"),
        ModelConfig("futureproof", "gpt-4o-mini", "FutureProof GPT-4o Mini"),
    ],
    "openai": [
        ModelConfig("openai", "gpt-4.1", "OpenAI GPT-4.1"),
        ModelConfig("openai", "gpt-5-mini", "OpenAI GPT-5 Mini"),
        ModelConfig("openai", "gpt-4o", "OpenAI GPT-4o"),
        ModelConfig("openai", "gpt-4o-mini", "OpenAI GPT-4o Mini"),
    ],
    "anthropic": [
        ModelConfig("anthropic", "claude-sonnet-4-20250514", "Claude Sonnet 4"),
        ModelConfig("anthropic", "claude-haiku-4-5-20251001", "Claude Haiku 4.5"),
    ],
    "google": [
        ModelConfig("google", "gemini-2.5-flash", "Gemini 2.5 Flash"),
        ModelConfig("google", "gemini-2.5-pro", "Gemini 2.5 Pro"),
    ],
    "azure": [
        ModelConfig("azure", "gpt-4.1", "Azure GPT-4.1"),
        ModelConfig("azure", "gpt-5-mini", "Azure GPT-5 Mini"),
        ModelConfig("azure", "gpt-4o", "Azure GPT-4o"),
        ModelConfig("azure", "gpt-4.1-mini", "Azure GPT-4.1 Mini"),
        ModelConfig("azure", "gpt-4o-mini", "Azure GPT-4o Mini"),
    ],
    "ollama": [
        ModelConfig("ollama", "qwen3", "Ollama Qwen3"),
    ],
}


def build_default_chain() -> list[ModelConfig]:
    """Build the default fallback chain from the active provider."""
    provider = settings.active_provider
    return list(_PROVIDER_CHAINS.get(provider, []))


def _build_provider_kwargs(config: ModelConfig) -> dict[str, Any]:
    """Build provider-specific kwargs for init_chat_model."""
    provider = config.provider
    kwargs: dict[str, Any] = {}

    if provider == "azure":
        kwargs["azure_deployment"] = config.model
        kwargs["azure_endpoint"] = settings.azure_openai_endpoint
        kwargs["api_version"] = settings.azure_openai_api_version
        kwargs["api_key"] = settings.azure_openai_api_key
    elif provider == "futureproof":
        kwargs["api_key"] = settings.futureproof_proxy_key
        kwargs["base_url"] = settings.futureproof_proxy_url
    elif provider == "openai":
        kwargs["api_key"] = settings.openai_api_key
    elif provider == "anthropic":
        kwargs["api_key"] = settings.anthropic_api_key
    elif provider == "google":
        kwargs["google_api_key"] = settings.google_api_key
    elif provider == "ollama":
        kwargs["base_url"] = settings.ollama_base_url

    return kwargs


class FallbackLLMManager:
    """Manages LLM model selection with automatic fallback on rate limits.

    This class maintains state about which models have failed recently
    and provides automatic fallback to alternative models when needed.
    """

    # Error indicators that should trigger fallback
    FALLBACK_ERROR_INDICATORS = [
        # Rate limits
        "429",
        "413",
        "rate_limit",
        "rate limit",
        "quota",
        "too many requests",
        "resource_exhausted",
        "tokens per",
        # Model unavailability
        "model_decommissioned",
        "decommissioned",
        "model not found",
        "not_found",
        "404",
        "does not exist",
        "is not found",
        "unavailable",
        "deprecated",
        "not supported",
    ]

    def __init__(
        self,
        fallback_chain: list[ModelConfig] | None = None,
        temperature: float | None = None,
    ):
        """Initialize the fallback manager.

        Args:
            fallback_chain: Custom chain of models to try. Uses default if None.
            temperature: LLM temperature. Uses config setting if None.
        """
        self._chain = fallback_chain or build_default_chain()
        self._temperature = (
            temperature if temperature is not None else settings.llm_temperature
        )
        self._failed_models: set[str] = set()
        self._current_model: ModelConfig | None = None

    def _model_key(self, config: ModelConfig) -> str:
        """Get a unique key for a model config."""
        return f"{config.provider}/{config.model}"

    def _is_fallback_error(self, error: Exception) -> bool:
        """Check if an exception should trigger a fallback to another model."""
        error_str = str(error).lower()
        return any(
            indicator in error_str for indicator in self.FALLBACK_ERROR_INDICATORS
        )

    def _create_model(
        self, config: ModelConfig, temperature: float | None = None
    ) -> BaseChatModel:
        """Create a LangChain chat model from config using init_chat_model.

        Args:
            config: Model configuration to instantiate
            temperature: Optional per-call temperature override. If None,
                uses the manager's default temperature.
        """
        from langchain.chat_models import init_chat_model

        model_provider = _PROVIDER_MAP.get(config.provider)
        if not model_provider:
            raise ValueError(f"Unknown provider: {config.provider}")

        is_reasoning = config.reasoning or any(
            config.model.startswith(p) for p in _REASONING_PREFIXES
        )

        kwargs: dict[str, Any] = {"streaming": True}

        # Reasoning models (o-series) don't support temperature/top_p/max_tokens
        if not is_reasoning:
            effective_temperature = (
                temperature if temperature is not None else self._temperature
            )
            kwargs["temperature"] = effective_temperature
            kwargs["max_tokens"] = 4096

        # Add provider-specific kwargs
        kwargs.update(_build_provider_kwargs(config))

        return init_chat_model(
            model=config.model,
            model_provider=model_provider,
            **kwargs,
        )

    def get_available_models(self) -> list[ModelConfig]:
        """Get list of available models (not failed)."""
        return [
            config
            for config in self._chain
            if self._model_key(config) not in self._failed_models
        ]

    def get_model(
        self,
        temperature: float | None = None,
        chain: list[ModelConfig] | None = None,
    ) -> tuple[BaseChatModel, ModelConfig]:
        """Get the best available model.

        Args:
            temperature: Optional per-call temperature override. If None,
                uses the manager's default temperature.
            chain: Optional chain override for purpose-specific routing.
                If provided, uses this chain instead of the default.
                Failed-model tracking still applies globally.

        Returns:
            Tuple of (model instance, model config)

        Raises:
            RuntimeError: If no models are available
        """
        effective_chain = chain or self._chain
        available = [
            config
            for config in effective_chain
            if self._model_key(config) not in self._failed_models
        ]

        if not available:
            # Reset failed models and try again
            logger.warning("All models failed, resetting failure state")
            self._failed_models.clear()
            available = [
                config
                for config in effective_chain
                if self._model_key(config) not in self._failed_models
            ]

        if not available:
            raise RuntimeError(
                "No LLM provider configured. Sign up for free tokens at "
                "https://futureproof.dev/signup, or set OPENAI_API_KEY, "
                "ANTHROPIC_API_KEY, or install Ollama for local models."
            )

        config = available[0]
        self._current_model = config

        logger.info(f"Using model: {config.description}")
        return self._create_model(config, temperature=temperature), config

    def mark_failed(self, config: ModelConfig | None = None) -> None:
        """Mark a model as failed (e.g., due to rate limiting).

        Args:
            config: Model config to mark. Uses current model if None.
        """
        config = config or self._current_model
        if config:
            key = self._model_key(config)
            logger.warning(f"Marking model as failed: {config.description}")
            self._failed_models.add(key)

    def handle_error(self, error: Exception) -> bool:
        """Handle an error from model invocation.

        Args:
            error: The exception that occurred

        Returns:
            True if fallback should be attempted (rate limit, model unavailable),
            False if this is a different type of error
        """
        if self._is_fallback_error(error):
            self.mark_failed()
            remaining = len(self.get_available_models())
            if remaining > 0:
                logger.info(
                    f"Model error detected, {remaining} fallback model(s) available"
                )
                return True
            else:
                logger.warning(
                    "Model error detected, no fallback models available"
                )
        return False

    def get_status(self) -> dict[str, Any]:
        """Get current status of the fallback manager."""
        return {
            "current_model": (
                self._current_model.description if self._current_model else None
            ),
            "failed_models": list(self._failed_models),
            "available_models": [
                m.description for m in self.get_available_models()
            ],
            "total_models": len(self._chain),
        }


# Global instance for session-wide state
_fallback_manager: FallbackLLMManager | None = None


def get_fallback_manager() -> FallbackLLMManager:
    """Get the global fallback manager instance."""
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = FallbackLLMManager()
    return _fallback_manager


def reset_fallback_manager() -> None:
    """Reset the global fallback manager, forcing re-creation on next use.

    Call after settings reload when LLM provider config changes.
    """
    global _fallback_manager
    _fallback_manager = None


def _build_purpose_chain(
    model_name: str, provider: str, description: str
) -> list[ModelConfig]:
    """Build a fallback chain with a purpose-specific model prepended.

    The purpose model is tried first; if it fails, the default chain
    models are tried in order (skipping any duplicate).
    """
    default_chain = build_default_chain()
    purpose_model = ModelConfig(provider, model_name, description)
    return [purpose_model] + [
        c for c in default_chain if c.model != model_name
    ]


def get_model_for_purpose(
    purpose: str,
    temperature: float | None = None,
) -> tuple[BaseChatModel, ModelConfig]:
    """Get a model optimized for a specific purpose.

    Checks provider-agnostic settings first (agent_model, analysis_model,
    etc.), then falls back to Azure-specific settings for backward compat.

    Args:
        purpose: One of "agent", "analysis", "summary", "synthesis".
        temperature: Optional per-call temperature override.

    Returns:
        Tuple of (model instance, model config)
    """
    # Provider-agnostic settings (preferred)
    purpose_map = {
        "agent": settings.agent_model,
        "analysis": settings.analysis_model,
        "summary": settings.summary_model,
        "synthesis": settings.synthesis_model,
    }

    # Legacy Azure-specific settings (backward compat)
    azure_map = {
        "agent": settings.azure_agent_deployment,
        "analysis": settings.azure_analysis_deployment,
        "summary": settings.azure_summary_deployment,
        "synthesis": settings.azure_synthesis_deployment,
    }

    model_name = purpose_map.get(purpose, "") or azure_map.get(purpose, "")
    if model_name:
        provider = settings.active_provider or "azure"
        desc = f"{provider} {model_name}"
        chain = _build_purpose_chain(model_name, provider, desc)
    else:
        chain = None
    return get_fallback_manager().get_model(temperature=temperature, chain=chain)


def get_model_with_fallback(
    temperature: float | None = None,
    purpose: str | None = None,
) -> tuple[BaseChatModel, ModelConfig]:
    """Get a model with automatic fallback support.

    This is the main entry point for getting an LLM model.
    It automatically handles fallback to alternative models.

    Always uses the global fallback manager so that failure tracking
    state (rate-limited providers, etc.) is preserved across calls.

    Args:
        temperature: Optional per-call temperature override. If None, uses the
            manager's default temperature from config.
        purpose: Optional purpose for model routing. One of "agent",
            "analysis", "summary", "synthesis". If set and a model is
            configured for this purpose, that model is tried first.

    Returns:
        Tuple of (model instance, model config)
    """
    if purpose:
        return get_model_for_purpose(purpose, temperature)
    return get_fallback_manager().get_model(temperature=temperature)
