"""LLM provider abstraction layer.

Provides a unified interface for interacting with different LLM providers,
following the Open-Closed and Dependency Inversion principles.
"""

from .azure import AzureOpenAIProvider
from .base import LLMError, LLMProvider, LLMResponse
from .factory import LLMFactory, get_llm
from .fallback import FallbackLLMManager, get_fallback_manager, get_model_with_fallback
from .gemini import GeminiProvider

__all__ = [
    "AzureOpenAIProvider",
    "FallbackLLMManager",
    "GeminiProvider",
    "LLMError",
    "LLMFactory",
    "LLMProvider",
    "LLMResponse",
    "get_fallback_manager",
    "get_llm",
    "get_model_with_fallback",
]
