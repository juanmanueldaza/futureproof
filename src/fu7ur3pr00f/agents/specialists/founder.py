"""Founder Agent — Startups and entrepreneurship specialist.

Uses LLM with focused system prompt to help developers launch
startups, validate ideas, and build companies.
"""

from typing import Any

from fu7ur3pr00f.agents.specialists.base import BaseAgent


class FounderAgent(BaseAgent):
    """Startups and entrepreneurship specialist.

    Focus areas:
    - Idea validation and market sizing
    - MVP planning and technical architecture
    - Finding co-founders and early team
    - Developer-to-founder transition
    - Bootstrapping vs. fundraising strategy
    """

    KEYWORDS = frozenset(
        {
            "startup",
            "founder",
            "cofounder",
            "co-founder",
            "launch",
            "product",
            "entrepreneur",
            "mvp",
            "side project",
            "business idea",
            "company",
            "build",
            "bootstrap",
            "fundraising",
            "revenue",
            "saas",
            "indie",
            "solo",
            "validate",
        }
    )

    @property
    def name(self) -> str:
        return "founder"

    @property
    def description(self) -> str:
        return "Startups and entrepreneurship"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a startup advisor specializing in developer-founders.\n\n"
            "Your expertise:\n"
            "- Idea validation and market sizing for technical products\n"
            "- MVP planning (scope, tech stack, timeline)\n"
            "- Developer-to-founder transition strategies\n"
            "- Bootstrapping vs. fundraising trade-offs\n"
            "- Building with existing skills (leveraging career experience)\n"
            "- Open source business models\n\n"
            "Response style:\n"
            "- Analyze the user's technical skills for founder-market fit\n"
            "- Be realistic about timelines and effort required\n"
            "- Suggest MVPs they can build with their existing stack\n"
            "- Reference their work experience for domain expertise angles\n"
            "- Warn about common developer-founder mistakes\n"
            "- Prefer sustainable bootstrapping over VC when appropriate\n"
        )

    def can_handle(self, intent: str) -> bool:
        intent_lower = intent.lower()
        return any(kw in intent_lower for kw in self.KEYWORDS)

    async def process(self, context: dict[str, Any]) -> str:
        """Process with technical skills context."""
        context.get("query", "")

        # Pull skills and project data for founder-market fit analysis
        skills = self.search_knowledge("skills technologies expertise", limit=5)
        projects = self.search_knowledge("projects products built", limit=3)
        extra = skills + projects
        if extra:
            context.setdefault("_extra_kb", [])
            context["_extra_kb"].extend(extra)

        return await super().process(context)


__all__ = ["FounderAgent"]
