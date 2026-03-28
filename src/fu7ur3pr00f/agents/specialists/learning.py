"""Learning Agent — Skill development and expertise building specialist."""

from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.specialists.toolkits import LEARNING_TOOLS
from fu7ur3pr00f.prompts import load_prompt


class LearningAgent(BaseAgent):
    """Skill development, learning roadmaps, and expertise building.

    Specialises in:
    - Personalised learning roadmaps for target roles
    - Identifying the highest-leverage skills to learn next
    - Technology trend analysis (what the market values)
    - Building expertise through teaching (blogs, talks, OSS)
    """

    @property
    def name(self) -> str:
        return "learning"

    @property
    def description(self) -> str:
        return "Skill development and expertise building"

    @property
    def system_prompt(self) -> str:
        return load_prompt("specialist_learning")

    @property
    def tools(self) -> list:
        return LEARNING_TOOLS


__all__ = ["LearningAgent"]
