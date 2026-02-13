"""LangGraph InMemoryStore for cross-thread episodic memory.

Provides semantic search over memories at the agent runtime level.
Works alongside ChromaDB persistence in episodic.py — tools dual-write
to both stores so that InMemoryStore provides fast runtime access
while ChromaDB provides persistence across restarts.
"""

import logging

from langgraph.store.memory import InMemoryStore

from futureproof.config import settings

logger = logging.getLogger(__name__)

_store: InMemoryStore | None = None


def _create_store() -> InMemoryStore:
    """Create an InMemoryStore with semantic search embeddings."""
    try:
        from langchain.embeddings import init_embeddings

        if settings.azure_openai_api_key and settings.azure_embedding_deployment:
            embeddings = init_embeddings(
                "azure_openai:text-embedding-3-small",
                azure_deployment=settings.azure_embedding_deployment,
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            dims = 1536
        else:
            # No embeddings available — use store without semantic search
            logger.warning(
                "Azure OpenAI not configured. Store will not support search. "
                "Set AZURE_OPENAI_API_KEY and AZURE_EMBEDDING_DEPLOYMENT."
            )
            return InMemoryStore()

        return InMemoryStore(index={"embed": embeddings, "dims": dims})

    except Exception:
        logger.exception("Failed to initialize embeddings for InMemoryStore")
        return InMemoryStore()


def get_memory_store() -> InMemoryStore:
    """Get the global InMemoryStore singleton.

    Returns:
        InMemoryStore with semantic search (if embeddings available)
    """
    global _store
    if _store is None:
        _store = _create_store()
    return _store
