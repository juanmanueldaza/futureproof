"""Code Agent — GitHub, GitLab, and open source strategy specialist.

Uses LLM with focused system prompt to help users improve their
code portfolio, contribute to open source, and showcase projects.
"""

from typing import Any

from fu7ur3pr00f.agents.specialists.base import BaseAgent


class CodeAgent(BaseAgent):
    """GitHub, GitLab, and open source strategy specialist.

    Focus areas:
    - GitHub/GitLab profile optimization
    - Open source contribution strategy
    - Project portfolio development
    - Code visibility and developer branding
    - Side project planning
    """

    KEYWORDS = frozenset(
        {
            "github",
            "gitlab",
            "repos",
            "repositories",
            "code",
            "commits",
            "open source",
            "oss",
            "contributions",
            "projects",
            "portfolio",
            "side project",
            "developer brand",
            "visibility",
        }
    )

    @property
    def name(self) -> str:
        return "code"

    @property
    def description(self) -> str:
        return "GitHub, GitLab, and open source strategy"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a developer portfolio and open source strategist.\n\n"
            "Your expertise:\n"
            "- GitHub/GitLab profile optimization for recruiters\n"
            "- Open source contribution strategy (what to contribute to, how)\n"
            "- Building impressive project portfolios\n"
            "- Developer branding through code (README, docs, architecture)\n"
            "- Side project selection for career impact\n\n"
            "Response style:\n"
            "- Analyze the user's existing repos and contributions\n"
            "- Identify gaps in their code portfolio\n"
            "- Suggest specific projects that demonstrate target role skills\n"
            "- Give actionable GitHub/GitLab profile improvements\n"
            "- Recommend open source projects matching their skill level\n"
            "- Prioritize quality over quantity — 3 great repos > 30 stale ones\n"
        )

    def can_handle(self, intent: str) -> bool:
        intent_lower = intent.lower()
        return any(kw in intent_lower for kw in self.KEYWORDS)

    async def process(self, context: dict[str, Any]) -> str:
        """Process with GitHub/GitLab data if available."""
        context.get("query", "")

        # Pull code-specific data
        code_data = self.search_knowledge(
            "github gitlab repositories projects contributions",
            limit=5,
        )
        if code_data:
            context.setdefault("_extra_kb", [])
            context["_extra_kb"].extend(code_data)

        return await super().process(context)


__all__ = ["CodeAgent"]
