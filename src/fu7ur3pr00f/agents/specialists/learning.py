"""Learning Agent — Skill development and expertise building specialist.

Uses LLM with focused system prompt to help users build skills,
plan learning paths, and become recognized experts.
"""

from typing import Any

from fu7ur3pr00f.agents.specialists.base import BaseAgent


class LearningAgent(BaseAgent):
    """Skill development and expertise building specialist.

    Focus areas:
    - Learning roadmaps for target roles
    - Identifying skill gaps from career data
    - Certification and course recommendations
    - Building public expertise (writing, speaking, teaching)
    - Deep vs. broad skill development strategy
    """

    KEYWORDS = frozenset(
        {
            "learning",
            "study",
            "learn",
            "skills",
            "courses",
            "certification",
            "expert",
            "authority",
            "teaching",
            "conference",
            "talk",
            "blog",
            "write",
            "publish",
            "training",
            "tutorial",
            "practice",
            "improve",
            "master",
            "specialize",
            "roadmap",
            "curriculum",
        }
    )

    @property
    def name(self) -> str:
        return "learning"

    @property
    def description(self) -> str:
        return "Skill development and expertise building"

    @property
    def system_prompt(self) -> str:
        return (
            "You are an expert learning strategist for software developers.\n\n"
            "Your expertise:\n"
            "- Designing personalized learning roadmaps\n"
            "- Identifying the highest-leverage skills to learn next\n"
            "- Recommending certifications, courses, and resources\n"
            "- Building expertise through teaching (blogs, talks, OSS)\n"
            "- Balancing depth vs. breadth in skill development\n\n"
            "Response style:\n"
            "- Analyze the user's current skills from their career data\n"
            "- Compare against requirements for their target role\n"
            "- Prioritize skills by impact (what moves the needle most)\n"
            "- Give specific resource recommendations, not vague 'learn X'\n"
            "- Include timelines: what to learn in 1 month, 3 months, 6 months\n"
            "- Suggest ways to demonstrate skills (projects, writing, talks)\n"
        )

    def can_handle(self, intent: str) -> bool:
        intent_lower = intent.lower()
        return any(kw in intent_lower for kw in self.KEYWORDS)

    async def process(self, context: dict[str, Any]) -> str:
        """Process with extra skills context if available."""
        context.get("query", "")

        # Also pull skills-specific data
        skills_data = self.search_knowledge("skills technologies tools", limit=5)
        if skills_data:
            context.setdefault("_extra_kb", [])
            context["_extra_kb"].extend(skills_data)

        return await super().process(context)


__all__ = ["LearningAgent"]
