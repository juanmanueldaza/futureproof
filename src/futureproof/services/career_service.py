"""Career intelligence service - unified facade.

This module provides a unified interface to career intelligence operations
while delegating to focused sub-services internally.

SRP-compliant: CareerService is now a facade that:
- Maintains backward compatibility with existing CLI
- Delegates to focused sub-services (GathererService, AnalysisService, GenerationService)
- Supports dependency injection for testing
"""

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from .analysis_service import AnalysisAction, AnalysisResult, AnalysisService
from .exceptions import AnalysisError, GenerationError, NoDataError, ServiceError
from .gatherer_service import GathererService
from .generation_service import GenerationService

if TYPE_CHECKING:
    from ..agents import CareerState
    from ..gatherers.base import BaseGatherer

# Re-export for backward compatibility
__all__ = [
    "AnalysisAction",
    "AnalysisError",
    "AnalysisResult",
    "CareerService",
    "GenerationError",
    "NoDataError",
    "ServiceError",
]


class CareerService:
    """Unified facade for career intelligence operations.

    Maintains backward compatibility with existing CLI while
    delegating to focused sub-services internally.

    SRP: This class now only coordinates between services.
    Each service has a single responsibility:
    - GathererService: Data collection
    - AnalysisService: Career analysis and advice
    - GenerationService: CV generation

    Supports dependency injection for testing:
        # Default usage (creates services internally)
        service = CareerService()

        # With injected gatherers (for testing)
        service = CareerService(gatherers={"github": mock_gatherer})
    """

    def __init__(
        self,
        gatherers: dict[str, "BaseGatherer"] | None = None,
    ) -> None:
        """Initialize CareerService.

        Args:
            gatherers: Optional dict mapping source names to gatherer instances.
                      Passed to GathererService for dependency injection.
        """
        self._gatherer_service = GathererService(gatherers=gatherers)
        self._analysis_service = AnalysisService()
        self._generation_service = GenerationService()

    # =========================================================================
    # Analysis Service Delegation
    # =========================================================================

    @property
    def graph(self):
        """Lazy-load graph to avoid import overhead."""
        return self._analysis_service.graph

    def load_data(self) -> "CareerState":
        """Load all processed career data."""
        return self._analysis_service.load_data()

    def has_data(self, state: "CareerState") -> bool:
        """Check if any career data is available."""
        return self._analysis_service.has_data(state)

    def analyze(
        self,
        action: AnalysisAction,
        market_data: dict | None = None,
    ) -> AnalysisResult:
        """Run career analysis.

        Args:
            action: Type of analysis to perform
            market_data: Optional market intelligence data for market-aware analysis

        Returns:
            AnalysisResult with content or error

        Raises:
            NoDataError: If no career data is available
        """
        return self._analysis_service.analyze(action, market_data)

    def get_advice(self, target: str) -> str:
        """Get strategic career advice for a target goal.

        Args:
            target: Target role or career goal

        Returns:
            Strategic advice text

        Raises:
            AnalysisError: If advice generation fails
        """
        return self._analysis_service.get_advice(target)

    # =========================================================================
    # Gatherer Service Delegation
    # =========================================================================

    def gather_all(self) -> dict[str, bool]:
        """Gather data from all sources.

        Returns:
            Dict mapping source names to success status
        """
        return self._gatherer_service.gather_all()

    def gather_github(self, username: str | None = None) -> Path:
        """Gather data from GitHub.

        Args:
            username: GitHub username (defaults to config)

        Returns:
            Path to generated file
        """
        return self._gatherer_service.gather_github(username)

    def gather_gitlab(self, username: str | None = None) -> Path:
        """Gather data from GitLab.

        Args:
            username: GitLab username (defaults to config)

        Returns:
            Path to generated file
        """
        return self._gatherer_service.gather_gitlab(username)

    def gather_portfolio(self, url: str | None = None) -> Path:
        """Gather data from portfolio website.

        Args:
            url: Portfolio URL (defaults to config)

        Returns:
            Path to generated file
        """
        return self._gatherer_service.gather_portfolio(url)

    def gather_linkedin(self, zip_path: Path, output_dir: Path | None = None) -> Path:
        """Gather data from LinkedIn export.

        Args:
            zip_path: Path to LinkedIn export ZIP file
            output_dir: Output directory (optional)

        Returns:
            Path to generated file
        """
        return self._gatherer_service.gather_linkedin(zip_path, output_dir)

    def gather_assessment(self, input_dir: Path | None = None) -> Path:
        """Gather CliftonStrengths assessment data from PDFs.

        Args:
            input_dir: Directory containing Gallup PDF files (defaults to data/raw)

        Returns:
            Path to generated markdown file
        """
        return self._gatherer_service.gather_assessment(input_dir)

    # =========================================================================
    # Generation Service Delegation
    # =========================================================================

    def generate_cv(
        self,
        language: Literal["en", "es"] = "en",
        format: Literal["ats", "creative"] = "ats",
    ) -> Path:
        """Generate CV and return path to output file.

        Args:
            language: Output language
            format: CV format

        Returns:
            Path to generated CV file

        Raises:
            GenerationError: If generation fails
        """
        return self._generation_service.generate_cv(language, format)

    def generate_all_cvs(self) -> list[Path]:
        """Generate all CV variants (all languages and formats).

        Returns:
            List of paths to generated files
        """
        return self._generation_service.generate_all_cvs()
