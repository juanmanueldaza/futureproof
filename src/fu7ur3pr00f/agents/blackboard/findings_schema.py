"""Pydantic schema for structured specialist findings."""

from pydantic import BaseModel, ConfigDict, Field

_STR_MAX = 4000
_LIST_MAX = 50
_SHORT_MAX = 500


class SpecialistFindingsModel(BaseModel):
    """Structured extraction of specialist findings from agent output.

    Enforces strict bounds to prevent injection attacks and resource exhaustion.
    """

    model_config = ConfigDict(extra="forbid")

    gaps: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Skill or knowledge gaps identified",
    )

    strengths: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Strengths, assets, and capabilities identified",
    )

    opportunities: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Career opportunities identified",
    )

    skills: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Relevant skills identified or recommended",
    )

    roles: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Target roles or career paths identified",
    )

    timeline: str = Field(
        default="",
        max_length=_SHORT_MAX,
        description="Recommended timeline for goals or transitions",
    )

    reasoning: str = Field(
        default="",
        max_length=_STR_MAX,
        description=(
            "Direct response to the user in first person "
            "(e.g. 'Your current title is Senior Analyst at Accenture'). "
            "For factual questions: one direct sentence. "
            "For analysis/strategy questions: comprehensive narrative. "
            "Never use third-person analyst framing like 'The specialist identified...'."
        ),
    )

    trade_offs: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Trade-offs or decision points identified (e.g. 'remote vs stability')",
    )

    action_items: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Concrete next actions user can take",
    )

    open_questions: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Questions that need user input to resolve",
    )

    confidence: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0) for these findings",
    )

    target_role: str = Field(
        default="",
        max_length=_SHORT_MAX,
        description="Target role identified (coach specialist)",
    )

    portfolio_items: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Portfolio projects or contributions (code specialist)",
    )

    recommended_path: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Recommended path or next steps (founder specialist)",
    )

    projects: list[str] = Field(
        default_factory=list,
        max_length=_LIST_MAX,
        description="Projects or portfolio items",
    )

    salary: str = Field(
        default="",
        max_length=_SHORT_MAX,
        description="Salary/compensation data (jobs specialist)",
    )

    extra: str = Field(
        default="",
        max_length=_SHORT_MAX,
        description="Specialist-specific extra findings (limited)",
    )
