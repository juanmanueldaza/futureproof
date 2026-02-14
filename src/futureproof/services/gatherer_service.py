"""Gatherer service - data collection operations.

Single responsibility: Manage and execute data gathering from external sources.
Supports dependency injection for testing.
"""

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

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

        Gathers from GitHub, GitLab, and Portfolio (if configured), and
        auto-detects LinkedIn ZIP exports and CliftonStrengths PDFs in data/raw/.

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

        # Auto-detect LinkedIn ZIP in data/raw/
        raw_dir = Path("data/raw")
        if raw_dir.exists():
            linkedin_zips = list(raw_dir.glob("*[Ll]inked[Ii]n*.zip"))
            if linkedin_zips:
                linkedin_zip = max(linkedin_zips, key=lambda p: p.stat().st_mtime)
                try:
                    self.gather_linkedin(linkedin_zip, verbose=verbose)
                    results["linkedin"] = True
                except Exception:
                    results["linkedin"] = False
            else:
                results["linkedin"] = False

            # Auto-detect CliftonStrengths PDFs
            from ..gatherers.cliftonstrengths import GALLUP_PDF_INDICATORS

            gallup_pdfs = [
                p
                for p in raw_dir.glob("*.pdf")
                if any(ind in p.name.lower() for ind in GALLUP_PDF_INDICATORS)
            ]
            if gallup_pdfs:
                try:
                    self.gather_assessment(raw_dir, verbose=verbose)
                    results["assessment"] = True
                except Exception:
                    results["assessment"] = False
            else:
                results["assessment"] = False

        return results

    def _gather_and_index(self, name: str, *args: Any, verbose: bool = False) -> Path:
        """Gather data from a source and auto-index if enabled.

        Args:
            name: Gatherer name (github, gitlab, portfolio, linkedin, assessment)
            *args: Arguments to pass to gatherer.gather()
            verbose: If True, print progress to console

        Returns:
            Path to generated file
        """
        gatherer = self._get_gatherer(name)
        path = gatherer.gather(*args)
        self._index_if_enabled(name, verbose=verbose)
        return path

    def gather_github(self, username: str | None = None, verbose: bool = False) -> Path:
        """Gather data from GitHub."""
        return self._gather_and_index("github", username, verbose=verbose)

    def gather_gitlab(self, username: str | None = None, verbose: bool = False) -> Path:
        """Gather data from GitLab."""
        return self._gather_and_index("gitlab", username, verbose=verbose)

    def gather_portfolio(self, url: str | None = None, verbose: bool = False) -> Path:
        """Gather data from portfolio website."""
        return self._gather_and_index("portfolio", url, verbose=verbose)

    def gather_linkedin(
        self, zip_path: Path, output_dir: Path | None = None, verbose: bool = False
    ) -> Path:
        """Gather data from LinkedIn export."""
        return self._gather_and_index("linkedin", zip_path, output_dir, verbose=verbose)

    def gather_assessment(self, input_dir: Path | None = None, verbose: bool = False) -> Path:
        """Gather CliftonStrengths assessment data from PDFs."""
        return self._gather_and_index("assessment", input_dir, verbose=verbose)
