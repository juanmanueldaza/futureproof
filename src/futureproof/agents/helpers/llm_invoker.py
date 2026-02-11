"""LLM invocation helper with consistent error handling.

Consolidates the repeated try/except LLM invocation pattern
across orchestrator nodes.
"""

from typing import Any


class LLMInvoker:
    """Invokes LLM with consistent error handling.

    Consolidates the repeated pattern:
        try:
            response = llm.invoke(prompt)
            return {result_key: response.content}
        except Exception as e:
            return {"error": f"Operation failed: {e}"}

    Usage:
        invoker = LLMInvoker()
        result = invoker.invoke(prompt, "analysis", "Analysis")
    """

    def __init__(self, temperature: float = 0.3) -> None:
        """Initialize the LLM invoker.

        Args:
            temperature: LLM temperature setting (0.0-1.0)
        """
        self.temperature = temperature

    def invoke(
        self,
        prompt: str,
        result_key: str,
        error_prefix: str = "Operation",
    ) -> dict[str, Any]:
        """Invoke LLM and return result dict.

        Args:
            prompt: The prompt to send to the LLM
            result_key: Key to use for successful response in result dict
            error_prefix: Prefix for error messages (e.g., "Analysis", "Advice")

        Returns:
            Dict with either {result_key: content} on success
            or {"error": message} on failure
        """
        from ...llm.fallback import get_model_with_fallback

        try:
            model, _config = get_model_with_fallback()
            response = model.invoke(prompt)
            content = (
                response.content if isinstance(response.content, str) else str(response.content)
            )
            return {result_key: content}
        except Exception as e:
            return {"error": f"{error_prefix} failed: {e}"}


# Default invoker instance
default_invoker = LLMInvoker()
