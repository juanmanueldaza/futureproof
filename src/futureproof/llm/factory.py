"""LLM provider factory.

Centralizes provider instantiation and configuration.
"""

from typing import Literal

from ..config import settings
from .base import LLMProvider
from .gemini import GeminiProvider

ProviderType = Literal["gemini"]


class LLMFactory:
    """Factory for creating LLM providers.

    Centralizes provider instantiation and configuration.
    New providers can be added by:
    1. Creating a new provider class implementing LLMProvider
    2. Registering it in PROVIDERS dict
    """

    PROVIDERS: dict[str, type[LLMProvider]] = {
        "gemini": GeminiProvider,
    }

    @classmethod
    def create(
        cls,
        provider: ProviderType | None = None,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> LLMProvider:
        """Create an LLM provider instance.

        Args:
            provider: Provider type. Defaults to config setting.
            model: Model name. Defaults to provider's default.
            temperature: Sampling temperature.

        Returns:
            Configured LLMProvider instance

        Raises:
            ValueError: If provider type is unknown
        """
        provider_type = provider or settings.llm_provider or "gemini"

        if provider_type not in cls.PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider_type}. Available: {list(cls.PROVIDERS.keys())}"
            )

        provider_class = cls.PROVIDERS[provider_type]
        return provider_class(model=model, temperature=temperature)


def get_llm(temperature: float = 0.3) -> LLMProvider:
    """Get default LLM provider.

    Backwards-compatible function that replaces old utils/llm.py function.

    Args:
        temperature: Sampling temperature

    Returns:
        Configured LLMProvider instance
    """
    return LLMFactory.create(temperature=temperature)
