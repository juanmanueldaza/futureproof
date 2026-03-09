"""Gatherer service - data collection operations.

Single responsibility: Manage and execute data gathering from external sources.
Database-first: gatherers return Section tuples, indexed directly to ChromaDB.
"""

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..config import settings
from ..memory.chunker import Section

if TYPE_CHECKING:
    from .knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)


class GathererService:
    """Service for data gathering operations.

    Encapsulates all data gathering logic, making it testable and reusable.
    Auto-indexes gathered sections directly to the knowledge base (ChromaDB).

    Supports dependency injection for testing:
        service = GathererService(gatherers={"portfolio": mock_gatherer})
    """

    def __init__(
        self,
        gatherers: dict[str, Any] | None = None,
        knowledge_service: "KnowledgeService | None" = None,
    ) -> None:
        self._gatherers = gatherers or {}
        self._knowledge_service = knowledge_service

    def _get_gatherer(self, name: str) -> Any:
        """Get or create a gatherer by name."""
        if name in self._gatherers:
            return self._gatherers[name]

        if name == "portfolio":
            from ..gatherers import PortfolioGatherer

            return PortfolioGatherer()
        if name == "linkedin":
            from ..gatherers import LinkedInGatherer

            return LinkedInGatherer()
        if name == "assessment":
            from ..gatherers import CliftonStrengthsGatherer

            return CliftonStrengthsGatherer()

        raise ValueError(f"Unknown gatherer: {name}")

    def _get_knowledge_service(self) -> "KnowledgeService":
        """Get or create the knowledge service."""
        if self._knowledge_service is None:
            from .knowledge_service import KnowledgeService

            self._knowledge_service = KnowledgeService()
        return self._knowledge_service

    def _index_sections(
        self,
        source_name: str,
        sections: list[Section],
        verbose: bool = False,
    ) -> None:
        """Index sections to knowledge base if auto-indexing is enabled."""
        if not settings.knowledge_auto_index:
            return

        try:
            from ..memory.knowledge import KnowledgeSource

            source_map = {
                "portfolio": KnowledgeSource.PORTFOLIO,
                "linkedin": KnowledgeSource.LINKEDIN,
                "assessment": KnowledgeSource.ASSESSMENT,
            }

            source = source_map.get(source_name)
            if source:
                service = self._get_knowledge_service()
                count = service.index_sections(source, sections, verbose=verbose)
                logger.info("Auto-indexed %d chunks for %s", count, source_name)
        except ImportError:
            logger.debug("ChromaDB not available, skipping auto-index")
        except Exception as e:
            logger.error("Auto-index failed for %s: %s", source_name, e)
            raise

    def gather_all(self, verbose: bool = False) -> dict[str, bool]:
        """Gather data from all sources.

        Gathers from Portfolio (if configured), and auto-detects
        LinkedIn ZIP exports and CliftonStrengths PDFs in data/raw/.

        Args:
            verbose: If True, print progress to console

        Returns:
            Dict mapping source names to success status
        """
        results: dict[str, bool] = {}
        total_start = time.monotonic()

        def _timed_gather(name: str, fn, *args, **kwargs) -> bool:
            t0 = time.monotonic()
            try:
                fn(*args, **kwargs)
                elapsed = time.monotonic() - t0
                logger.info("%s gathered in %.1fs", name, elapsed)
                if verbose:
                    from ..chat.ui import display_gather_result

                    display_gather_result(name, elapsed)
                return True
            except Exception as e:
                elapsed = time.monotonic() - t0
                logger.warning("%s gather failed in %.1fs: %s", name, elapsed, e)
                if verbose:
                    from ..chat.ui import display_gather_result

                    display_gather_result(name, elapsed, success=False)
                return False

        results["portfolio"] = _timed_gather("portfolio", self.gather_portfolio, verbose=verbose)

        # Auto-detect LinkedIn ZIP in data/raw/
        raw_dir = settings.raw_dir
        if raw_dir.exists():
            linkedin_zips = list(raw_dir.glob("*[Ll]inked[Ii]n*.zip"))
            if linkedin_zips:
                linkedin_zip = max(linkedin_zips, key=lambda p: p.stat().st_mtime)
                results["linkedin"] = _timed_gather(
                    "linkedin", self.gather_linkedin, linkedin_zip, verbose=verbose
                )
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
                results["assessment"] = _timed_gather(
                    "assessment", self.gather_assessment, raw_dir, verbose=verbose
                )
            else:
                results["assessment"] = False

        total_elapsed = time.monotonic() - total_start
        logger.info("All sources gathered in %.1fs", total_elapsed)
        if verbose:
            from ..chat.ui import display_timing

            display_timing(total_elapsed)

        return results

    def gather_portfolio(
        self, url: str | None = None, verbose: bool = False,
    ) -> list[Section]:
        """Gather data from portfolio website."""
        gatherer = self._get_gatherer("portfolio")
        sections = gatherer.gather(url)
        self._index_sections("portfolio", sections, verbose=verbose)
        return sections

    def gather_linkedin(
        self, zip_path: Path, verbose: bool = False,
    ) -> list[Section]:
        """Gather data from LinkedIn export."""
        gatherer = self._get_gatherer("linkedin")
        sections = gatherer.gather(zip_path)
        self._index_sections("linkedin", sections, verbose=verbose)
        return sections

    def gather_assessment(
        self, input_dir: Path | None = None, verbose: bool = False,
    ) -> list[Section]:
        """Gather CliftonStrengths assessment data from PDFs."""
        gatherer = self._get_gatherer("assessment")
        sections = gatherer.gather(input_dir)
        self._index_sections("assessment", sections, verbose=verbose)
        return sections
