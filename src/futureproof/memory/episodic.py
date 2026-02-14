"""Episodic memory for long-term storage of decisions and experiences.

Uses ChromaDB for semantic search over past decisions, interactions,
and career milestones. This enables the agent to recall relevant
past experiences when making recommendations.

Example uses:
- "Remember when I rejected that Stripe offer?" -> Recalls the decision context
- "What companies have I applied to?" -> Searches past job applications
- "Why did I pivot to backend?" -> Finds career transition reasoning
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .chromadb_store import ChromaDBStore

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
        return self.content

    def to_metadata(self) -> dict[str, Any]:
        """Convert to ChromaDB metadata format."""
        return {
            "memory_type": self.memory_type.value,
            "context": self.context,
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
        reserved = {"memory_type", "context", "timestamp"}
        return cls(
            id=id,
            memory_type=MemoryType(metadata.get("memory_type", "decision")),
            content=document,
            context=metadata.get("context", ""),
            timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.now().isoformat())),
            metadata={k: v for k, v in metadata.items() if k not in reserved},
        )


class EpisodicStore(ChromaDBStore):
    """ChromaDB-backed store for episodic memories.

    Provides semantic search over past decisions and experiences.
    """

    collection_name = "career_memories"
    collection_description = "Career decisions and experiences"

    def __init__(self, persist_dir: Path | None = None) -> None:
        super().__init__(persist_dir)

    def remember(self, memory: EpisodicMemory) -> str:
        """Store a new episodic memory."""
        self._add(
            ids=[memory.id],
            documents=[memory.to_document()],
            metadatas=[memory.to_metadata()],
        )
        logger.info("Stored memory: %s (%s)", memory.id, memory.memory_type.value)
        return memory.id

    def recall(
        self,
        query: str,
        limit: int = 5,
        memory_type: MemoryType | None = None,
    ) -> list[EpisodicMemory]:
        """Search for relevant memories."""
        where = None
        if memory_type:
            where = {"memory_type": memory_type.value}

        results = self._query(query, limit=limit, where=where)
        return [EpisodicMemory.from_chromadb(id, doc, meta) for id, doc, meta in results]

    def stats(self) -> dict[str, Any]:
        """Get statistics about the episodic store."""
        return {
            "total_memories": self.collection.count(),
            "by_type": self._count_by_values("memory_type", [mt.value for mt in MemoryType]),
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
    """Get the global episodic store instance."""
    global _store
    if _store is None:
        _store = EpisodicStore()
    return _store
