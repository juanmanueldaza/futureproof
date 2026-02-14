"""Episodic memory for long-term storage of decisions and experiences.

Uses ChromaDB for semantic search over past decisions, interactions,
and career milestones. This enables the agent to recall relevant
past experiences when making recommendations.

Example uses:
- "Remember when I rejected that Stripe offer?" -> Recalls the decision context
- "What companies have I applied to?" -> Searches past job applications
- "Why did I pivot to backend?" -> Finds career transition reasoning

Architecture:
    ┌─────────────────────────────────────────┐
    │           Episodic Memory               │
    │  ┌─────────────────────────────────┐    │
    │  │         ChromaDB                 │    │
    │  │  ┌────────────────────────────┐  │    │
    │  │  │  career_decisions          │  │    │
    │  │  │  job_applications          │  │    │
    │  │  │  conversation_summaries    │  │    │
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

from .embeddings import get_embedding_function

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of episodic memories."""

    DECISION = "decision"  # Career decisions made
    APPLICATION = "application"  # Job applications
    CONVERSATION = "conversation"  # Conversation summaries
    MILESTONE = "milestone"  # Career milestones
    LEARNING = "learning"  # Skills learned or courses taken


@dataclass
class EpisodicMemory:
    """A single episodic memory entry."""

    id: str
    memory_type: MemoryType
    content: str
    context: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_document(self) -> str:
        """Convert to searchable document string."""
        return f"{self.content}. Context: {self.context}"

    def to_metadata(self) -> dict[str, Any]:
        """Convert to ChromaDB metadata format."""
        return {
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp.isoformat(),
            **{k: str(v) for k, v in self.metadata.items()},  # ChromaDB needs string values
        }

    @classmethod
    def from_chromadb(
        cls,
        id: str,
        document: str,
        metadata: dict[str, Any],
    ) -> "EpisodicMemory":
        """Create from ChromaDB query result."""
        # Parse content and context from document
        if ". Context: " in document:
            content, context = document.rsplit(". Context: ", 1)
        else:
            content = document
            context = ""

        return cls(
            id=id,
            memory_type=MemoryType(metadata.get("memory_type", "decision")),
            content=content,
            context=context,
            timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.now().isoformat())),
            metadata={k: v for k, v in metadata.items() if k not in ("memory_type", "timestamp")},
        )


class EpisodicStore:
    """ChromaDB-backed store for episodic memories.

    Provides semantic search over past decisions and experiences.
    """

    def __init__(self, persist_dir: Path | None = None) -> None:
        """Initialize the episodic store.

        Args:
            persist_dir: Directory for ChromaDB persistence.
                        Defaults to ~/.futureproof/episodic/
        """
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
                logger.info(f"ChromaDB initialized at {self.persist_dir}")
            except ImportError:
                logger.warning("ChromaDB not installed. Episodic memory disabled.")
                raise
        return self._client

    @property
    def collection(self):
        """Get or create the memories collection."""
        if self._collection is None:
            embedding_fn = get_embedding_function()
            self._collection = self.client.get_or_create_collection(
                name="career_memories",
                metadata={"description": "Career decisions and experiences"},
                embedding_function=embedding_fn,  # type: ignore[arg-type]
            )
        return self._collection

    def remember(self, memory: EpisodicMemory) -> str:
        """Store a new episodic memory.

        Args:
            memory: The memory to store

        Returns:
            The memory ID
        """
        self.collection.add(
            ids=[memory.id],
            documents=[memory.to_document()],
            metadatas=[memory.to_metadata()],
        )
        logger.info(f"Stored memory: {memory.id} ({memory.memory_type.value})")
        return memory.id

    def recall(
        self,
        query: str,
        limit: int = 5,
        memory_type: MemoryType | None = None,
    ) -> list[EpisodicMemory]:
        """Search for relevant memories.

        Args:
            query: Search query (semantic search)
            limit: Maximum results to return
            memory_type: Optional filter by memory type

        Returns:
            List of matching memories, ordered by relevance
        """
        where = None
        if memory_type:
            where = {"memory_type": memory_type.value}

        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,  # type: ignore[arg-type]
        )

        memories = []
        if results["ids"] and results["ids"][0]:
            for i, id in enumerate(results["ids"][0]):
                doc = results["documents"][0][i] if results["documents"] else ""
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                memories.append(EpisodicMemory.from_chromadb(id, doc, dict(meta)))

        return memories

    def stats(self) -> dict[str, Any]:
        """Get statistics about the episodic store.

        Returns:
            Dictionary with store statistics
        """
        count = self.collection.count()

        # Count by type
        type_counts = {}
        for mem_type in MemoryType:
            results = self.collection.get(
                where={"memory_type": mem_type.value},
            )
            type_counts[mem_type.value] = len(results["ids"]) if results["ids"] else 0

        return {
            "total_memories": count,
            "by_type": type_counts,
            "persist_dir": str(self.persist_dir),
        }


# =============================================================================
# Convenience functions for creating common memory types
# =============================================================================


def remember_decision(
    decision: str,
    context: str,
    outcome: str | None = None,
    alternatives_considered: list[str] | None = None,
) -> EpisodicMemory:
    """Create a decision memory.

    Args:
        decision: The decision that was made
        context: Context/reasoning behind the decision
        outcome: Optional outcome of the decision
        alternatives_considered: Other options that were considered

    Returns:
        EpisodicMemory ready to be stored
    """
    return EpisodicMemory(
        id=str(uuid.uuid4()),
        memory_type=MemoryType.DECISION,
        content=decision,
        context=context,
        metadata={
            "outcome": outcome or "",
            "alternatives": ",".join(alternatives_considered or []),
        },
    )


def remember_application(
    company: str,
    role: str,
    status: str,
    notes: str = "",
) -> EpisodicMemory:
    """Create a job application memory.

    Args:
        company: Company name
        role: Role applied for
        status: Application status (applied, interviewing, rejected, offer, etc.)
        notes: Additional notes

    Returns:
        EpisodicMemory ready to be stored
    """
    content = f"Applied to {company} for {role} position"
    context = f"Status: {status}. {notes}" if notes else f"Status: {status}"

    return EpisodicMemory(
        id=str(uuid.uuid4()),
        memory_type=MemoryType.APPLICATION,
        content=content,
        context=context,
        metadata={
            "company": company,
            "role": role,
            "status": status,
        },
    )


# =============================================================================
# Module-level store instance
# =============================================================================

_store: EpisodicStore | None = None


def get_episodic_store() -> EpisodicStore:
    """Get the global episodic store instance.

    Returns:
        EpisodicStore singleton
    """
    global _store
    if _store is None:
        _store = EpisodicStore()
    return _store
