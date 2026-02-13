"""Gatherer service - data collection operations.

Single responsibility: Manage and execute data gathering from external sources.
Supports dependency injection for testing.
"""

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ..config import settings

if TYPE_CHECKING:
    from ..gatherers.base import BaseGatherer
    from .knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

# Registry mapping gatherer names to (module_path, class_name).
# To add a new gatherer, add an entry here — no code changes needed elsewhere.
_GATHERER_REGISTRY: dict[str, tuple[str, str]] = {
    "github": ("futureproof.gatherers", "GitHubGatherer"),
    "gitlab": ("futureproof.gatherers", "GitLabGatherer"),
    "portfolio": ("futureproof.gatherers", "PortfolioGatherer"),
    "linkedin": ("futureproof.gatherers", "LinkedInGatherer"),
    "assessment": ("futureproof.gatherers.cliftonstrengths", "CliftonStrengthsGatherer"),
}


class GathererService:
    """Service for data gathering operations.

    Encapsulates all data gathering logic, making it testable and reusable.
    Optionally auto-indexes gathered data to the knowledge base.

    Supports dependency injection for testing:
        # Default usage (creates gatherers internally)
        service = GathererService()

        # With injected gatherers (for testing)
        service = GathererService(gatherers={"github": mock_gatherer})
    """

    def __init__(
        self,
        gatherers: dict[str, "BaseGatherer"] | None = None,
        knowledge_service: "KnowledgeService | None" = None,
    ) -> None:
        """Initialize GathererService.

        Args:
            gatherers: Optional dict mapping source names to gatherer instances.
                      If not provided, gatherers are created lazily on demand.
            knowledge_service: Optional KnowledgeService for auto-indexing.
                              If not provided and auto_index is enabled, created lazily.
        """
        self._gatherers = gatherers or {}
        self._knowledge_service = knowledge_service

    def _get_gatherer(self, name: str) -> "BaseGatherer":
        """Get or create a gatherer by name.

        Uses injected gatherer if available, otherwise creates from registry.

        Args:
            name: Gatherer name (github, gitlab, portfolio, linkedin, assessment)

        Returns:
            BaseGatherer instance

        Raises:
            ValueError: If gatherer name is unknown
        """
        if name in self._gatherers:
            return self._gatherers[name]

        entry = _GATHERER_REGISTRY.get(name)
        if entry is None:
            raise ValueError(f"Unknown gatherer: {name}")

        module_path, class_name = entry
        module = importlib.import_module(module_path)
        gatherer_cls = getattr(module, class_name)
        return gatherer_cls()

    def _get_knowledge_service(self) -> "KnowledgeService":
        """Get or create the knowledge service."""
        if self._knowledge_service is None:
            from .knowledge_service import KnowledgeService

            self._knowledge_service = KnowledgeService()
        return self._knowledge_service

    def _index_if_enabled(self, source_name: str, verbose: bool = False) -> None:
        """Index source to knowledge base if auto-indexing is enabled.

        Args:
            source_name: Name of the source (github, gitlab, etc.)
            verbose: If True, print progress to console
        """
        if not settings.knowledge_auto_index:
            return

        try:
            from ..memory.knowledge import KnowledgeSource

            # Map gatherer name to knowledge source
            source_map = {
                "github": KnowledgeSource.GITHUB,
                "gitlab": KnowledgeSource.GITLAB,
                "portfolio": KnowledgeSource.PORTFOLIO,
                "linkedin": KnowledgeSource.LINKEDIN,
                "assessment": KnowledgeSource.ASSESSMENT,
            }

            source = source_map.get(source_name)
            if source:
                service = self._get_knowledge_service()
                count = service.index_source(source, verbose=verbose)
                logger.info(f"Auto-indexed {count} chunks for {source_name}")
        except ImportError:
            logger.debug("ChromaDB not available, skipping auto-index")
        except Exception as e:
            logger.warning(f"Auto-index failed for {source_name}: {e}")

    def gather_all(self, verbose: bool = False) -> dict[str, bool]:
        """Gather data from all sources.

        Args:
            verbose: If True, print progress to console

        Returns:
            Dict mapping source names to success status
        """
        results: dict[str, bool] = {}

        for name in ("github", "gitlab", "portfolio"):
            try:
                gatherer = self._get_gatherer(name)
                gatherer.gather()
                self._index_if_enabled(name, verbose=verbose)
                results[name] = True
            except Exception:
                results[name] = False

        return results

    def gather_github(self, username: str | None = None, verbose: bool = False) -> Path:
        """Gather data from GitHub.

        Args:
            username: GitHub username (defaults to config)
            verbose: If True, print progress to console

        Returns:
            Path to generated file
        """
        gatherer = self._get_gatherer("github")
        path = gatherer.gather(username)
        self._index_if_enabled("github", verbose=verbose)
        return path

    def gather_gitlab(self, username: str | None = None, verbose: bool = False) -> Path:
        """Gather data from GitLab.

        Args:
            username: GitLab username (defaults to config)
            verbose: If True, print progress to console

        Returns:
            Path to generated file
        """
        gatherer = self._get_gatherer("gitlab")
        path = gatherer.gather(username)
        self._index_if_enabled("gitlab", verbose=verbose)
        return path

    def gather_portfolio(self, url: str | None = None, verbose: bool = False) -> Path:
        """Gather data from portfolio website.

        Args:
            url: Portfolio URL (defaults to config)
            verbose: If True, print progress to console

        Returns:
            Path to generated file
        """
        gatherer = self._get_gatherer("portfolio")
        path = gatherer.gather(url)
        self._index_if_enabled("portfolio", verbose=verbose)
        return path

    def gather_linkedin(
        self, zip_path: Path, output_dir: Path | None = None, verbose: bool = False
    ) -> Path:
        """Gather data from LinkedIn export.

        Args:
            zip_path: Path to LinkedIn export ZIP file
            output_dir: Output directory (optional)
            verbose: If True, print progress to console

        Returns:
            Path to generated file
        """
        gatherer = self._get_gatherer("linkedin")
        path = gatherer.gather(zip_path, output_dir)
        self._index_if_enabled("linkedin", verbose=verbose)
        return path

    def gather_assessment(self, input_dir: Path | None = None, verbose: bool = False) -> Path:
        """Gather CliftonStrengths assessment data from PDFs.

        Args:
            input_dir: Directory containing Gallup PDF files (defaults to data/raw)
            verbose: If True, print progress to console

        Returns:
            Path to generated markdown file
        """
        gatherer = self._get_gatherer("assessment")
        path = gatherer.gather(input_dir)
        self._index_if_enabled("assessment", verbose=verbose)
        return path
