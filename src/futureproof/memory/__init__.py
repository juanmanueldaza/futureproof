"""Memory module for FutureProof persistent state management.

Three-tier memory architecture:
- Conversations: LangGraph SqliteSaver for conversation state
- Profile: YAML-based user identity and goals
- ChromaDB: Episodic memory (decisions, applications) + career knowledge RAG
"""

from futureproof.memory.checkpointer import get_checkpointer

# Chunker for markdown processing
from futureproof.memory.chunker import MarkdownChunk, MarkdownChunker

# Episodic memory (lazy import to avoid ChromaDB startup cost)
from futureproof.memory.episodic import (
    EpisodicMemory,
    EpisodicStore,
    MemoryType,
    get_episodic_store,
    remember_application,
    remember_decision,
)

# Knowledge base for RAG
from futureproof.memory.knowledge import (
    CareerKnowledgeStore,
    KnowledgeChunk,
    KnowledgeSource,
    get_knowledge_store,
)
from futureproof.memory.profile import UserProfile, load_profile, save_profile

__all__ = [
    # Checkpointer
    "get_checkpointer",
    # Profile
    "UserProfile",
    "load_profile",
    "save_profile",
    # Chunker
    "MarkdownChunker",
    "MarkdownChunk",
    # Episodic Memory
    "EpisodicStore",
    "EpisodicMemory",
    "MemoryType",
    "get_episodic_store",
    "remember_decision",
    "remember_application",
    # Knowledge Base
    "CareerKnowledgeStore",
    "KnowledgeChunk",
    "KnowledgeSource",
    "get_knowledge_store",
]
