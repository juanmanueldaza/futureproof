"""Coach Agent — Career growth and leadership coaching specialist.

Uses LLM with focused system prompt and career data context to provide
CliftonStrengths-based coaching advice.
"""

from typing import Any

from fu7ur3pr00f.agents.specialists.base import BaseAgent


class CoachAgent(BaseAgent):
    """Career growth and leadership coaching specialist.

    Focus areas:
    - Promotions (Senior → Staff → Principal)
    - Leadership development
    - CliftonStrengths-based growth strategies
    - Navigating organizational dynamics
    - Building influence and visibility
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
        return (
            "You are a senior career coach specializing in developer career growth.\n\n"
            "Your expertise:\n"
            "- Promotion strategies (IC track: Senior → Staff → Principal)\n"
            "- Leadership development for engineers\n"
            "- CliftonStrengths-based coaching (if data available)\n"
            "- Building influence and organizational visibility\n"
            "- Navigating organizational dynamics\n\n"
            "Response style:\n"
            "- Assess current position based on the user's actual career data\n"
            "- Identify specific gaps between current level and target\n"
            "- Provide a concrete action plan with timelines\n"
            "- Reference CliftonStrengths themes when available\n"
            "- Use real examples from the user's experience, not generic advice\n"
            "- Be direct — say what's missing, not just what's strong\n"
        )

    def can_handle(self, intent: str) -> bool:
        intent_lower = intent.lower()
        return any(kw in intent_lower for kw in self.KEYWORDS)

    async def process(self, context: dict[str, Any]) -> str:
        """Process with extra strengths context if available."""
        query = context.get("query", "")

        # Augment context with strengths data specifically
        strengths = self.search_knowledge(query, limit=3, source="cliftonstrengths")
        if strengths:
            extra = "\n\n## CliftonStrengths Data\n"
            extra += "\n".join(r.content for r in strengths)
            context.setdefault("_extra_context", "")
            context["_extra_context"] = extra

        return await super().process(context)

    def _build_system_prompt(self, profile: str, kb_context: str) -> str:
        """Override to inject extra context (e.g., strengths)."""
        base = super()._build_system_prompt(profile, kb_context)
        # Check if process() added extra context
        # (can't access context dict here, so handled via class-level cache)
        return base


__all__ = ["CoachAgent"]
