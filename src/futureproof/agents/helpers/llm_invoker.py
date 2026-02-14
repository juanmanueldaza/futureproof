"""LLM invocation helper with consistent error handling."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Max retry attempts — matches the default fallback chain length (4 models)
_MAX_ATTEMPTS = 4


def invoke_llm(
    prompt: str,
    result_key: str,
    error_prefix: str = "Operation",
) -> dict[str, Any]:
    """Invoke LLM with automatic fallback on rate limits and model errors.

    Retries with the next model in the fallback chain when a recoverable
    error (429 rate limit, 404 model not found, etc.) is encountered.

    Args:
        prompt: The prompt to send to the LLM
        result_key: Key to use for successful response in result dict
        error_prefix: Prefix for error messages (e.g., "Analysis", "Advice")

    Returns:
        Dict with either {result_key: content} on success
        or {"error": message} on failure
    """
    from ...llm.fallback import get_fallback_manager, get_model_with_fallback

    manager = get_fallback_manager()
    last_error: Exception | None = None
    model_desc = "unknown"

    for attempt in range(_MAX_ATTEMPTS):
        try:
            model, config = get_model_with_fallback(purpose="analysis")
            model_desc = config.description
            response = model.invoke(prompt)
            content = (
                response.content if isinstance(response.content, str) else str(response.content)
            )
            return {result_key: content}
        except Exception as e:
            last_error = e
            if manager.handle_error(e) and attempt < _MAX_ATTEMPTS - 1:
                logger.warning(
                    "%s: %s failed (%s), trying next model",
                    error_prefix,
                    model_desc,
                    type(e).__name__,
                )
                continue
            break

    return {"error": f"{error_prefix} failed: {last_error}"}
