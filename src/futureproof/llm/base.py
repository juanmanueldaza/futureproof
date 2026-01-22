"""Base LLM provider interface.

Defines the abstract interface that all LLM providers must implement,
enabling swappable backends through Dependency Inversion.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Standardized LLM response.

    Provides a consistent interface regardless of the underlying LLM provider.
    """

    content: str
    raw_response: Any = None
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)


class LLMError(Exception):
    """Base exception for LLM errors."""

    pass


class LLMConnectionError(LLMError):
    """Raised when connection to LLM fails."""

    pass


class LLMResponseError(LLMError):
    """Raised when LLM returns invalid response."""

    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Implements the Dependency Inversion Principle - high-level modules
    depend on this abstraction, not concrete implementations.

    To add a new provider:
    1. Create a new class that extends LLMProvider
    2. Implement invoke() and model_name property
    3. Register in LLMFactory.PROVIDERS
    """

    @abstractmethod
    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.3,
        api_key: str | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            model: Model name or identifier
            temperature: Sampling temperature (0-1)
            api_key: API key for the provider
        """
        ...

    @abstractmethod
    def invoke(self, prompt: str) -> LLMResponse:
        """Send prompt to LLM and get response.

        Args:
            prompt: The prompt text

        Returns:
            LLMResponse with standardized content

        Raises:
            LLMError: If invocation fails
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        pass
