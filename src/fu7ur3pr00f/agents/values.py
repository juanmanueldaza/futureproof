"""FutureProof values enforcement for agent responses.

This module ensures all agent responses align with FutureProof's core values:
- Free software freedom
- Open source collaboration
- Developer sovereignty
- Ethical technology
- Work-life harmony

Example:
    >>> from fu7ur3pr00f.agents.values import apply_values_filter, VALUES_PROMPT
    >>> response = "Take the job, it pays 20% more!"
    >>> filtered = apply_values_filter(
    ...     response,
    ...     context={"company_uses_proprietary": True}
    ... )
    >>> print(filtered)
    'The salary is higher, but consider: this company uses proprietary software...'
"""

from dataclasses import dataclass
from typing import Any

from fu7ur3pr00f.prompts import load_prompt


@dataclass
class ValuesContext:
    """Context for values-based filtering.

    Attributes:
        company_uses_proprietary: Does company use proprietary software?
        company_contributes_to_oss: Does company contribute to open source?
        product_respects_freedom: Does product respect user freedom?
        work_is_ethical: Is the work ethical (no surveillance/manipulation)?
        has_work_life_balance: Does company respect work-life balance?
        is_remote_friendly: Is remote work available?
        fair_compensation: Is compensation fair?
        crunch_expected: Is crunch/overtime expected?

    Example:
        >>> ctx = ValuesContext(
        ...     company_uses_proprietary=True,
        ...     product_respects_freedom=False,
        ...     crunch_expected=True
        ... )
        >>> ctx.has_red_flags()
        True
    """

    company_uses_proprietary: bool = False
    company_contributes_to_oss: bool = False
    product_respects_freedom: bool = True
    work_is_ethical: bool = True
    has_work_life_balance: bool = True
    is_remote_friendly: bool = False
    fair_compensation: bool = True
    crunch_expected: bool = False

    def has_red_flags(self) -> bool:
        """Check if opportunity has ethical red flags.

        Returns:
            True if any critical red flags present

        Example:
            >>> ctx = ValuesContext(
            ...     work_is_ethical=False,
            ...     crunch_expected=True
            ... )
            >>> ctx.has_red_flags()
            True
        """
        return (
            not self.work_is_ethical
            or not self.product_respects_freedom
            or self.crunch_expected
        )

    def has_green_flags(self) -> bool:
        """Check if opportunity has ethical green flags.

        Returns:
            True if multiple green flags present

        Example:
            >>> ctx = ValuesContext(
            ...     company_contributes_to_oss=True,
            ...     is_remote_friendly=True,
            ...     has_work_life_balance=True
            ... )
            >>> ctx.has_green_flags()
            True
        """
        green_count = sum(
            [
                self.company_contributes_to_oss,
                self.product_respects_freedom,
                self.work_is_ethical,
                self.has_work_life_balance,
                self.is_remote_friendly,
                self.fair_compensation,
            ]
        )
        return green_count >= 4

    def red_flag_messages(self) -> list[str]:
        """Build the list of red flag warning messages for this context."""
        flags: list[str] = []
        if self.company_uses_proprietary:
            flags.append("❌ Company uses proprietary software (restricts user freedom)")
        if not self.product_respects_freedom:
            flags.append("❌ Product may not respect user freedom")
        if not self.work_is_ethical:
            flags.append("❌ Work may involve unethical practices")
        if self.crunch_expected:
            flags.append("❌ Crunch culture / long hours expected")
        return flags

    def green_flag_messages(self) -> list[str]:
        """Build the list of green flag approval messages for this context."""
        flags: list[str] = []
        if self.company_contributes_to_oss:
            flags.append("✅ Company contributes to open source")
        if self.product_respects_freedom:
            flags.append("✅ Product respects user freedom")
        if self.work_is_ethical:
            flags.append("✅ Ethical business model")
        if self.has_work_life_balance:
            flags.append("✅ Work-life balance respected")
        if self.is_remote_friendly:
            flags.append("✅ Remote-friendly")
        if self.fair_compensation:
            flags.append("✅ Fair compensation")
        return flags


# Core values prompt template for all agents
VALUES_PROMPT = load_prompt("values")

# Values-based response templates
RED_FLAG_RESPONSE = load_prompt("values_red_flag")
GREEN_FLAG_RESPONSE = load_prompt("values_green_flag")
MIXED_FLAG_RESPONSE = load_prompt("values_mixed_flag")


