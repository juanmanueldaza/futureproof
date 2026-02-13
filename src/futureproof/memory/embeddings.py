"""Embedding functions for ChromaDB vector stores.

Provides cloud-based embeddings using Azure OpenAI instead of
slow local sentence-transformers. This significantly improves
knowledge base search latency from ~30s to ~1-2s.

Usage:
    from futureproof.memory.embeddings import get_embedding_function

    # In ChromaDB collection creation:
    collection = client.get_or_create_collection(
        name="my_collection",
        embedding_function=get_embedding_function(),
    )
"""

import logging
from typing import Any

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from futureproof.config import settings

logger = logging.getLogger(__name__)


class AzureOpenAIEmbeddingFunction(EmbeddingFunction[Documents]):
    """ChromaDB embedding function using Azure OpenAI.

    Uses text-embedding-3-small/large models which are:
    - Fast (cloud-based)
    - High quality (supports dimension reduction)
    - Covered by Azure free credits ($200)
    """

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.azure_openai_api_key
        self._endpoint = endpoint or settings.azure_openai_endpoint
        self._deployment = deployment or settings.azure_embedding_deployment
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

    # text-embedding-3-small/large max context is 8192 tokens (~2 chars/token)
    MAX_CHARS = 15000

    def _truncate(self, texts: list[str]) -> list[str]:
        """Truncate texts that exceed the model's context limit."""
        return [t[: self.MAX_CHARS] if len(t) > self.MAX_CHARS else t for t in texts]

    def __call__(self, input: Documents) -> Embeddings:
        """Generate embeddings for a list of documents."""
        if not input:
            return []

        try:
            docs: list[str] = list(input) if isinstance(input, list) else [input]
            response = self.client.embeddings.create(
                input=self._truncate(docs),
                model=self._deployment,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Azure OpenAI embedding failed: {e}")
            raise


class CachedEmbeddingFunction(EmbeddingFunction[Documents]):
    """Wrapper that adds in-memory caching to any embedding function.

    Useful for reducing API calls when the same text is embedded multiple times.
    """

    def __init__(
        self,
        base_function: EmbeddingFunction[Documents],
        max_cache_size: int = 1000,
    ) -> None:
        """Initialize the cached embedding function.

        Args:
            base_function: The underlying embedding function to cache
            max_cache_size: Maximum number of embeddings to cache
        """
        self._base = base_function
        self._cache: dict[str, Any] = {}  # Can be list[float] or numpy array
        self._max_size = max_cache_size

    def __call__(self, input: Documents) -> Embeddings:
        """Generate embeddings with caching.

        Args:
            input: List of text documents to embed

        Returns:
            List of embedding vectors
        """
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
            for idx, doc, emb in zip(uncached_indices, uncached_docs, new_embeddings):
                results[idx] = emb

                # Add to cache (evict oldest if full)
                if len(self._cache) >= self._max_size:
                    # Simple eviction: remove first item
                    first_key = next(iter(self._cache))
                    del self._cache[first_key]

                self._cache[doc] = emb

        return results  # type: ignore[return-value]


# Global embedding function instance
_embedding_function: EmbeddingFunction[Documents] | None = None


def get_embedding_function(use_cache: bool = True) -> EmbeddingFunction[Documents]:
    """Get the configured embedding function for ChromaDB.

    Returns Azure OpenAI embeddings if configured, otherwise falls back
    to ChromaDB's default (sentence-transformers, slower but works offline).

    Args:
        use_cache: Whether to wrap with caching (recommended)

    Returns:
        ChromaDB-compatible embedding function
    """
    global _embedding_function

    if _embedding_function is not None:
        return _embedding_function

    if settings.azure_openai_api_key and settings.azure_embedding_deployment:
        logger.info("Using Azure OpenAI embeddings")
        base: EmbeddingFunction[Documents] = AzureOpenAIEmbeddingFunction()
        if use_cache:
            _embedding_function = CachedEmbeddingFunction(base)
        else:
            _embedding_function = base
    else:
        logger.warning(
            "No embedding API configured. Using default embeddings (slow, local). "
            "Set AZURE_OPENAI_API_KEY and AZURE_EMBEDDING_DEPLOYMENT for faster performance."
        )
        # Return None to let ChromaDB use its default
        return None  # type: ignore[return-value]

    return _embedding_function


def clear_embedding_cache() -> None:
    """Clear the embedding cache and reset the global instance."""
    global _embedding_function
    _embedding_function = None
