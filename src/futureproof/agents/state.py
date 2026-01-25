"""State definitions for LangGraph career intelligence operations.

Uses Pydantic models for type safety and structured output from LLMs.
Supports both the new Pydantic-based state and backwards-compatible TypedDict.
"""

import operator
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================


class CareerAnalysisResult(BaseModel):
    """Structured output from career analysis."""

    professional_identity: str = Field(description="Summary of who this person is professionally")
    stated_goals: list[str] = Field(
        default_factory=list, description="Career goals explicitly stated in profile"
    )
    actual_activities: list[str] = Field(
        default_factory=list, description="What they're actually doing based on evidence"
    )
    technical_skills: list[str] = Field(
        default_factory=list, description="Technical skills demonstrated"
    )
    strengths: list[str] = Field(default_factory=list, description="Key professional strengths")
    gaps: list[str] = Field(default_factory=list, description="Gaps between goals and reality")
    alignment_score: int = Field(
        default=0, ge=0, le=100, description="Goal-reality alignment score (0-100)"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Actionable recommendations"
    )


class MarketFitAnalysis(BaseModel):
    """Structured output from market fit analysis."""

    alignment_score: int = Field(
        ge=0, le=100, description="How well profile aligns with market demand (0-100)"
    )
    matching_skills: list[str] = Field(
        default_factory=list, description="Skills that match current market demand"
    )
    missing_skills: list[str] = Field(
        default_factory=list, description="In-demand skills not present in profile"
    )
    opportunities: list[str] = Field(
        default_factory=list, description="Market opportunities matching profile"
    )
    risks: list[str] = Field(
        default_factory=list, description="Career risks based on market trends"
    )
    salary_insights: str = Field(default="", description="Salary positioning based on market data")
    recommended_focus: list[str] = Field(
        default_factory=list, description="Skills/areas to focus on"
    )


class SkillGapAnalysis(BaseModel):
    """Structured output from skill gap analysis."""

    current_skills: list[str] = Field(
        default_factory=list, description="Skills demonstrated in profile"
    )
    in_demand_skills: list[str] = Field(
        default_factory=list, description="Skills currently in high demand"
    )
    critical_gaps: list[str] = Field(
        default_factory=list, description="Critical skill gaps to address"
    )
    quick_wins: list[str] = Field(
        default_factory=list, description="Skills close to current expertise (easy to learn)"
    )
    learning_roadmap: list[str] = Field(
        default_factory=list, description="Prioritized learning path"
    )


class TechTrendsAnalysis(BaseModel):
    """Structured output from tech trends analysis."""

    rising_technologies: list[str] = Field(
        default_factory=list, description="Technologies with growing demand"
    )
    declining_technologies: list[str] = Field(
        default_factory=list, description="Technologies with decreasing demand"
    )
    stable_foundations: list[str] = Field(
        default_factory=list, description="Core technologies that remain valuable"
    )
    emerging_roles: list[str] = Field(
        default_factory=list, description="New job roles gaining traction"
    )
    market_sentiment: str = Field(default="", description="Overall tech job market sentiment")


# ============================================================================
# Market Data Models
# ============================================================================


class MarketData(BaseModel):
    """Market intelligence data from external sources."""

    job_market: str = Field(default="", description="Job market data (JobSpy, Brave)")
    tech_trends: str = Field(default="", description="Technology trends (HN, GitHub)")
    economic_context: str = Field(default="", description="Economic indicators (BLS)")
    salary_data: str = Field(default="", description="Salary/compensation data")
    last_updated: str = Field(default="", description="When market data was last refreshed")


# ============================================================================
# LangGraph State (TypedDict for graph compatibility)
# ============================================================================


class CareerState(TypedDict, total=False):
    """State for LangGraph execution.

    Uses TypedDict for LangGraph compatibility while supporting Pydantic
    models for structured output.

    The 'messages' field uses Annotated with operator.add to enable
    message accumulation across nodes (LangGraph reducer pattern).
    """

    # Action routing
    action: str  # What to do: gather, analyze, generate, advise, market_*
    target: str | None  # Target role for advice

    # Message accumulation for tool-calling agents
    messages: Annotated[list[Any], operator.add]

    # Career data from gatherers
    linkedin_data: str | None
    github_data: str | None
    gitlab_data: str | None
    portfolio_data: str | None

    # Market intelligence data
    market_data: MarketData | None
    job_market: str | None
    tech_trends: str | None
    economic_context: str | None
    salary_data: str | None

    # Analysis results (can be str or structured Pydantic model)
    analysis: str | CareerAnalysisResult | None
    goals: str | None
    reality: str | None
    gaps: str | None
    market_fit: MarketFitAnalysis | None
    skill_gaps: SkillGapAnalysis | None
    trending_skills: TechTrendsAnalysis | None

    # Generation results
    cv_en: str | None
    cv_es: str | None

    # Advice results
    advice: str | None

    # Error tracking
    error: str | None

    # Include market data in analysis
    include_market: bool


# ============================================================================
# Input Types (for type hints in node functions)
# ============================================================================


class GatherInput(TypedDict, total=False):
    """Input for gather operations."""

    source: Literal["github", "gitlab", "linkedin", "portfolio", "all"]
    username: str | None
    url: str | None
    zip_path: str | None


class AnalyzeInput(TypedDict, total=False):
    """Input for analysis operations."""

    action: Literal[
        "analyze_full",
        "analyze_goals",
        "analyze_reality",
        "analyze_gaps",
        "analyze_market_fit",
        "analyze_skill_gaps",
        "analyze_trends",
    ]
    include_market: bool


class GenerateInput(TypedDict, total=False):
    """Input for CV generation."""

    language: Literal["en", "es"]
    format: Literal["ats", "creative"]


class AdviseInput(TypedDict, total=False):
    """Input for advice operations."""

    target: str  # Target role/goal
    include_market: bool


class MarketGatherInput(TypedDict, total=False):
    """Input for market data gathering."""

    source: Literal["all", "jobs", "trends", "economic"]
    force_refresh: bool
