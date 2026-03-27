"""Coach Agent — Career growth and leadership specialist."""

from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.specialists.toolkits import COACH_TOOLS
from fu7ur3pr00f.prompts import load_prompt


class CoachAgent(BaseAgent):
    """Career growth, promotions, and leadership coaching.

    Specialises in:
    - Promotion strategy (Senior → Staff → Principal)
    - CliftonStrengths-based development planning
    - Leadership and influence building
    - Skill gap analysis for target roles
    """

    KEYWORDS = frozenset(
        {
            "promotion",
            "promoted",
            "leadership",
            "lead",
            "manager",
            "staff",
            "principal",
            "senior",
            "career growth",
            "career path",
            "influence",
            "office politics",
            "cliftonstrengths",
            "strengths",
            "coaching",
            "mentor",
            "mentoring",
            "visibility",
            "impact",
            "advice",
            "strategy",
            "next step",
            "linkedin",
            "generate",
            "title",
            "position",
            "role",
        }
    )

    @property
    def name(self) -> str:
        return "coach"

    @property
    def description(self) -> str:
        return "Career growth and leadership coach"

    @property
    def system_prompt(self) -> str:
        return load_prompt("specialist_coach")

    @property
    def tools(self) -> list:
        return COACH_TOOLS


__all__ = ["CoachAgent"]
