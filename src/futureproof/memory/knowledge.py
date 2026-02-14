"""Career knowledge base for RAG-based retrieval.

Provides semantic search over career documents (GitHub, GitLab, LinkedIn, Portfolio).
Unlike EpisodicStore (for decisions/experiences), this stores factual career data
that can be queried by the agent instead of loading full documents into context.
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

    GITHUB = "github"
    GITLAB = "gitlab"
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
        source_str = metadata.get("source", "github")
        try:
            source = KnowledgeSource(source_str)
        except ValueError:
            source = KnowledgeSource.GITHUB

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

    def index_markdown_file(
        self,
        source: KnowledgeSource,
        file_path: Path,
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Parse and index a markdown file by sections.

        Args:
            source: Knowledge source (github, gitlab, etc.)
            file_path: Path to the markdown file
            extra_metadata: Additional metadata to include with all chunks

        Returns:
            List of chunk IDs created
        """
        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            return []

        content = file_path.read_text()
        chunks = self.chunker.chunk(content)

        chunk_ids = []
        for chunk in chunks:
            section = chunk.section_name or file_path.stem
            metadata = {
                "file": file_path.name,
                "parent_section": chunk.parent_section,
                **(extra_metadata or {}),
            }

            chunk_id = self._index_document(
                source=source,
                content=chunk.content,
                section=section,
                metadata=metadata,
            )
            chunk_ids.append(chunk_id)

        logger.info("Indexed %d chunks from %s", len(chunk_ids), file_path.name)
        return chunk_ids

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
        return {
            "total_chunks": self.collection.count(),
            "by_source": self._count_by_values("source", [src.value for src in KnowledgeSource]),
            "persist_dir": str(self.persist_dir),
        }


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
