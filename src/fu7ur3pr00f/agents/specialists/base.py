"""Base class for specialist agents.

All specialist agents inherit from this base class to ensure:
- Consistent interface (can_handle, process)
- Shared knowledge base access (ChromaDB)
- LLM-powered responses via the fallback manager
- Unified error handling
"""

import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeResult:
    """A single result from knowledge base search."""

    content: str
    metadata: dict[str, Any]
    score: float | None = None


@dataclass
class MemoryResult:
    """A single episodic memory result."""

    content: str
    event_type: str
    timestamp: float | None = None
    score: float | None = None


class BaseAgent(ABC):
    """Abstract base class for all specialist agents.

    Subclasses must implement:
    - name: Agent identifier
    - description: Human-readable description
    - system_prompt: Focused system prompt for this specialist
    - can_handle(): Intent matching logic

    The process() method is provided — it builds context from ChromaDB,
    constructs a prompt, and calls the LLM.
    """

    _knowledge_store = None
    _episodic_store = None
    _store_lock = threading.Lock()

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier (e.g., 'coach', 'founder')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of agent's purpose."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for this specialist's LLM calls.

        Should define the agent's persona, focus areas, and response style.
        Will be augmented with user profile and knowledge base context at runtime.
        """
        ...

    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """Check if this agent can handle the request."""
        ...

    async def process(self, context: dict[str, Any]) -> str:
        """Process request via LLM with knowledge base context.

        Builds a prompt from:
        1. The specialist's system_prompt
        2. Relevant career data from ChromaDB
        3. User profile (if available)
        4. The user's query

        Then calls the LLM and returns the response.
        """
        query = context.get("query", "")
        user_profile = context.get("user_profile", {})

        # Gather context from knowledge base
        kb_context = self._gather_context(query)

        # Build the full prompt
        profile_text = self._format_profile(user_profile)
        full_system = self._build_system_prompt(profile_text, kb_context)

        # Call LLM
        try:
            response = self._call_llm(full_system, query)
        except Exception as e:
            logger.exception("LLM call failed in %s agent", self.name)
            response = (
                f"I encountered an error processing your request: {e}\n\n"
                "Try rephrasing your question, or use the main chat "
                "(without /multi) for full tool access."
            )

        # Apply values filter if enabled
        from fu7ur3pr00f.agents.values import ValuesContext, apply_values_filter

        return apply_values_filter(response, context=ValuesContext())

    def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """Call the LLM with system + user messages.

        Uses the analysis model from the fallback manager for higher
        quality reasoning (same model used for CV generation and analysis).
        """
        from fu7ur3pr00f.llm.fallback import get_model_with_fallback

        model, config = get_model_with_fallback(purpose="analysis")
        logger.info("%s agent using: %s", self.name, config.description)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        result = model.invoke(messages)
        return str(result.content)

    def _gather_context(self, query: str) -> str:
        """Search knowledge base for relevant career data."""
        results = self.search_knowledge(query, limit=8)
        if not results:
            return "No career data available. The user should run /gather first."

        parts = []
        for r in results:
            source = r.metadata.get("source", "unknown")
            section = r.metadata.get("section", "")
            header = f"[{source}" + (f" / {section}]" if section else "]")
            parts.append(f"{header}\n{r.content}")

        return "\n\n---\n\n".join(parts)

    def _format_profile(self, user_profile: dict) -> str:
        """Format user profile for prompt injection."""
        if not user_profile:
            # Try loading from disk
            try:
                from fu7ur3pr00f.memory.profile import load_profile

                profile = load_profile()
                summary = profile.summary()
                if summary != "No profile information available.":
                    return summary
            except Exception:
                pass
            return "No profile configured yet."
        # If dict provided, format key fields
        parts = []
        for key in ("name", "current_role", "target_roles", "skills", "goals"):
            if key in user_profile and user_profile[key]:
                parts.append(
                    f"**{key.replace('_', ' ').title()}:** {user_profile[key]}"
                )
        return "\n".join(parts) if parts else "No profile configured yet."

    def _build_system_prompt(self, profile: str, kb_context: str) -> str:
        """Assemble the full system prompt with context."""
        return (
            f"{self.system_prompt}\n\n"
            f"## User Profile\n{profile}\n\n"
            f"## Career Data (from knowledge base)\n{kb_context}\n\n"
            "## Instructions\n"
            "- Use ONLY the career data above — do not invent facts\n"
            "- Be specific and actionable, referencing the user's actual experience\n"
            "- If data is missing, say so and suggest running /gather\n"
        )

    # ── Knowledge base access ────────────────────────────────────────────

    @classmethod
    def _get_knowledge_store(cls):
        """Lazy-load the knowledge store singleton."""
        if cls._knowledge_store is None:
            with cls._store_lock:
                if cls._knowledge_store is None:
                    from fu7ur3pr00f.memory.knowledge import CareerKnowledgeStore

                    cls._knowledge_store = CareerKnowledgeStore()
        return cls._knowledge_store

    @classmethod
    def _get_episodic_store(cls):
        """Lazy-load the episodic store singleton."""
        if cls._episodic_store is None:
            with cls._store_lock:
                if cls._episodic_store is None:
                    from fu7ur3pr00f.memory.episodic import EpisodicStore

                    cls._episodic_store = EpisodicStore()
        return cls._episodic_store

    def search_knowledge(
        self,
        query: str,
        limit: int = 5,
        source: str | None = None,
    ) -> list[KnowledgeResult]:
        """Search career knowledge base.

        Args:
            query: Search query (embedded for similarity search)
            limit: Max results
            source: Optional filter by source (e.g., "linkedin", "github")

        Returns:
            List of KnowledgeResult with content and metadata
        """
        try:
            store = self._get_knowledge_store()
            # CareerKnowledgeStore.search() returns list[dict] with
            # "content", "metadata" keys
            results = store.search(query, limit=limit)

            return [
                KnowledgeResult(
                    content=r.get("content", r.get("document", "")),
                    metadata=r.get("metadata", {}),
                    score=r.get("score"),
                )
                for r in results
            ]
        except Exception:
            logger.debug("Knowledge search failed", exc_info=True)
            return []

    def recall_memories(
        self,
        query: str,
        event_type: str | None = None,
        limit: int = 5,
    ) -> list[MemoryResult]:
        """Recall episodic memories."""
        try:
            store = self._get_episodic_store()
            # EpisodicStore.recall() returns list[EpisodicMemory]
            memories = store.recall(query, limit=limit)

            return [
                MemoryResult(
                    content=str(getattr(m, "content", m)),
                    event_type=str(getattr(m, "memory_type", "unknown")),
                    timestamp=getattr(m, "timestamp", None),
                )
                for m in memories
            ]
        except Exception:
            logger.debug("Memory recall failed", exc_info=True)
            return []
