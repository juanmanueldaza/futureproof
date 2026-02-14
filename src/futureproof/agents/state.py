"""State definitions for LangGraph career intelligence operations."""

from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

# ============================================================================
# Market Data Model
# ============================================================================


class MarketData(BaseModel):
    """Market intelligence data from external sources."""

    job_market: str = Field(default="", description="Job market data (JobSpy, Brave)")
    tech_trends: str = Field(default="", description="Technology trends (HN, GitHub)")
    economic_context: str = Field(default="", description="Economic indicators (BLS)")
    salary_data: str = Field(default="", description="Salary/compensation data")


# ============================================================================
# LangGraph State
# ============================================================================


class CareerState(TypedDict, total=False):
    """Complete state for LangGraph execution.

    The 'messages' field uses Annotated with add_messages to enable
    message accumulation with deduplication across nodes (LangGraph reducer).
    """

    # Routing
    action: str
    target: str | None
    include_market: bool

    # Messages and errors
    messages: Annotated[list[AnyMessage], add_messages]
    error: str | None

    # Career data
    linkedin_data: str | None
    github_data: str | None
    gitlab_data: str | None
    portfolio_data: str | None
    assessment_data: str | None

    # Market data
    market_data: MarketData | None
    job_market: str | None
    tech_trends: str | None
    economic_context: str | None
    salary_data: str | None

    # Analysis results
    analysis: str | None
    goals: str | None
    reality: str | None
    gaps: str | None
    market_fit: str | None
    skill_gaps: str | None
    trending_skills: str | None

    # Generation results
    cv_en: str | None
    cv_es: str | None
    advice: str | None
