"""LLM provider abstraction layer.

Uses FallbackLLMManager for resilient model selection with automatic
fallback across multiple providers (Azure, Groq, Gemini, Cerebras, SambaNova).
"""

from .fallback import FallbackLLMManager, get_fallback_manager, get_model_with_fallback

__all__ = [
    "FallbackLLMManager",
    "get_fallback_manager",
    "get_model_with_fallback",
]
