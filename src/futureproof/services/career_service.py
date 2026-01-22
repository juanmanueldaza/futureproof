"""Career intelligence service - business logic layer.

This module extracts business logic from the CLI, enabling:
- Unit testing without CLI
- Reuse from other interfaces (API, GUI)
- Clear separation of concerns
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..agents import CareerState, create_graph
from ..utils.data_loader import load_career_data


class ServiceError(Exception):
    """Base exception for service errors."""

    pass


class NoDataError(ServiceError):
    """Raised when no career data is available."""

    pass


class AnalysisError(ServiceError):
    """Raised when analysis fails."""

    pass


class GenerationError(ServiceError):
    """Raised when CV generation fails."""

    pass


AnalysisAction = Literal["analyze_full", "analyze_goals", "analyze_reality", "analyze_gaps"]


@dataclass
class AnalysisResult:
    """Result of a career analysis."""

    action: str
    content: str
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if analysis was successful."""
        return self.error is None


class CareerService:
    """Service layer for career intelligence operations.

    Encapsulates all business logic, making CLI a thin wrapper.
    """

    def __init__(self) -> None:
        self._graph = None

    @property
    def graph(self):
        """Lazy-load graph to avoid import overhead."""
        if self._graph is None:
            self._graph = create_graph()
        return self._graph

    def load_data(self) -> CareerState:
        """Load all processed career data."""
        data = load_career_data()
        return CareerState(**data)  # type: ignore[typeddict-item]

    def has_data(self, state: CareerState) -> bool:
        """Check if any career data is available."""
        return any(k.endswith("_data") and v for k, v in state.items())

    def analyze(self, action: AnalysisAction) -> AnalysisResult:
        """Run career analysis.

        Args:
            action: Type of analysis to perform

        Returns:
            AnalysisResult with content or error

        Raises:
            NoDataError: If no career data is available
        """
        state = self.load_data()

        if not self.has_data(state):
            raise NoDataError("No career data found. Run 'futureproof gather all' first.")

        state["action"] = action
        result = self.graph.invoke(state)

        # Map action to result key
        result_key = {
            "analyze_goals": "goals",
            "analyze_reality": "reality",
            "analyze_gaps": "gaps",
            "analyze_full": "analysis",
        }.get(action, "analysis")

        if "error" in result and result["error"]:
            return AnalysisResult(action=action, content="", error=result["error"])

        return AnalysisResult(
            action=action,
            content=result.get(result_key, "Analysis complete"),
        )

    def gather_all(self) -> dict[str, bool]:
        """Gather data from all sources.

        Returns:
            Dict mapping source names to success status
        """
        from ..gatherers import GitHubGatherer, GitLabGatherer, PortfolioGatherer

        results: dict[str, bool] = {}

        gatherers = [
            ("github", GitHubGatherer()),
            ("gitlab", GitLabGatherer()),
            ("portfolio", PortfolioGatherer()),
        ]

        for name, gatherer in gatherers:
            try:
                gatherer.gather()
                results[name] = True
            except Exception:
                results[name] = False

        return results

    def gather_github(self, username: str | None = None) -> Path:
        """Gather data from GitHub.

        Args:
            username: GitHub username (defaults to config)

        Returns:
            Path to generated file
        """
        from ..gatherers import GitHubGatherer

        gatherer = GitHubGatherer()
        return gatherer.gather(username)

    def gather_gitlab(self, username: str | None = None) -> Path:
        """Gather data from GitLab.

        Args:
            username: GitLab username (defaults to config)

        Returns:
            Path to generated file
        """
        from ..gatherers import GitLabGatherer

        gatherer = GitLabGatherer()
        return gatherer.gather(username)

    def gather_portfolio(self, url: str | None = None) -> Path:
        """Gather data from portfolio website.

        Args:
            url: Portfolio URL (defaults to config)

        Returns:
            Path to generated file
        """
        from ..gatherers import PortfolioGatherer

        gatherer = PortfolioGatherer()
        return gatherer.gather(url)

    def gather_linkedin(self, zip_path: Path, output_dir: Path | None = None) -> Path:
        """Gather data from LinkedIn export.

        Args:
            zip_path: Path to LinkedIn export ZIP file
            output_dir: Output directory (optional)

        Returns:
            Path to generated file
        """
        from ..gatherers import LinkedInGatherer

        gatherer = LinkedInGatherer()
        return gatherer.gather(zip_path, output_dir)

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
        from ..generators import CVGenerator

        try:
            generator = CVGenerator()
            output_path = generator.generate(language=language, format=format)
            return output_path
        except Exception as e:
            raise GenerationError(f"CV generation failed: {e}") from e

    def generate_all_cvs(self) -> list[Path]:
        """Generate all CV variants (all languages and formats).

        Returns:
            List of paths to generated files
        """
        from ..generators import CVGenerator

        generator = CVGenerator()
        paths: list[Path] = []

        for language in ("en", "es"):
            for cv_format in ("ats", "creative"):
                try:
                    path = generator.generate(
                        language=language,  # type: ignore[arg-type]
                        format=cv_format,  # type: ignore[arg-type]
                    )
                    paths.append(path)
                except Exception:
                    pass  # Continue with other variants

        return paths

    def get_advice(self, target: str) -> str:
        """Get strategic career advice for a target goal.

        Args:
            target: Target role or career goal

        Returns:
            Strategic advice text

        Raises:
            AnalysisError: If advice generation fails
        """
        state = self.load_data()
        state["action"] = "advise"
        state["target"] = target

        result = self.graph.invoke(state)

        if "error" in result and result["error"]:
            raise AnalysisError(result["error"])

        return result.get("advice", "Advice generated")
