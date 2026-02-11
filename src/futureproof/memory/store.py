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

        # Prefer Azure embeddings if configured, otherwise Gemini
        if settings.azure_openai_api_key and settings.azure_embedding_deployment:
            embeddings = init_embeddings(
                "azure_openai:text-embedding-3-small",
                azure_deployment=settings.azure_embedding_deployment,
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            dims = 1536
        elif settings.gemini_api_key:
            embeddings = init_embeddings(
                "google_genai:models/gemini-embedding-001",
                google_api_key=settings.gemini_api_key,
            )
            dims = 768
        else:
            # No embeddings available — use store without semantic search
            logger.warning("No embedding API keys configured. Store will not support search.")
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
