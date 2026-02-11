"""Knowledge indexing service.

Orchestrates indexing of career documents into the knowledge base.
Called after data gathering to keep the index current.
"""

import logging
from pathlib import Path
from typing import Any

from ..config import settings
from ..memory.knowledge import (
    CareerKnowledgeStore,
    KnowledgeSource,
    get_knowledge_store,
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service for managing the career knowledge base.

    Responsibilities:
    - Index career documents after gathering
    - Provide search interface for agent tools
    - Handle incremental updates (clear + re-index per source)
    """

    def __init__(self, store: CareerKnowledgeStore | None = None) -> None:
        """Initialize the knowledge service.

        Args:
            store: CareerKnowledgeStore instance (uses singleton if not provided)
        """
        self._store = store

    @property
    def store(self) -> CareerKnowledgeStore:
        """Get the knowledge store (lazy initialization)."""
        if self._store is None:
            self._store = get_knowledge_store()
        return self._store

    def index_source(self, source: KnowledgeSource, verbose: bool = False) -> int:
        """Index a single source from processed files.

        Clears existing chunks for source first (incremental update).

        Args:
            source: The knowledge source to index
            verbose: If True, print progress to console

        Returns:
            Count of chunks indexed
        """
        # Clear existing data for this source
        cleared = self.store.clear_source(source)
        if cleared > 0:
            logger.info(f"Cleared {cleared} existing chunks for {source.value}")

        # Get the file(s) to index
        files = self._get_source_files(source)
        if not files:
            logger.warning(f"No files found for source: {source.value}")
            return 0

        total_chunks = 0
        for file_path in files:
            if not file_path.exists():
                logger.debug(f"File not found, skipping: {file_path}")
                continue

            chunk_ids = self.store.index_markdown_file(
                source=source,
                file_path=file_path,
            )
            total_chunks += len(chunk_ids)

            if verbose:
                from ..utils.console import console

                console.print(
                    f"  [dim]📝 Indexed {len(chunk_ids)} chunks from {file_path.name}[/dim]"
                )

        logger.info(f"Indexed {total_chunks} chunks for {source.value}")
        return total_chunks

    def index_all(self, verbose: bool = False) -> dict[str, int]:
        """Index all available career data sources.

        Args:
            verbose: If True, print progress to console

        Returns:
            Dict mapping source names to chunk counts
        """
        results: dict[str, int] = {}

        for source in KnowledgeSource:
            try:
                count = self.index_source(source, verbose=verbose)
                results[source.value] = count
            except Exception as e:
                logger.error(f"Failed to index {source.value}: {e}")
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
        # Convert source strings to enum
        source_enums = None
        if sources:
            source_enums = []
            for s in sources:
                try:
                    source_enums.append(KnowledgeSource(s.lower()))
                except ValueError:
                    logger.warning(f"Unknown source: {s}")

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

    def get_stats(self) -> dict[str, Any]:
        """Get knowledge base statistics.

        Returns:
            Dict with total_chunks, by_source counts
        """
        return self.store.get_stats()

    def _get_source_files(self, source: KnowledgeSource) -> list[Path]:
        """Get the processed file path(s) for a source.

        Args:
            source: The knowledge source

        Returns:
            List of file paths to index
        """
        source_mappings: dict[KnowledgeSource, list[Path]] = {
            KnowledgeSource.GITHUB: [
                settings.processed_dir / "github" / settings.github_output_filename
            ],
            KnowledgeSource.GITLAB: [
                settings.processed_dir / "gitlab" / settings.gitlab_output_filename
            ],
            KnowledgeSource.PORTFOLIO: [
                settings.processed_dir / "portfolio" / settings.portfolio_output_filename
            ],
            KnowledgeSource.ASSESSMENT: [
                settings.processed_dir / "assessment" / "cliftonstrengths.md"
            ],
        }

        # LinkedIn has multiple files
        if source == KnowledgeSource.LINKEDIN:
            linkedin_dir = settings.processed_dir / "linkedin"
            if linkedin_dir.exists():
                # Index all markdown files in linkedin directory
                return list(linkedin_dir.glob("*.md"))
            return []

        return source_mappings.get(source, [])
