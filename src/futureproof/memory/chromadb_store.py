"""Base ChromaDB store with shared lazy-init, query, and stats logic.

Both CareerKnowledgeStore and EpisodicStore share the same ChromaDB
boilerplate (lazy client/collection, query iteration, get-by-filter).
This base class extracts that shared pattern.
"""

import logging
from pathlib import Path
from typing import Any

from .embeddings import get_embedding_function

logger = logging.getLogger(__name__)


class ChromaDBStore:
    """Base class for ChromaDB-backed stores.

    Provides lazy-initialized client/collection and shared helpers
    for querying, adding, and counting documents.
    """

    collection_name: str = ""
    collection_description: str = ""

    def __init__(self, persist_dir: Path | None = None) -> None:
        from futureproof.memory.checkpointer import get_data_dir

        if persist_dir is None:
            persist_dir = get_data_dir() / "episodic"

        self.persist_dir = persist_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = None
        self._collection = None

    @property
    def client(self):
        """Lazy-load ChromaDB client."""
        if self._client is None:
            try:
                import chromadb  # type: ignore[import-not-found]

                self._client = chromadb.PersistentClient(path=str(self.persist_dir))
                logger.info("ChromaDB initialized at %s", self.persist_dir)
            except ImportError:
                logger.warning("ChromaDB not installed.")
                raise
        return self._client

    @property
    def collection(self):
        """Get or create the collection."""
        if self._collection is None:
            embedding_fn = get_embedding_function()
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": self.collection_description},
                embedding_function=embedding_fn,  # type: ignore[arg-type]
            )
        return self._collection

    def _add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Add documents to the collection."""
        self.collection.add(ids=ids, documents=documents, metadatas=metadatas)  # type: ignore[arg-type]

    def _query(
        self,
        query: str,
        limit: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Query the collection and return (id, document, metadata) tuples."""
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,  # type: ignore[arg-type]
        )

        items = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                doc = results["documents"][0][i] if results["documents"] else ""
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                items.append((doc_id, doc, dict(meta)))
        return items

    def _get_by_filter(self, where: dict[str, Any]) -> list[str]:
        """Get document IDs matching a filter."""
        results = self.collection.get(where=where)
        return results["ids"] if results["ids"] else []

    def _count_by_values(
        self,
        field: str,
        values: list[str],
    ) -> dict[str, int]:
        """Count documents for each value of a metadata field."""
        counts = {}
        for value in values:
            ids = self._get_by_filter({field: value})
            counts[value] = len(ids)
        return counts
