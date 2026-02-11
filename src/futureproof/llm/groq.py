"""Groq LLM provider.

Implements the LLMProvider interface for Groq's fast inference API.
"""

from typing import Any

from langchain_groq import ChatGroq
from pydantic import SecretStr

from ..config import settings
from .base import LLMError, LLMProvider, LLMResponse


class GroqProvider(LLMProvider):
    """Groq LLM provider.

    Supports Groq models through the langchain-groq integration.
    Groq provides fast inference for open-source models like Llama and Mixtral.
    """

    # Available models - extend this dict to add new models
    MODELS: dict[str, str] = {
        "llama-3.3-70b": "llama-3.3-70b-versatile",
        "llama-3.1-8b": "llama-3.1-8b-instant",
        "mixtral": "mixtral-8x7b-32768",
    }

    DEFAULT_MODEL = "llama-3.3-70b"

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.3,
        api_key: str | None = None,
    ) -> None:
        """Initialize Groq provider.

        Args:
            model: Model name (short key or full name). Defaults to config or DEFAULT_MODEL
            temperature: Sampling temperature (0-1)
            api_key: API key. Defaults to config
        """
        self._model_key = model or settings.llm_model or self.DEFAULT_MODEL
        self._model_name = self.MODELS.get(self._model_key, self._model_key)
        self._temperature = temperature
        self._api_key = api_key or settings.groq_api_key

        self._client = ChatGroq(
            model=self._model_name,
            api_key=SecretStr(self._api_key),
            temperature=self._temperature,
        )

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        return self._model_name

    def invoke(self, prompt: str) -> LLMResponse:
        """Send prompt to Groq.

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
            raise LLMError(f"Groq invocation failed: {e}") from e

    def _parse_content(self, content: Any) -> str:
        """Parse Groq response content to string.

        Args:
            content: Raw response content

        Returns:
            Parsed string content
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts) if parts else str(content)
        return str(content)
