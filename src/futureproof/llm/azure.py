"""Azure OpenAI LLM provider.

Implements the LLMProvider interface for Azure OpenAI / AI Foundry models.
"""

from langchain_openai import AzureChatOpenAI

from ..config import settings
from .base import LLMError, LLMProvider, LLMResponse


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI LLM provider.

    Supports Azure OpenAI models through the langchain-openai integration.
    Requires AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and
    AZURE_CHAT_DEPLOYMENT to be configured.
    """

    DEFAULT_MODEL = "gpt-4.1"

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.3,
        api_key: str | None = None,
    ) -> None:
        from pydantic import SecretStr

        self._model_name = model or settings.azure_chat_deployment or self.DEFAULT_MODEL
        self._temperature = temperature
        self._api_key = api_key or settings.azure_openai_api_key

        self._client = AzureChatOpenAI(
            azure_deployment=self._model_name,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=SecretStr(self._api_key),
            api_version=settings.azure_openai_api_version,
            temperature=self._temperature,
        )

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        return self._model_name

    def invoke(self, prompt: str) -> LLMResponse:
        """Send prompt to Azure OpenAI.

        Args:
            prompt: The prompt text

        Returns:
            LLMResponse with content

        Raises:
            LLMError: If invocation fails
        """
        try:
            response = self._client.invoke(prompt)
            content = (
                response.content if isinstance(response.content, str) else str(response.content)
            )

            return LLMResponse(
                content=content,
                raw_response=response,
                model=self._model_name,
            )
        except Exception as e:
            raise LLMError(f"Azure OpenAI invocation failed: {e}") from e
