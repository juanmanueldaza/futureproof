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

    def index_content(
        self,
        source: KnowledgeSource,
        content: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Chunk and index raw markdown content directly (no file I/O).

        Uses batch indexing — chunks are sent to ChromaDB in groups of 100
        to avoid overwhelming the embedding API while still being efficient.

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
                section=chunk.category or "general",
                metadata={"chunk_index": idx, **(extra_metadata or {})},
            )
            ids.append(kc.id)
            documents.append(kc.to_document())
            metadatas.append(kc.to_metadata())

        # Batch add — split into groups to avoid overwhelming the embedding API
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            self._add(
                ids=ids[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end],
            )

        logger.info("Indexed %d chunks for %s", len(ids), source.value)
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

    def get_filtered_content(
        self,
        source: KnowledgeSource,
        excluded_sections: frozenset[str] = frozenset(),
        excluded_prefixes: tuple[str, ...] = (),
    ) -> str:
        """Retrieve chunks for a source, excluding specified sections.

        Uses metadata-only retrieval (no embeddings) followed by Python-side
        filtering. For collections <1000 chunks this is sub-millisecond.

        Handles two types of exclusion:
        - Exact section names (e.g., "Connections") via set lookup
        - Section name prefixes (e.g., "Conversation:") via str.startswith()

        Args:
            source: Knowledge source to retrieve
            excluded_sections: Section names to exclude (exact match)
            excluded_prefixes: Section name prefixes to exclude

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

        # Filter out excluded sections
        filtered: list[tuple] = []
        for doc, meta in zip(docs, metas):
            section = str(meta.get("section", ""))
            if section in excluded_sections:
                continue
            if excluded_prefixes and section.startswith(excluded_prefixes):
                continue
            filtered.append((doc, meta))

        if not filtered:
            return ""

        # Sort by chunk_index
        def _sort_key(pair: tuple) -> int:
            idx = pair[1].get("chunk_index", 0)
            return int(idx) if isinstance(idx, (int, float, str)) else 0

        sorted_docs = sorted(filtered, key=_sort_key)
        return "\n\n".join(doc for doc, _ in sorted_docs)

    def search(
        self,
        query: str,
        limit: int = 5,
        sources: list[KnowledgeSource] | None = None,
        section: str | None = None,
        excluded_sections: frozenset[str] = frozenset(),
        excluded_prefixes: tuple[str, ...] = (),
    ) -> list[KnowledgeChunk]:
        """Semantic search across career knowledge.

        Args:
            query: Search query
            limit: Maximum results
            sources: Optional source filter
            section: Optional section filter (exact match)
            excluded_sections: Section names to exclude (exact match)
            excluded_prefixes: Section name prefixes to exclude
        """
        conditions: list[dict] = []
        if sources:
            if len(sources) == 1:
                conditions.append({"source": sources[0].value})
            else:
                conditions.append({"source": {"$in": [s.value for s in sources]}})
        if section:
            conditions.append({"section": section})

        where = None
        if len(conditions) == 1:
            where = conditions[0]
        elif len(conditions) > 1:
            where = {"$and": conditions}

        needs_filtering = bool(excluded_sections or excluded_prefixes)
        fetch_limit = limit * 3 if needs_filtering else limit

        results = self._query(query, limit=fetch_limit, where=where)
        chunks = [KnowledgeChunk.from_chromadb(id, doc, meta) for id, doc, meta in results]

        if needs_filtering:
            chunks = [
                c for c in chunks
                if c.section not in excluded_sections
                and not (excluded_prefixes and c.section.startswith(excluded_prefixes))
            ]

        return chunks[:limit]

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
