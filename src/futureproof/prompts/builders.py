"""Centralized prompt construction service.

Follows Single Responsibility Principle (SRP) by consolidating all prompt
building logic into a dedicated service.
"""

from typing import Any

from .loader import load_prompt


class PromptBuilder:
    """Centralized prompt construction service.

    Consolidates prompt building logic previously scattered across
    orchestrator.py and provides a single point for prompt customization.
    """

    # Maps action names to prompt file stems in md/
    ANALYSIS_TEMPLATES: dict[str, str] = {
        "analyze_gaps": "analyze_gaps",
    }

    MARKET_PROMPT_MAP: dict[str, str] = {
        "analyze_market_fit": "market_fit",
        "analyze_skill_gaps": "market_skill_gap",
        "analyze_trends": "trending_skills",
    }

    def build_analysis_prompt(self, action: str, career_data: str) -> str:
        """Build the appropriate analysis prompt based on action type.

        Args:
            action: The analysis action (analyze_full, analyze_goals, etc.)
            career_data: Combined career data string

        Returns:
            Formatted prompt ready for LLM invocation
        """
        name = self.ANALYSIS_TEMPLATES.get(action)

        if name:
            return load_prompt(name).format(career_data=career_data)

        # Default: full analysis
        return f"{load_prompt('analyze_career')}\n\n{career_data}"

    def build_market_context(self, state: dict[str, Any]) -> str:
        """Build market context string from state.

        Args:
            state: State dict containing market data fields

        Returns:
            Formatted market context string
        """
        parts: list[str] = []

        job_market = state.get("job_market")
        if job_market:
            parts.append(f"### Job Market Data\n{job_market}")

        tech_trends = state.get("tech_trends")
        if tech_trends:
            parts.append(f"### Technology Trends\n{tech_trends}")

        economic_context = state.get("economic_context")
        if economic_context:
            parts.append(f"### Economic Context\n{economic_context}")

        salary_data = state.get("salary_data")
        if salary_data:
            parts.append(f"### Salary Data\n{salary_data}")

        return "\n\n".join(parts)

    def build_market_analysis_prompt(self, action: str, career_data: str, market_data: str) -> str:
        """Build market analysis prompt.

        Args:
            action: The analysis action (analyze_market_fit, analyze_skill_gaps, etc.)
            career_data: Combined and anonymized career data
            market_data: Market context string

        Returns:
            Formatted prompt ready for LLM invocation
        """
        name = self.MARKET_PROMPT_MAP.get(action, "market_fit")
        return load_prompt(name).format(career_data=career_data, market_data=market_data)

    def build_advice_prompt(
        self, target: str, career_data: str, market_context: str | None = None
    ) -> str:
        """Build strategic advice prompt.

        Args:
            target: Target role or goal
            career_data: Combined career data with optional analysis
            market_context: Optional market context string

        Returns:
            Formatted prompt ready for LLM invocation
        """
        data_section = career_data
        if market_context:
            data_section = f"{career_data}\n\n## Market Context\n{market_context}"

        return f"""{load_prompt("strategic_advice")}

TARGET GOAL: {target}

CAREER DATA:
{data_section}

Provide strategic, actionable advice for achieving the target goal."""

    def enrich_with_market_context(self, career_data: str, state: dict[str, Any]) -> str:
        """Add market context to career data if available.

        Args:
            career_data: Base career data string
            state: State dict that may contain market data

        Returns:
            Career data with market context appended if available
        """
        market_context = self.build_market_context(state)
        if market_context:
            return f"{career_data}\n\n## Market Context\n{market_context}"
        return career_data


# Module-level singleton for convenience
_builder: PromptBuilder | None = None


def get_prompt_builder() -> PromptBuilder:
    """Get the prompt builder singleton.

    Returns:
        PromptBuilder instance
    """
    global _builder
    if _builder is None:
        _builder = PromptBuilder()
    return _builder
