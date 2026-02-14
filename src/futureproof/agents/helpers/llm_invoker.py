"""LLM invocation helper with consistent error handling."""

from typing import Any


def invoke_llm(
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
        model, _config = get_model_with_fallback(purpose="analysis")
        response = model.invoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        return {result_key: content}
    except Exception as e:
        return {"error": f"{error_prefix} failed: {e}"}
