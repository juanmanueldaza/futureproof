"""Google Gemini LLM provider.

Implements the LLMProvider interface for Google's Gemini models.
"""

from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import settings
from .base import LLMError, LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider.

    Supports Gemini models through the langchain-google-genai integration.
    New models can be added to MODELS dict without code changes (Open-Closed).
    """

    # Available models - extend this dict to add new models
    MODELS: dict[str, str] = {
        "gemini-2-flash": "gemini-2.0-flash",
        "gemini-3-flash": "gemini-3-flash-preview",
        "gemini-3-pro": "gemini-3-pro-preview",
    }

    DEFAULT_MODEL = "gemini-3-flash"

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.3,
        api_key: str | None = None,
    ) -> None:
        """Initialize Gemini provider.

        Args:
            model: Model name (short key or full name). Defaults to config or DEFAULT_MODEL
            temperature: Sampling temperature (0-1)
            api_key: API key. Defaults to config
        """
        self._model_key = model or settings.llm_model or self.DEFAULT_MODEL
        self._model_name = self.MODELS.get(self._model_key, self._model_key)
        self._temperature = temperature
        self._api_key = api_key or settings.gemini_api_key

        self._client = ChatGoogleGenerativeAI(
            model=self._model_name,
            google_api_key=self._api_key,
            temperature=self._temperature,
        )

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        return self._model_name

    def invoke(self, prompt: str) -> LLMResponse:
        """Send prompt to Gemini.

        Args:
            prompt: The prompt text

        Returns:
            LLMResponse with content

        Raises:
            LLMError: If invocation fails
        """
        try:
            response = self._client.invoke(prompt)
            content = self._parse_content(response.content)

            return LLMResponse(
                content=content,
                raw_response=response,
                model=self._model_name,
            )
        except Exception as e:
            raise LLMError(f"Gemini invocation failed: {e}") from e

    def _parse_content(self, content: Any) -> str:
        """Parse Gemini response content to string.

        Handles various response formats from different Gemini versions.

        Args:
            content: Raw response content

        Returns:
            Parsed string content
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            # Gemini 3 returns [{'type': 'text', 'text': '...'}]
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts) if parts else str(content)
        return str(content)
