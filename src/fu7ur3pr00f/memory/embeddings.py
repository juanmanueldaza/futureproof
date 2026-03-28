"""Embedding functions for ChromaDB vector stores.

Supports multiple providers: Azure OpenAI, OpenAI, FutureProof proxy,
Ollama (local), and ChromaDB's default sentence-transformers fallback.

Usage:
    from fu7ur3pr00f.memory.embeddings import get_embedding_function

    # In ChromaDB collection creation:
    collection = client.get_or_create_collection(
        name="my_collection",
        embedding_function=get_embedding_function(),
    )
"""

import logging
import threading
from abc import abstractmethod
from typing import Any

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from fu7ur3pr00f.config import settings
from fu7ur3pr00f.constants import MAX_EMBEDDING_CACHE_SIZE

logger = logging.getLogger(__name__)


class _TruncatingEmbeddingFunction(EmbeddingFunction[Documents]):
    """Base class for OpenAI-family embedding functions with truncation."""

    MAX_CHARS = 15000

    def _truncate(self, texts: list[str]) -> list[str]:
        """Truncate texts that exceed the model's context limit."""
        return [t[: self.MAX_CHARS] if len(t) > self.MAX_CHARS else t for t in texts]

    @property
    @abstractmethod
    def client(self) -> Any:
        """The embedding client. Subclasses must override."""
        raise NotImplementedError

    @property
    def _model_name(self) -> str:
        """The model name to use for embeddings. Subclasses must override."""
        raise NotImplementedError

    def __call__(self, input: Documents) -> Embeddings:
        """Generate embeddings for a list of documents."""
        if not input:
            return []

        try:
            docs: list[str] = list(input) if isinstance(input, list) else [input]
            response = self.client.embeddings.create(
                input=self._truncate(docs),
                model=self._model_name,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error("%s embedding failed: %s", type(self).__name__, e)
            raise


class AzureOpenAIEmbeddingFunction(_TruncatingEmbeddingFunction):
    """ChromaDB embedding function using Azure OpenAI."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.azure_openai_api_key
        self._endpoint = endpoint or settings.azure_openai_endpoint
        self._deployment = (
            deployment
            or settings.azure_embedding_deployment
            or "text-embedding-3-small"
        )
        self._api_version = api_version or settings.azure_openai_api_version
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load the Azure OpenAI client."""
        if self._client is None:
            from openai import AzureOpenAI

            self._client = AzureOpenAI(
                api_key=self._api_key,
                azure_endpoint=self._endpoint,
                api_version=self._api_version,
            )
            logger.debug("Azure OpenAI embedding client initialized")
        return self._client

    @property
    def _model_name(self) -> str:
        return self._deployment


class OpenAIEmbeddingFunction(_TruncatingEmbeddingFunction):
    """ChromaDB embedding function using OpenAI or OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str | None = None,
        model: str = "text-embedding-3-small",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load the OpenAI client."""
        if self._client is None:
            from openai import OpenAI

            kwargs: dict[str, Any] = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = OpenAI(**kwargs)
            logger.debug("OpenAI embedding client initialized")
        return self._client

    @property
    def _model_name(self) -> str:
        return self._model


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    """ChromaDB embedding function using Ollama local models."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load the Ollama client."""
        if self._client is None:
            import httpx

            self._client = httpx.Client(base_url=self._base_url, timeout=60.0)
            logger.debug("Ollama embedding client initialized")
        return self._client

    def __call__(self, input: Documents) -> Embeddings:
        """Generate embeddings for a list of documents."""
        if not input:
            return []

        try:
            docs: list[str] = list(input) if isinstance(input, list) else [input]
            embeddings: list[list[float]] = []
            for doc in docs:
                response = self.client.post(
                    "/api/embed",
                    json={"model": self._model, "input": doc},
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embeddings"][0])
            return embeddings  # type: ignore[return-value]
        except Exception as e:
            logger.error("Ollama embedding failed: %s", e)
            raise


class CachedEmbeddingFunction(EmbeddingFunction[Documents]):
    """Wrapper that adds in-memory caching to any embedding function."""

    def __init__(
        self,
        base_function: EmbeddingFunction[Documents],
        max_cache_size: int = MAX_EMBEDDING_CACHE_SIZE,
    ) -> None:
        self._base = base_function
        self._cache: dict[str, Any] = {}  # Can be list[float] or numpy array
        self._max_size = max_cache_size

    def __call__(self, input: Documents) -> Embeddings:
        """Generate embeddings with caching."""
        if not input:
            return []

        results: list[Any] = []
        uncached_docs: list[str] = []
        uncached_indices: list[int] = []

        # Check cache for each document
        for i, doc in enumerate(input):
            if doc in self._cache:
                results.append(self._cache[doc])
            else:
                results.append(None)  # Placeholder
                uncached_docs.append(doc)
                uncached_indices.append(i)

        # Embed uncached documents
        if uncached_docs:
            new_embeddings = self._base(uncached_docs)

            # Update results and cache
            for idx, doc, emb in zip(
                uncached_indices, uncached_docs, new_embeddings, strict=True
            ):  # noqa: E501
                results[idx] = emb

                # Add to cache (evict oldest if full)
                if len(self._cache) >= self._max_size:
                    first_key = next(iter(self._cache))
                    del self._cache[first_key]

                self._cache[doc] = emb

        return results  # type: ignore[return-value]


# Global embedding function instance
_embedding_function: EmbeddingFunction[Documents] | None = None
_embed_lock = threading.Lock()


def get_embedding_function() -> EmbeddingFunction[Documents]:
    """Get the configured embedding function for ChromaDB.

    Auto-detects the active provider and returns the appropriate
    embedding function wrapped with caching. Falls back to ChromaDB's
    default (sentence-transformers) if no provider is configured.
    """
    global _embedding_function

    if _embedding_function is not None:
        return _embedding_function

    with _embed_lock:
        if _embedding_function is not None:
            return _embedding_function

        provider = settings.active_provider
        model = settings.embedding_model
        base: EmbeddingFunction[Documents] | None = None

        if provider == "azure":
            logger.info("Using Azure OpenAI embeddings")
            base = AzureOpenAIEmbeddingFunction()

        elif provider in ("openai", "fu7ur3pr00f"):
            api_key = (
                settings.fu7ur3pr00f_proxy_key
                if provider == "fu7ur3pr00f"
                else settings.openai_api_key
            )
            base_url = (
                settings.fu7ur3pr00f_proxy_url if provider == "fu7ur3pr00f" else None
            )
            logger.info("Using %s embeddings", provider)
            base = OpenAIEmbeddingFunction(
                api_key=api_key,
                base_url=base_url,
                model=model or "text-embedding-3-small",
            )

        elif provider == "ollama":
            logger.info("Using Ollama local embeddings")
            base = OllamaEmbeddingFunction(
                base_url=settings.ollama_base_url,
                model=model or "nomic-embed-text",
            )

        if base is None:
            logger.warning(
                "No embedding provider configured. Using default embeddings "
                "(slow, local). Set an LLM provider for faster performance."
            )
            return None  # type: ignore[return-value]

        _embedding_function = CachedEmbeddingFunction(base)
        return _embedding_function
