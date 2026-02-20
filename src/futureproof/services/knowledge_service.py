"""Knowledge indexing service.

Orchestrates indexing of career documents into the knowledge base.
Database-first: content is indexed directly to ChromaDB, no intermediate files.
"""

import logging
import time
from typing import Any

from ..memory.knowledge import (
    CareerKnowledgeStore,
    KnowledgeSource,
    get_knowledge_store,
)

logger = logging.getLogger(__name__)

# Sections excluded from analysis/CV prompts — social/network data
# searchable via the agent's search_career_knowledge tool (RAG).
_EXCLUDED_SECTIONS: frozenset[str] = frozenset(
    {
        "Connections",
        "Messages",
        "Network",
        "Job Applications",
        "Posts",
    }
)

# Dynamic sub-section prefixes to exclude (unpredictable names).
# "Conversation:" — titled threads: "Conversation: John Smith"
# "Conversation " — untitled threads: "Conversation 2-M2FkOTFi..."
# "Sponsored" — sponsored InMail: "Sponsored Conversation"
_EXCLUDED_PREFIXES: tuple[str, ...] = (
    "Conversation:",
    "Conversation ",
    "Sponsored",
)


class KnowledgeService:
    """Service for managing the career knowledge base.

    Responsibilities:
    - Index career content directly (no file I/O for portfolio/assessment)
    - Index LinkedIn files after CLI generates them
    - Provide search interface for agent tools
    - Retrieve all content for a source (replaces file-based data loading)
    """

    def __init__(self, store: CareerKnowledgeStore | None = None) -> None:
        self._store = store

    @property
    def store(self) -> CareerKnowledgeStore:
        """Get the knowledge store (lazy initialization)."""
        if self._store is None:
            self._store = get_knowledge_store()
        return self._store

    def index_content(
        self,
        source: KnowledgeSource,
        content: str,
        verbose: bool = False,
    ) -> int:
        """Index raw content directly into the knowledge base.

        Clears existing chunks for source first (incremental update).

        Args:
            source: The knowledge source
            content: Raw markdown content to index
            verbose: If True, print progress to console

        Returns:
            Count of chunks indexed
        """
        t0 = time.monotonic()

        # Get existing chunk IDs BEFORE indexing new content
        old_ids = self.store._get_by_filter({"source": source.value})

        # Index new content first — if embedding fails, old data is preserved
        chunk_ids = self.store.index_content(source=source, content=content)

        # Only delete old chunks AFTER successful indexing
        if old_ids:
            self.store.collection.delete(ids=old_ids)
            logger.info("Cleared %d old chunks for %s", len(old_ids), source.value)

        elapsed = time.monotonic() - t0

        if verbose:
            from ..chat.ui import display_indexing_result

            display_indexing_result(source.value, len(chunk_ids), elapsed)

        logger.info("Indexed %d chunks for %s in %.1fs", len(chunk_ids), source.value, elapsed)
        return len(chunk_ids)

    def index_all(self, verbose: bool = False) -> dict[str, int]:
        """Report existing chunk counts for all sources.

        All sources are indexed at gather time via index_content().

        Args:
            verbose: If True, print progress to console

        Returns:
            Dict mapping source names to chunk counts
        """
        results: dict[str, int] = {}
        stats = self.store.get_stats()

        for source in KnowledgeSource:
            count = stats.get("by_source", {}).get(source.value, 0)
            results[source.value] = count

        return results

    def search(
        self,
        query: str,
        limit: int = 5,
        sources: list[str] | None = None,
        section: str | None = None,
        include_social: bool = False,
    ) -> list[dict[str, Any]]:
        """Search knowledge base.

        Args:
            query: Search query
            limit: Maximum results
            sources: Optional list of source names to filter by
            section: Optional section name to filter by (e.g., "Connections")
            include_social: If True, include social/network data
                (messages, connections, posts). Default False — focuses on
                career content (experience, skills, education, etc.)

        Returns:
            List of result dicts with content, source, section
        """
        source_enums = None
        if sources:
            source_enums = []
            for s in sources:
                try:
                    source_enums.append(KnowledgeSource(s.lower()))
                except ValueError:
                    logger.warning("Unknown source: %s", s)

        # When searching for career content, exclude social/network sections
        # to avoid messages and connections drowning out profile data.
        # Explicit section filter overrides this (user knows what they want).
        excluded_sections: frozenset[str] = frozenset()
        excluded_prefixes: tuple[str, ...] = ()
        if not include_social and section is None:
            excluded_sections = _EXCLUDED_SECTIONS
            excluded_prefixes = _EXCLUDED_PREFIXES

        chunks = self.store.search(
            query,
            limit=limit,
            sources=source_enums,
            section=section,
            excluded_sections=excluded_sections,
            excluded_prefixes=excluded_prefixes,
        )

        return [
            {
                "content": chunk.content,
                "source": chunk.source.value,
                "section": chunk.section,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]

    def get_all_content(self) -> dict[str, str]:
        """Get all career content from the knowledge base.

        Returns:
            Dict with keys like 'linkedin_data', 'portfolio_data', etc.
            Only includes sources that have indexed content.
        """
        data: dict[str, str] = {}
        source_keys = {
            KnowledgeSource.LINKEDIN: "linkedin_data",
            KnowledgeSource.PORTFOLIO: "portfolio_data",
            KnowledgeSource.ASSESSMENT: "assessment_data",
        }
        for source, key in source_keys.items():
            content = self.store.get_all_content(source)
            if content:
                data[key] = content
        return data

    def get_filtered_content(
        self,
        excluded_sections: frozenset[str] | None = None,
        excluded_prefixes: tuple[str, ...] | None = None,
    ) -> dict[str, str]:
        """Get career content with irrelevant sections excluded.

        LinkedIn is filtered by excluding social/network sections.
        Portfolio and Assessment are always returned fully (small data).

        Args:
            excluded_sections: Sections to exclude. Defaults to social data.
            excluded_prefixes: Prefixes to exclude. Defaults to conversations.

        Returns:
            Dict with keys 'linkedin_data', 'portfolio_data', 'assessment_data'.
        """
        if excluded_sections is None:
            excluded_sections = _EXCLUDED_SECTIONS
        if excluded_prefixes is None:
            excluded_prefixes = _EXCLUDED_PREFIXES

        data: dict[str, str] = {}

        # LinkedIn — filtered (exclude Connections, Messages, etc.)
        linkedin = self.store.get_filtered_content(
            KnowledgeSource.LINKEDIN,
            excluded_sections,
            excluded_prefixes,
        )
        if linkedin:
            data["linkedin_data"] = linkedin

        # Portfolio & Assessment — full (small data, always relevant)
        for source, key in [
            (KnowledgeSource.PORTFOLIO, "portfolio_data"),
            (KnowledgeSource.ASSESSMENT, "assessment_data"),
        ]:
            content = self.store.get_all_content(source)
            if content:
                data[key] = content

        return data

    def get_stats(self) -> dict[str, Any]:
        """Get knowledge base statistics."""
        return self.store.get_stats()
