"""Code Agent — GitHub, GitLab, and open source strategy specialist."""

from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.specialists.toolkits import CODE_TOOLS
from fu7ur3pr00f.prompts import load_prompt


class CodeAgent(BaseAgent):
    """GitHub, GitLab, and open source portfolio specialist.

    Specialises in:
    - GitHub/GitLab profile and repository analysis
    - Open source contribution strategy
    - Portfolio gap identification
    - Project visibility and developer branding
    - Selecting side projects for career impact
    """

    @property
    def name(self) -> str:
        return "code"

    @property
    def description(self) -> str:
        return "GitHub, GitLab, and open source strategy"

    @property
    def system_prompt(self) -> str:
        return load_prompt("specialist_code")

    @property
    def tools(self) -> list:
        return CODE_TOOLS


__all__ = ["CodeAgent"]
