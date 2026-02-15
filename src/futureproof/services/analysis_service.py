"""Analysis service - career analysis and advice operations.

Single responsibility: Execute career analysis and advice generation via LangGraph.
"""

import json
from dataclasses import dataclass
from typing import Literal

from ..agents import CareerState, create_graph
from ..agents.helpers import ACTION_RESULT_KEYS
from ..utils.data_loader import load_career_data
from .exceptions import AnalysisError, NoDataError

# Type alias for analysis actions
AnalysisAction = Literal[
    "analyze_full",
    "analyze_gaps",
    "analyze_market",
    "analyze_skills",
]


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


class AnalysisService:
    """Service for career analysis operations.

    Encapsulates LangGraph invocation for analysis and advice.
    Lazy-loads the graph to avoid import overhead.
    """

    def __init__(self) -> None:
        """Initialize AnalysisService."""
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

    def analyze(
        self,
        action: AnalysisAction,
        market_data: dict | None = None,
        target: str | None = None,
    ) -> AnalysisResult:
        """Run career analysis.

        Args:
            action: Type of analysis to perform
            market_data: Optional market intelligence data for market-aware analysis
            target: Optional target role for gap analysis

        Returns:
            AnalysisResult with content or error

        Raises:
            NoDataError: If no career data is available
        """
        state = self.load_data()

        if not self.has_data(state):
            raise NoDataError("No career data found. Run 'futureproof gather all' first.")

        state["action"] = action

        if target:
            state["target"] = target

        # Add market data if provided
        # Map gatherer keys to state keys expected by the orchestrator
        if market_data:
            # Tech trends from HN trending stories + hiring trends
            trends_parts = []
            stories = market_data.get("trending_stories", [])
            if stories:
                top = stories[:10] if isinstance(stories, list) else []
                trends_parts.append(
                    "Trending topics:\n"
                    + "\n".join(f"- {s.get('title', '')} ({s.get('points', 0)} pts)" for s in top)
                )
            hiring = market_data.get("hiring_trends", {})
            if hiring:
                trends_parts.append(f"Hiring trends:\n{json.dumps(hiring, indent=2)}")
            state["tech_trends"] = "\n\n".join(trends_parts)

            # Job postings from HN
            jobs = market_data.get("hn_job_postings", [])
            if jobs:
                job_lines = []
                for j in jobs[:20]:
                    company = j.get("company", "Unknown")
                    role = j.get("role", "")
                    tech = ", ".join(j.get("tech_stack", []))
                    job_lines.append(f"- {company}: {role} [{tech}]")
                state["job_market"] = "HN Job Postings:\n" + "\n".join(job_lines)

            state["economic_context"] = market_data.get("economic_context", "")

        result = self.graph.invoke(state)

        # Use centralized result key mapping
        result_key = ACTION_RESULT_KEYS.get(action, "analysis")

        if "error" in result and result["error"]:
            return AnalysisResult(action=action, content="", error=result["error"])

        return AnalysisResult(
            action=action,
            content=result.get(result_key, "Analysis complete"),
        )

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
