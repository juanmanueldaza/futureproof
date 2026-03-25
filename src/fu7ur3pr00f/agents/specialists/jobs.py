"""Jobs Agent — Job search and market intelligence specialist.

Uses LLM with focused system prompt to help users find jobs,
understand market dynamics, and negotiate compensation.
"""

from typing import Any

from fu7ur3pr00f.agents.specialists.base import BaseAgent


class JobsAgent(BaseAgent):
    """Job search and market intelligence specialist.

    Focus areas:
    - Job market analysis for target roles
    - Resume/CV optimization advice
    - Interview preparation strategies
    - Salary negotiation guidance
    - Remote work opportunities
    """

    KEYWORDS = frozenset(
        {
            "jobs",
            "job",
            "hiring",
            "interview",
            "salary",
            "compensation",
            "benefits",
            "remote",
            "work from home",
            "job search",
            "apply",
            "resume",
            "cv",
            "negotiate",
            "offer",
            "market",
            "opportunity",
            "recruiter",
            "application",
            "cover letter",
        }
    )

    @property
    def name(self) -> str:
        return "jobs"

    @property
    def description(self) -> str:
        return "Job search and market intelligence"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a job search strategist for software developers.\n\n"
            "Your expertise:\n"
            "- Analyzing job market trends and demand\n"
            "- Matching user skills to market opportunities\n"
            "- Salary negotiation strategies (always advocate for fair pay)\n"
            "- Resume/CV optimization for ATS and human readers\n"
            "- Interview preparation (system design, behavioral, coding)\n"
            "- Remote work strategies and opportunities\n\n"
            "Response style:\n"
            "- Analyze the user's experience against market demand\n"
            "- Be specific about salary ranges (cite data when available)\n"
            "- Identify the user's strongest selling points from their data\n"
            "- Suggest concrete job search strategies, not generic 'apply more'\n"
            "- For salary questions, consider location, experience, and market\n"
            "- Warn about common pitfalls (lowball offers, hidden red flags)\n"
        )

    def can_handle(self, intent: str) -> bool:
        intent_lower = intent.lower()
        return any(kw in intent_lower for kw in self.KEYWORDS)

    async def process(self, context: dict[str, Any]) -> str:
        """Process with extra experience context."""
        context.get("query", "")

        # Pull experience data specifically for job matching
        experience = self.search_knowledge(
            "work experience positions companies", limit=5
        )
        if experience:
            context.setdefault("_extra_kb", [])
            context["_extra_kb"].extend(experience)

        return await super().process(context)


__all__ = ["JobsAgent"]