def apply_values_filter(
    response: str,
    context: ValuesContext | dict[str, bool] | None = None,
    include_values_reminder: bool = True,
) -> str:
    """Apply values-based filtering to agent response.

    Disabled by default. Enable via VALUES_FILTER_ENABLED=true in .env.

    Analyzes the context and modifies response to highlight ethical concerns
    or praise value-aligned opportunities.

    Args:
        response: Original agent response
        context: Values context (dict or ValuesContext)
        include_values_reminder: Whether to include values reminder

    Returns:
        Filtered response with values-aware messaging
    """
    # Opt-in: return unchanged unless explicitly enabled
    from fu7ur3pr00f.config import settings

    if not settings.values_filter_enabled:
        return response

    # Convert dict to ValuesContext if needed
    if isinstance(context, dict):
        ctx = ValuesContext(**context)
    elif context is None:
        ctx = ValuesContext()
    else:
        ctx = context

    # If no red flags and response doesn't need modification, return as-is
    if not ctx.has_red_flags() and not ctx.has_green_flags():
        return response

    red_flags = ctx.red_flag_messages()
    green_flags = ctx.green_flag_messages()

    # Choose appropriate template
    if red_flags and green_flags:
        template = MIXED_FLAG_RESPONSE
    elif red_flags:
        template = RED_FLAG_RESPONSE
    elif green_flags:
        template = GREEN_FLAG_RESPONSE
    else:
        return response

    # Format response
    filtered = template.format(
        red_flags="\n".join(red_flags) if red_flags else "None identified",
        green_flags="\n".join(green_flags) if green_flags else "None identified",
        alternatives=(
            "- Look for OSS-contributing companies\n"
            "- Seek remote-first, values-aligned startups"
        ),
        # Freedom Tax placeholders (defaults for template compatibility)
        amount="0",
        X="0",
        score="50",
        sovereignty_score="50",
        concern="unidentified",
        N="3",
    )

    # Append original response if it adds value
    if response.strip():
        filtered = f"{response}\n\n{filtered}"

    return filtered


def check_opportunity_alignment(
    company_name: str,
    job_description: str,
    user_values: list[str] | None = None,
) -> dict[str, Any]:
    """Check how well an opportunity aligns with user values via LLM analysis.

    Args:
        company_name: Company name
        job_description: Job description text
        user_values: User's prioritized values (default: FutureProof defaults)

    Returns:
        Dict with alignment score, breakdown, and recommendation
    """
    import json

    from langchain_core.messages import HumanMessage

    from fu7ur3pr00f.llm.fallback import get_model_with_fallback

    if user_values is None:
        user_values = [
            "free_software",
            "open_source",
            "remote_friendly",
            "work_life_balance",
            "ethical",
        ]

    values_list = ", ".join(user_values)
    breakdown_schema = ", ".join(f'"{v}": <int 0-100>' for v in user_values)
    prompt = (
        f"Analyze this job opportunity for alignment with the developer's values.\n\n"
        f"Company: {company_name}\n"
        f"Job description:\n{job_description[:3000]}\n\n"
        f"Values to evaluate (in priority order): {values_list}\n\n"
        f"For each value, score 0-100 based on evidence in the description. "
        f"Then compute an overall weighted score (higher priority values count more).\n\n"
        f"Respond with valid JSON only:\n"
        f'{{"score": <int 0-100>, "breakdown": {{{breakdown_schema}}}, '
        f'"recommendation": "<one sentence>"}}'
    )

    try:
        model, _ = get_model_with_fallback(purpose="analysis")
        result = model.invoke([HumanMessage(content=prompt)])
        content = result.content.strip()  # type: ignore
        # Extract JSON from response
        start = content.find("{")
        end = content.rfind("}") + 1
        data = json.loads(content[start:end])
        return {
            "score": int(data.get("score", 50)),
            "breakdown": {
                v: int(data.get("breakdown", {}).get(v, 50)) for v in user_values
            },
            "recommendation": str(
                data.get("recommendation", "Unable to assess alignment.")
            ),
        }
    except Exception:
        return {
            "score": 50,
            "breakdown": {v: 50 for v in user_values},
            "recommendation": "Could not assess alignment — check logs for details.",
        }


# Export public API
__all__ = [
    "ValuesContext",
    "VALUES_PROMPT",
    "apply_values_filter",
    "check_opportunity_alignment",
]
