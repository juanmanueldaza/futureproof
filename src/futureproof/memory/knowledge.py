"""Career knowledge base for RAG-based retrieval.

Provides semantic search over career documents (LinkedIn, Portfolio, Assessment).
Unlike EpisodicStore (for decisions/experiences), this stores factual career data
that can be queried by the agent instead of loading full documents into context.

Architecture: Database-first — gatherers index content directly to ChromaDB
via index_content(). No intermediate markdown files on disk.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .chromadb_store import ChromaDBStore
from .chunker import MarkdownChunker

logger = logging.getLogger(__name__)


class KnowledgeSource(Enum):
    """Sources of career knowledge."""

    LINKEDIN = "linkedin"
    PORTFOLIO = "portfolio"
    ASSESSMENT = "assessment"  # CliftonStrengths


@dataclass
class KnowledgeChunk:
    """A chunk of career knowledge with metadata."""

    id: str
    content: str
    source: KnowledgeSource
    section: str  # e.g., "Repositories", "Experience", "Skills"
    metadata: dict[str, Any] = field(default_factory=dict)
    indexed_at: datetime = field(default_factory=datetime.now)

    def to_document(self) -> str:
        """Convert to searchable document string."""
        return self.content

    def to_metadata(self) -> dict[str, str]:
        """Convert to ChromaDB metadata format (all values must be strings)."""
        return {
            "source": self.source.value,
            "section": self.section,
            "indexed_at": self.indexed_at.isoformat(),
            **{k: str(v) for k, v in self.metadata.items()},
        }

    @classmethod
    def from_chromadb(
        cls,
        id: str,
        document: str,
        metadata: dict[str, Any],
    ) -> "KnowledgeChunk":
        """Create from ChromaDB query result."""
        source_str = metadata.get("source", "portfolio")
        try:
            source = KnowledgeSource(source_str)
        except ValueError:
            source = KnowledgeSource.PORTFOLIO

        reserved = {"source", "section", "indexed_at"}
        return cls(
            id=id,
            content=document,
            source=source,
            section=metadata.get("section", ""),
            indexed_at=datetime.fromisoformat(
                metadata.get("indexed_at", datetime.now().isoformat())
            ),
            metadata={k: v for k, v in metadata.items() if k not in reserved},
        )


class CareerKnowledgeStore(ChromaDBStore):
    """ChromaDB-backed store for career knowledge RAG.

    Uses a separate collection from EpisodicStore to keep
    factual career data distinct from episodic memories.
    """

    collection_name = "career_knowledge"
    collection_description = "Career knowledge for RAG retrieval"

    def __init__(
        self,
        persist_dir: Path | None = None,
        chunker: MarkdownChunker | None = None,
    ) -> None:
        super().__init__(persist_dir)
        self._chunker = chunker

    @property
    def chunker(self) -> MarkdownChunker:
        """Get the markdown chunker (lazy initialization)."""
        if self._chunker is None:
            from futureproof.config import settings

            self._chunker = MarkdownChunker(
                max_tokens=settings.knowledge_chunk_max_tokens,
                min_tokens=settings.knowledge_chunk_min_tokens,
            )
        return self._chunker

    def _index_document(
        self,
        source: KnowledgeSource,
        content: str,
        section: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Index a single document chunk."""
        chunk = KnowledgeChunk(
            id=str(uuid.uuid4()),
            content=content,
            source=source,
            section=section,
            metadata=metadata or {},
        )

        self._add(
            ids=[chunk.id],
            documents=[chunk.to_document()],
            metadatas=[chunk.to_metadata()],
        )

        logger.debug("Indexed chunk: %s (%s/%s)", chunk.id, source.value, section)
        return chunk.id

    def index_content(
        self,
        source: KnowledgeSource,
        content: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Chunk and index raw markdown content directly (no file I/O).

        Uses batch indexing — all chunks are sent to ChromaDB in a single
        ``collection.add()`` call, triggering one batch embedding request
        instead of one per chunk.

        Args:
            source: Knowledge source
            content: Raw markdown content to index
            extra_metadata: Additional metadata to include with all chunks

        Returns:
            List of chunk IDs created
        """
        if not content.strip():
            logger.warning("Empty content for source: %s", source.value)
            return []

        chunks = self.chunker.chunk(content)

        # Build batch arrays
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, str]] = []

        for idx, chunk in enumerate(chunks):
            kc = KnowledgeChunk(
                id=str(uuid.uuid4()),
                content=chunk.content,
                source=source,
                section=chunk.section_name or "general",
                metadata={"chunk_index": idx, **(extra_metadata or {})},
            )
            ids.append(kc.id)
            documents.append(kc.to_document())
            metadatas.append(kc.to_metadata())

        # Single batch add — one embedding API call for all chunks
        self._add(ids=ids, documents=documents, metadatas=metadatas)

        logger.info("Indexed %d chunks for %s (batch)", len(ids), source.value)
        return ids

    def get_all_content(self, source: KnowledgeSource) -> str:
        """Retrieve all chunks for a source and join them in order.

        Uses metadata-based retrieval (not semantic search) to reconstruct
        the full content for a source. Chunks are sorted by chunk_index.

        Args:
            source: Knowledge source to retrieve

        Returns:
            Combined content string, or empty string if no data
        """
        results = self.collection.get(
            where={"source": source.value},
            include=["documents", "metadatas"],
        )

        docs = results["documents"]
        metas = results["metadatas"]
        if not docs or not metas:
            return ""

        # Sort by chunk_index if available, else preserve order
        def _sort_key(pair: tuple) -> int:
            idx = pair[1].get("chunk_index", 0)
            return int(idx) if isinstance(idx, (int, float, str)) else 0

        pairs = list(zip(docs, metas))
        sorted_docs = sorted(pairs, key=_sort_key)
        return "\n\n".join(doc for doc, _ in sorted_docs)

    def search(
        self,
        query: str,
        limit: int = 5,
        sources: list[KnowledgeSource] | None = None,
    ) -> list[KnowledgeChunk]:
        """Semantic search across career knowledge."""
        where = None
        if sources:
            if len(sources) == 1:
                where = {"source": sources[0].value}
            else:
                where = {"source": {"$in": [s.value for s in sources]}}

        results = self._query(query, limit=limit, where=where)
        return [KnowledgeChunk.from_chromadb(id, doc, meta) for id, doc, meta in results]

    def clear_source(self, source: KnowledgeSource) -> int:
        """Clear all chunks from a source (before re-indexing)."""
        ids = self._get_by_filter({"source": source.value})
        if ids:
            self.collection.delete(ids=ids)
            logger.info("Cleared %d chunks from %s", len(ids), source.value)
            return len(ids)
        return 0

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the knowledge store."""
        return self._get_stats(
            total_label="total_chunks",
            group_field="source",
            group_values=[src.value for src in KnowledgeSource],
            group_label="by_source",
        )


# =============================================================================
# Module-level store instance
# =============================================================================

_store: CareerKnowledgeStore | None = None


def get_knowledge_store() -> CareerKnowledgeStore:
    """Get the global knowledge store instance."""
    global _store
    if _store is None:
        _store = CareerKnowledgeStore()
    return _store
