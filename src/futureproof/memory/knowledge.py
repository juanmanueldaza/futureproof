"""Career knowledge base for RAG-based retrieval.

Provides semantic search over career documents (GitHub, GitLab, LinkedIn, Portfolio).
Unlike EpisodicStore (for decisions/experiences), this stores factual career data
that can be queried by the agent instead of loading full documents into context.

Architecture:
    ┌─────────────────────────────────────────┐
    │         Career Knowledge Base           │
    │  ┌─────────────────────────────────┐    │
    │  │         ChromaDB                 │    │
    │  │  ┌────────────────────────────┐  │    │
    │  │  │  career_knowledge          │  │    │
    │  │  │  (github, gitlab, linkedin │  │    │
    │  │  │   portfolio, assessment)   │  │    │
    │  │  └────────────────────────────┘  │    │
    │  └─────────────────────────────────┘    │
    └─────────────────────────────────────────┘
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .chunker import MarkdownChunker
from .embeddings import get_embedding_function

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
        return f"[{self.source.value}] {self.section}: {self.content}"

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
        # Extract content from document (remove prefix)
        content = document
        if ": " in document:
            # Remove "[source] section: " prefix if present
            parts = document.split(": ", 1)
            if len(parts) > 1:
                content = parts[1]

        source_str = metadata.get("source", "github")
        try:
            source = KnowledgeSource(source_str)
        except ValueError:
            source = KnowledgeSource.GITHUB

        return cls(
            id=id,
            content=content,
            source=source,
            section=metadata.get("section", ""),
            indexed_at=datetime.fromisoformat(
                metadata.get("indexed_at", datetime.now().isoformat())
            ),
            metadata={
                k: v for k, v in metadata.items() if k not in ("source", "section", "indexed_at")
            },
        )


class CareerKnowledgeStore:
    """ChromaDB-backed store for career knowledge RAG.

    Follows same pattern as EpisodicStore but for factual career data.
    Uses a separate collection to keep episodic and factual data distinct.
    """

    COLLECTION_NAME = "career_knowledge"

    def __init__(
        self,
        persist_dir: Path | None = None,
        chunker: MarkdownChunker | None = None,
    ) -> None:
        """Initialize the knowledge store.

        Args:
            persist_dir: Directory for ChromaDB persistence.
                        Defaults to ~/.futureproof/episodic/ (shared with episodic)
            chunker: MarkdownChunker instance (uses default if not provided)
        """
        from futureproof.memory.checkpointer import get_data_dir

        if persist_dir is None:
            persist_dir = get_data_dir() / "episodic"

        self.persist_dir = persist_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._chunker = chunker
        self._client = None
        self._collection = None

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

    @property
    def client(self):
        """Lazy-load ChromaDB client."""
        if self._client is None:
            try:
                import chromadb  # type: ignore[import-not-found]

                self._client = chromadb.PersistentClient(path=str(self.persist_dir))
                logger.info(f"ChromaDB knowledge store initialized at {self.persist_dir}")
            except ImportError:
                logger.warning("ChromaDB not installed. Knowledge base disabled.")
                raise
        return self._client

    @property
    def collection(self):
        """Get or create the knowledge collection."""
        if self._collection is None:
            embedding_fn = get_embedding_function()
            self._collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "Career knowledge for RAG retrieval"},
                embedding_function=embedding_fn,  # type: ignore[arg-type]
            )
        return self._collection

    def _index_document(
        self,
        source: KnowledgeSource,
        content: str,
        section: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Index a single document chunk.

        Args:
            source: Knowledge source (github, gitlab, etc.)
            content: The text content to index
            section: Section name (e.g., "Repositories", "Experience")
            metadata: Additional metadata

        Returns:
            The chunk ID
        """
        chunk = KnowledgeChunk(
            id=str(uuid.uuid4()),
            content=content,
            source=source,
            section=section,
            metadata=metadata or {},
        )

        self.collection.add(
            ids=[chunk.id],
            documents=[chunk.to_document()],
            metadatas=[chunk.to_metadata()],
        )

        logger.debug(f"Indexed chunk: {chunk.id} ({source.value}/{section})")
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
            logger.warning(f"File not found: {file_path}")
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

        logger.info(f"Indexed {len(chunk_ids)} chunks from {file_path.name}")
        return chunk_ids

    def search(
        self,
        query: str,
        limit: int = 5,
        sources: list[KnowledgeSource] | None = None,
    ) -> list[KnowledgeChunk]:
        """Semantic search across career knowledge.

        Args:
            query: Search query
            limit: Maximum results to return
            sources: Optional filter by sources

        Returns:
            List of matching chunks, ordered by relevance
        """
        where = None
        if sources:
            if len(sources) == 1:
                where = {"source": sources[0].value}
            else:
                where = {"source": {"$in": [s.value for s in sources]}}

        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,  # type: ignore[arg-type]
        )

        chunks = []
        if results["ids"] and results["ids"][0]:
            for i, id in enumerate(results["ids"][0]):
                doc = results["documents"][0][i] if results["documents"] else ""
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                chunks.append(KnowledgeChunk.from_chromadb(id, doc, dict(meta)))

        return chunks

    def clear_source(self, source: KnowledgeSource) -> int:
        """Clear all chunks from a source (before re-indexing).

        Args:
            source: The source to clear

        Returns:
            Number of chunks deleted
        """
        results = self.collection.get(
            where={"source": source.value},
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(f"Cleared {len(results['ids'])} chunks from {source.value}")
            return len(results["ids"])

        return 0

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the knowledge store.

        Returns:
            Dictionary with store statistics
        """
        total = self.collection.count()

        # Count by source
        source_counts = {}
        for src in KnowledgeSource:
            results = self.collection.get(
                where={"source": src.value},
            )
            source_counts[src.value] = len(results["ids"]) if results["ids"] else 0

        return {
            "total_chunks": total,
            "by_source": source_counts,
            "persist_dir": str(self.persist_dir),
        }


# =============================================================================
# Module-level store instance
# =============================================================================

_store: CareerKnowledgeStore | None = None


def get_knowledge_store() -> CareerKnowledgeStore:
    """Get the global knowledge store instance.

    Returns:
        CareerKnowledgeStore singleton
    """
    global _store
    if _store is None:
        _store = CareerKnowledgeStore()
    return _store
