"""LLM fallback chain for resilient model selection.

Provides automatic fallback between providers and models when rate limits
or other errors are encountered. This ensures the chat remains usable
even when primary providers are temporarily unavailable.

Supported providers:
- Azure: Azure OpenAI / AI Foundry ($200 free credits)
- Groq: Fast inference, 100k tokens/day per model
- Gemini: Google's models, 15 RPM / 1M tokens/day
- Cerebras: Extremely fast, free tier (https://cerebras.ai)
- SambaNova: Free tier with Llama 405B (https://sambanova.ai)
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

    provider: str
    model: str
    description: str

    def get_api_key(self) -> str:
        """Get the API key for this provider."""
        if self.provider == "azure":
            return settings.azure_openai_api_key
        elif self.provider == "groq":
            return settings.groq_api_key
        elif self.provider == "gemini":
            return settings.gemini_api_key
        elif self.provider == "cerebras":
            return settings.cerebras_api_key
        elif self.provider == "sambanova":
            return settings.sambanova_api_key
        return ""

    def is_available(self) -> bool:
        """Check if this model is available (has API key configured)."""
        if self.provider == "azure":
            return settings.has_azure
        return bool(self.get_api_key())


# Default fallback chain - ordered by preference
# Note: Check provider docs for current model availability
DEFAULT_FALLBACK_CHAIN: list[ModelConfig] = [
    # Primary: Azure OpenAI ($200 free credits, high quality)
    ModelConfig("azure", "gpt-4.1", "Azure GPT-4.1"),
    ModelConfig("azure", "gpt-4.1-mini", "Azure GPT-4.1 Mini"),
    # Fallback: Groq (100k TPD per model, very fast)
    ModelConfig("groq", "llama-3.3-70b-versatile", "Groq Llama 3.3 70B"),
    # Fallback 1: Groq Mixtral (separate 100k TPD quota)
    ModelConfig("groq", "mixtral-8x7b-32768", "Groq Mixtral 8x7B"),
    # Fallback 2: Groq smaller model (separate 100k TPD quota)
    ModelConfig("groq", "llama-3.1-8b-instant", "Groq Llama 8B"),
    # Fallback 3: Gemini 2.5 Flash (latest, fast)
    ModelConfig("gemini", "gemini-2.5-flash", "Gemini 2.5 Flash"),
    # Fallback 4: Gemini 2.0 Flash
    ModelConfig("gemini", "gemini-2.0-flash", "Gemini 2.0 Flash"),
    # Fallback 5: Gemini 3 Flash Preview
    ModelConfig("gemini", "gemini-3-flash-preview", "Gemini 3 Flash Preview"),
    # Fallback 6: Cerebras (extremely fast inference)
    ModelConfig("cerebras", "llama-3.3-70b", "Cerebras Llama 3.3 70B"),
    # Fallback 7: SambaNova 70B
    ModelConfig("sambanova", "Meta-Llama-3.1-70B-Instruct", "SambaNova Llama 3.1 70B"),
    # Fallback 8: SambaNova 405B (largest free model available!)
    ModelConfig("sambanova", "Meta-Llama-3.1-405B-Instruct", "SambaNova Llama 405B"),
]


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
        self._chain = fallback_chain or DEFAULT_FALLBACK_CHAIN
        self._temperature = temperature if temperature is not None else settings.llm_temperature
        self._failed_models: set[str] = set()
        self._current_model: ModelConfig | None = None

    def _model_key(self, config: ModelConfig) -> str:
        """Get a unique key for a model config."""
        return f"{config.provider}/{config.model}"

    def _is_fallback_error(self, error: Exception) -> bool:
        """Check if an exception should trigger a fallback to another model."""
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in self.FALLBACK_ERROR_INDICATORS)

    # Provider to init_chat_model model_provider mapping
    _PROVIDER_MAP: dict[str, str] = {
        "azure": "azure_openai",
        "groq": "groq",
        "gemini": "google_genai",
        "cerebras": "openai",
        "sambanova": "openai",
    }

    # OpenAI-compatible providers that need a custom base_url
    _BASE_URLS: dict[str, str] = {
        "cerebras": "https://api.cerebras.ai/v1",
        "sambanova": "https://api.sambanova.ai/v1",
    }

    def _create_model(self, config: ModelConfig) -> BaseChatModel:
        """Create a LangChain chat model from config using init_chat_model."""
        from langchain.chat_models import init_chat_model

        model_provider = self._PROVIDER_MAP.get(config.provider)
        if not model_provider:
            raise ValueError(f"Unknown provider: {config.provider}")

        kwargs: dict[str, Any] = {
            "temperature": self._temperature,
            "streaming": True,
        }

        if config.provider == "azure":
            kwargs["azure_deployment"] = config.model
            kwargs["azure_endpoint"] = settings.azure_openai_endpoint
            kwargs["api_version"] = settings.azure_openai_api_version
            kwargs["api_key"] = config.get_api_key()
        elif config.provider == "gemini":
            kwargs["google_api_key"] = config.get_api_key()
        else:
            kwargs["api_key"] = config.get_api_key()

        base_url = self._BASE_URLS.get(config.provider)
        if base_url:
            kwargs["base_url"] = base_url

        return init_chat_model(
            model=config.model,
            model_provider=model_provider,
            **kwargs,
        )

    def get_available_models(self) -> list[ModelConfig]:
        """Get list of available models (configured and not failed)."""
        return [
            config
            for config in self._chain
            if config.is_available() and self._model_key(config) not in self._failed_models
        ]

    def get_model(self) -> tuple[BaseChatModel, ModelConfig]:
        """Get the best available model.

        Returns:
            Tuple of (model instance, model config)

        Raises:
            RuntimeError: If no models are available
        """
        available = self.get_available_models()

        if not available:
            # Reset failed models and try again
            logger.warning("All models failed, resetting failure state")
            self._failed_models.clear()
            available = self.get_available_models()

        if not available:
            raise RuntimeError(
                "No LLM models available. Please configure "
                "AZURE_OPENAI_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY."
            )

        config = available[0]
        self._current_model = config

        logger.info(f"Using model: {config.description}")
        return self._create_model(config), config

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
            True if fallback should be attempted (rate limit, model unavailable, etc.),
            False if this is a different type of error that shouldn't trigger fallback
        """
        if self._is_fallback_error(error):
            self.mark_failed()
            remaining = len(self.get_available_models())
            if remaining > 0:
                logger.info(f"Model error detected, {remaining} fallback model(s) available")
                return True
            else:
                logger.warning("Model error detected, no fallback models available")
        return False

    def reset(self) -> None:
        """Reset all failure states."""
        self._failed_models.clear()
        self._current_model = None

    def get_status(self) -> dict[str, Any]:
        """Get current status of the fallback manager."""
        return {
            "current_model": self._current_model.description if self._current_model else None,
            "failed_models": list(self._failed_models),
            "available_models": [m.description for m in self.get_available_models()],
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


def get_model_with_fallback(
    temperature: float | None = None,
) -> tuple[BaseChatModel, ModelConfig]:
    """Get a model with automatic fallback support.

    This is the main entry point for getting an LLM model.
    It automatically handles fallback to alternative models.

    Args:
        temperature: Optional temperature override. If None, uses the
            global setting from the shared fallback manager.

    Returns:
        Tuple of (model instance, model config)
    """
    if temperature is not None:
        # Create a temporary manager with custom temperature
        manager = FallbackLLMManager(temperature=temperature)
        return manager.get_model()
    return get_fallback_manager().get_model()
