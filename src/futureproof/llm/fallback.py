"""LLM fallback chain for resilient model selection.

Provides automatic fallback between Azure OpenAI models when rate limits
or other errors are encountered. This ensures the chat remains usable
even when the primary model is temporarily unavailable.
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


# Default fallback chain - ordered by preference
DEFAULT_FALLBACK_CHAIN: list[ModelConfig] = [
    ModelConfig("azure", "gpt-4.1", "Azure GPT-4.1"),
    ModelConfig("azure", "gpt-4o", "Azure GPT-4o"),
    ModelConfig("azure", "gpt-4.1-mini", "Azure GPT-4.1 Mini"),
    ModelConfig("azure", "gpt-4o-mini", "Azure GPT-4o Mini"),
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

    def _create_model(self, config: ModelConfig, temperature: float | None = None) -> BaseChatModel:
        """Create a LangChain chat model from config using init_chat_model.

        Args:
            config: Model configuration to instantiate
            temperature: Optional per-call temperature override. If None,
                uses the manager's default temperature.
        """
        from langchain.chat_models import init_chat_model

        if config.provider != "azure":
            raise ValueError(f"Unknown provider: {config.provider}")
        model_provider = "azure_openai"

        effective_temperature = temperature if temperature is not None else self._temperature
        kwargs: dict[str, Any] = {
            "temperature": effective_temperature,
            "streaming": True,
        }

        kwargs["azure_deployment"] = config.model
        kwargs["azure_endpoint"] = settings.azure_openai_endpoint
        kwargs["api_version"] = settings.azure_openai_api_version
        kwargs["api_key"] = settings.azure_openai_api_key

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
            if settings.has_azure and self._model_key(config) not in self._failed_models
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
            if settings.has_azure and self._model_key(config) not in self._failed_models
        ]

        if not available:
            # Reset failed models and try again
            logger.warning("All models failed, resetting failure state")
            self._failed_models.clear()
            available = [
                config
                for config in effective_chain
                if settings.has_azure and self._model_key(config) not in self._failed_models
            ]

        if not available:
            raise RuntimeError(
                "No LLM models available. Please configure "
                "AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT."
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


def _build_purpose_chain(deployment: str, description: str) -> list[ModelConfig]:
    """Build a fallback chain with a purpose-specific model prepended.

    The purpose model is tried first; if it fails, the default chain
    models are tried in order (skipping any duplicate).
    """
    purpose_model = ModelConfig("azure", deployment, description)
    return [purpose_model] + [c for c in DEFAULT_FALLBACK_CHAIN if c.model != deployment]


def get_model_for_purpose(
    purpose: str,
    temperature: float | None = None,
) -> tuple[BaseChatModel, ModelConfig]:
    """Get a model optimized for a specific purpose.

    Builds a purpose-specific fallback chain by prepending the configured
    deployment for that purpose. If no deployment is configured, falls
    back to the default chain.

    Args:
        purpose: One of "agent", "analysis", "summary".
        temperature: Optional per-call temperature override.

    Returns:
        Tuple of (model instance, model config)
    """
    deployment_map = {
        "agent": (settings.azure_agent_deployment, "Agent"),
        "analysis": (settings.azure_analysis_deployment, "Analysis"),
        "summary": (settings.azure_summary_deployment, "Summary"),
    }

    deployment, desc = deployment_map.get(purpose, ("", ""))
    chain = _build_purpose_chain(deployment, desc) if deployment else None
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
            "analysis", "summary". If set and a deployment is configured
            for this purpose, that model is tried first.

    Returns:
        Tuple of (model instance, model config)
    """
    if purpose:
        return get_model_for_purpose(purpose, temperature)
    return get_fallback_manager().get_model(temperature=temperature)
