"""Knowledge indexing service.

Orchestrates indexing of career documents into the knowledge base.
Database-first: content is indexed directly to ChromaDB, no intermediate files.
LinkedIn is the exception (external CLI writes files, which are read and indexed).
"""

import logging
from pathlib import Path
from typing import Any

from ..memory.knowledge import (
    CareerKnowledgeStore,
    KnowledgeSource,
    get_knowledge_store,
)

logger = logging.getLogger(__name__)


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
        cleared = self.store.clear_source(source)
        if cleared > 0:
            logger.info("Cleared %d existing chunks for %s", cleared, source.value)

        chunk_ids = self.store.index_content(source=source, content=content)

        if verbose:
            from ..utils.console import console

            console.print(f"  [dim]Indexed {len(chunk_ids)} chunks for {source.value}[/dim]")

        logger.info("Indexed %d chunks for %s", len(chunk_ids), source.value)
        return len(chunk_ids)

    def index_files(
        self,
        source: KnowledgeSource,
        files: list[Path],
        verbose: bool = False,
    ) -> int:
        """Index files into the knowledge base (for LinkedIn CLI output).

        Clears existing chunks for source first.

        Args:
            source: The knowledge source
            files: List of markdown file paths to index
            verbose: If True, print progress to console

        Returns:
            Count of chunks indexed
        """
        cleared = self.store.clear_source(source)
        if cleared > 0:
            logger.info("Cleared %d existing chunks for %s", cleared, source.value)

        total_chunks = 0
        for file_path in files:
            if not file_path.exists():
                logger.debug("File not found, skipping: %s", file_path)
                continue

            chunk_ids = self.store.index_markdown_file(
                source=source,
                file_path=file_path,
            )
            total_chunks += len(chunk_ids)

            if verbose:
                from ..utils.console import console

                console.print(f"  [dim]Indexed {len(chunk_ids)} chunks from {file_path.name}[/dim]")

        logger.info("Indexed %d chunks for %s", total_chunks, source.value)
        return total_chunks

    def index_source(self, source: KnowledgeSource, verbose: bool = False) -> int:
        """Index a source from processed files (LinkedIn only).

        For portfolio/assessment, use index_content() instead — they are
        indexed directly at gather time.

        Args:
            source: The knowledge source to index
            verbose: If True, print progress to console

        Returns:
            Count of chunks indexed
        """
        if source == KnowledgeSource.LINKEDIN:
            from ..config import settings

            linkedin_dir = settings.processed_dir / "linkedin"
            if linkedin_dir.exists():
                files = list(linkedin_dir.glob("*.md"))
                return self.index_files(source, files, verbose=verbose)
            logger.warning("LinkedIn directory not found: %s", linkedin_dir)
            return 0

        logger.warning(
            "%s should be indexed via index_content() at gather time, not via index_source()",
            source.value,
        )
        return 0

    def index_all(self, verbose: bool = False) -> dict[str, int]:
        """Index all available career data sources.

        Indexes LinkedIn from files. Portfolio/assessment must be gathered
        first (they are indexed at gather time).

        Args:
            verbose: If True, print progress to console

        Returns:
            Dict mapping source names to chunk counts
        """
        results: dict[str, int] = {}

        for source in KnowledgeSource:
            try:
                if source == KnowledgeSource.LINKEDIN:
                    count = self.index_source(source, verbose=verbose)
                else:
                    # Portfolio/assessment: report existing chunk count
                    stats = self.store.get_stats()
                    count = stats.get("by_source", {}).get(source.value, 0)
                results[source.value] = count
            except Exception as e:
                logger.error("Failed to index %s: %s", source.value, e)
                results[source.value] = 0

        return results

    def search(
        self,
        query: str,
        limit: int = 5,
        sources: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search knowledge base.

        Args:
            query: Search query
            limit: Maximum results
            sources: Optional list of source names to filter by

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

        chunks = self.store.search(query, limit=limit, sources=source_enums)

        return [
            {
                "content": chunk.content,
                "source": chunk.source.value,
                "section": chunk.section,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]

    def get_source_content(self, source: KnowledgeSource) -> str:
        """Get all content for a source from the knowledge base.

        Args:
            source: The knowledge source

        Returns:
            Combined content string, or empty string if no data
        """
        return self.store.get_all_content(source)

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

    def get_stats(self) -> dict[str, Any]:
        """Get knowledge base statistics."""
        return self.store.get_stats()
