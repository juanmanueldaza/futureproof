"""Career knowledge base for RAG-based retrieval.

Provides semantic search over career documents (LinkedIn, Portfolio, Assessment).
Unlike EpisodicStore (for decisions/experiences), this stores factual career data
that can be queried by the agent instead of loading full documents into context.

Architecture: Database-first — gatherers produce Section tuples (name, content)
that are indexed directly to ChromaDB via index_sections(). No intermediate files.
"""

import logging
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

from .chromadb_store import ChromaDBStore
from .chunker import MarkdownChunker, Section

logger = logging.getLogger(__name__)


class KnowledgeSource(Enum):
    """Sources of career knowledge."""

    LINKEDIN = "linkedin"
    PORTFOLIO = "portfolio"
    ASSESSMENT = "assessment"  # CliftonStrengths


class CareerKnowledgeStore(ChromaDBStore):
    """ChromaDB-backed store for career knowledge RAG.

    Uses a separate collection from EpisodicStore to keep
    factual career data distinct from episodic memories.
    """

    collection_name = "career_knowledge"

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

    def index_sections(
        self,
        source: KnowledgeSource,
        sections: list[Section],
    ) -> list[str]:
        """Index pre-labeled sections directly (no header parsing).

        Each section's name becomes chunk metadata. Content is split
        by size only via chunk_section().

        Uses batch indexing — chunks are sent to ChromaDB in groups of 100.

        Args:
            source: Knowledge source
            sections: List of Section(name, content) tuples

        Returns:
            List of chunk IDs created
        """
        if not sections:
            logger.warning("No sections for source: %s", source.value)
            return []

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, str]] = []

        chunk_idx = 0
        for section in sections:
            chunks = self.chunker.chunk_section(section)
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                ids.append(chunk_id)
                documents.append(chunk.content)
                metadatas.append({
                    "source": source.value,
                    "section": section.name,
                    "chunk_index": str(chunk_idx),
                })
                chunk_idx += 1

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

    def _fetch_sorted_docs(
        self,
        source: KnowledgeSource,
        excluded_sections: frozenset[str] = frozenset(),
        excluded_prefixes: tuple[str, ...] = (),
    ) -> str:
        """Fetch chunks for a source, optionally filter, sort, and join."""
        results = self.collection.get(
            where={"source": source.value},
            include=["documents", "metadatas"],
        )

        docs = results["documents"]
        metas = results["metadatas"]
        if not docs or not metas:
            return ""

        pairs = list(zip(docs, metas))

        if excluded_sections or excluded_prefixes:
            pairs = [
                (doc, meta) for doc, meta in pairs
                if str(meta.get("section", "")) not in excluded_sections
                and not (
                    excluded_prefixes
                    and str(meta.get("section", "")).startswith(excluded_prefixes)
                )
            ]
            if not pairs:
                return ""

        def _sort_key(pair: tuple) -> int:
            idx = pair[1].get("chunk_index", 0)
            return int(idx) if isinstance(idx, (int, float, str)) else 0

        pairs.sort(key=_sort_key)
        return "\n\n".join(doc for doc, _ in pairs)

    def get_all_content(self, source: KnowledgeSource) -> str:
        """Retrieve all chunks for a source and join them in order."""
        return self._fetch_sorted_docs(source)

    def get_filtered_content(
        self,
        source: KnowledgeSource,
        excluded_sections: frozenset[str] = frozenset(),
        excluded_prefixes: tuple[str, ...] = (),
    ) -> str:
        """Retrieve chunks for a source, excluding specified sections."""
        return self._fetch_sorted_docs(source, excluded_sections, excluded_prefixes)

    def search(
        self,
        query: str,
        limit: int = 5,
        sources: list[KnowledgeSource] | None = None,
        section: str | None = None,
        excluded_sections: frozenset[str] = frozenset(),
        excluded_prefixes: tuple[str, ...] = (),
    ) -> list[dict[str, Any]]:
        """Semantic search across career knowledge.

        Args:
            query: Search query
            limit: Maximum results
            sources: Optional source filter
            section: Optional section filter (exact match)
            excluded_sections: Section names to exclude (exact match)
            excluded_prefixes: Section name prefixes to exclude

        Returns:
            List of result dicts with content, source, section, metadata
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

        reserved = {"source", "section", "chunk_index"}
        items: list[dict[str, Any]] = []
        for _id, doc, meta in results:
            sec = str(meta.get("section", ""))
            if needs_filtering:
                if sec in excluded_sections:
                    continue
                if excluded_prefixes and sec.startswith(excluded_prefixes):
                    continue
            items.append({
                "content": doc,
                "source": meta.get("source", "portfolio"),
                "section": sec,
                "metadata": {k: v for k, v in meta.items() if k not in reserved},
            })

        return items[:limit]

    def clear_source(self, source: KnowledgeSource) -> int:
        """Clear all chunks from a source (before re-indexing)."""
        ids = self.get_ids_by_filter({"source": source.value})
        if ids:
            self.delete_by_ids(ids)
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
