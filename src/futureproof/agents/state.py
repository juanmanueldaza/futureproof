"""Refined state definitions following Interface Segregation Principle.

This module defines focused TypedDicts for different operations instead of
a monolithic state that mixes input, output, intermediate, and error states.
"""

from typing import Literal, TypedDict

# ============================================================================
# Input States - What comes from user/CLI
# ============================================================================


class GatherInput(TypedDict, total=False):
    """Input for gather operations."""

    source: Literal["github", "gitlab", "linkedin", "portfolio", "all"]
    username: str | None
    url: str | None
    zip_path: str | None


class AnalyzeInput(TypedDict, total=False):
    """Input for analysis operations."""

    action: Literal["analyze_full", "analyze_goals", "analyze_reality", "analyze_gaps"]


class GenerateInput(TypedDict, total=False):
    """Input for CV generation."""

    language: Literal["en", "es"]
    format: Literal["ats", "creative"]


class AdviseInput(TypedDict, total=False):
    """Input for advice operations."""

    target: str  # Target role/goal


# ============================================================================
# Data States - Career data from sources
# ============================================================================


class CareerData(TypedDict, total=False):
    """Raw career data from various sources."""

    linkedin_data: str
    github_data: str
    gitlab_data: str
    portfolio_data: str


# ============================================================================
# Output States - Results from operations
# ============================================================================


class AnalysisOutput(TypedDict, total=False):
    """Output from analysis operations."""

    analysis: str
    goals: str
    reality: str
    gaps: str


class GenerationOutput(TypedDict, total=False):
    """Output from generation operations."""

    cv_en: str
    cv_es: str


class AdviceOutput(TypedDict, total=False):
    """Output from advice operations."""

    advice: str


# ============================================================================
# Combined State - For graph execution (backwards compatible)
# ============================================================================


class CareerState(TypedDict, total=False):
    """Combined state for graph execution.

    This maintains backwards compatibility while the codebase migrates
    to using the specific state types where appropriate.

    Note: The 'error' field is kept for backwards compatibility but
    new code should raise exceptions instead of using it.
    """

    # Input - action routing
    action: str  # What to do: gather, analyze, generate, advise
    target: str | None  # Target role for advice

    # Data sources
    linkedin_data: str | None
    github_data: str | None
    gitlab_data: str | None
    portfolio_data: str | None

    # Analysis results
    analysis: str | None
    goals: str | None
    reality: str | None
    gaps: str | None

    # Generation results
    cv_en: str | None
    cv_es: str | None

    # Advice results
    advice: str | None

    # Error tracking (deprecated - use exceptions instead)
    error: str | None
