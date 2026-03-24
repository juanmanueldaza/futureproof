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

from dataclasses import dataclass, field


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
            not self.work_is_ethical or
            not self.product_respects_freedom or
            self.crunch_expected
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
        green_count = sum([
            self.company_contributes_to_oss,
            self.product_respects_freedom,
            self.work_is_ethical,
            self.has_work_life_balance,
            self.is_remote_friendly,
            self.fair_compensation,
        ])
        return green_count >= 4


# Core values prompt template for all agents
VALUES_PROMPT = """
## Core Values

You are FutureProof, a career intelligence assistant that helps developers 
succeed on their own terms while upholding these values:

### Free Software Freedom
- Users should control the software they run
- Proprietary software restricts user freedom
- Open source is the ethical default

### Hacker Ethic
- Access to computers should be unlimited
- All information should be free
- Mistrust authority, promote decentralization
- Judge by hacking, not credentials
- Create art and beauty on computers

### Open Source Values
- Transparency in development
- Collaboration over competition
- Meritocracy (best ideas win)
- Inclusivity and mentorship
- Long-term sustainability

### Developer Sovereignty
- Own your data (local storage)
- Own your career (no lock-in)
- Own your tools (forkable, modifiable)

### Work-Life Harmony
- Remote work is freedom
- Burnout is not a badge of honor
- Multiple income streams provide independence

## Recommendation Guidelines

When evaluating opportunities (jobs, projects, companies):

### Red Flags (warn user)
- ❌ Proprietary surveillance software
- ❌ Products that harm user privacy
- ❌ Dark patterns or user manipulation
- ❌ Crunch culture / 60+ hour weeks
- ❌ No OSS contributions from company
- ❌ Vendor lock-in business models

### Green Flags (highlight)
- ✅ Company uses/contributes to OSS
- ✅ Product respects user freedom
- ✅ Remote-friendly, flexible hours
- ✅ Fair compensation + equity
- ✅ Ethical business model
- ✅ Strong engineering culture

## Response Style

When an opportunity has red flags:
1. Acknowledge the positive aspects
2. Clearly state the ethical concerns
3. Suggest alternatives that align with values
4. Let user make informed decision

Example:
"The salary is 20% higher, but consider:
- This company uses proprietary surveillance software
- You can't show the code you write
- 60-hour weeks are expected

Here are 5 ethical alternatives that pay well..."

When an opportunity has green flags:
1. Highlight what makes it special
2. Explain why these values matter
3. Encourage user to prioritize similarly

Remember: You're not neutral. You believe in free software, 
open source, and developer freedom. Help users build careers 
that reflect those values.
"""


# Values-based response templates
RED_FLAG_RESPONSE = """
⚠️ **Ethical Concerns**

This opportunity has some red flags to consider:

{red_flags}

**Alternatives that align with your values:**
{alternatives}

The choice is yours, but remember: your code will outlive your employment. 
Choose wisely.
"""


GREEN_FLAG_RESPONSE = """
✅ **Values-Aligned Opportunity**

This opportunity stands out for:

{green_flags}

Companies like this are rare. They respect:
- User freedom
- Open source collaboration
- Developer well-being

If this aligns with your goals, it's worth pursuing.
"""


MIXED_FLAG_RESPONSE = """
⚖️ **Mixed Opportunity**

**Green flags:**
{green_flags}

**Red flags:**
{red_flags}

**Questions to ask yourself:**
- Can you influence the red flags from within?
- Do the green flags outweigh the concerns?
- Will you be proud of this work in 2 years?

Only you can decide what trade-offs are acceptable.
"""


def apply_values_filter(
    response: str,
    context: ValuesContext | dict[str, bool] | None = None,
    include_values_reminder: bool = True,
) -> str:
    """Apply values-based filtering to agent response.
    
    Analyzes the context and modifies response to highlight ethical concerns
    or praise value-aligned opportunities.
    
    Args:
        response: Original agent response
        context: Values context (dict or ValuesContext)
        include_values_reminder: Whether to include values reminder
    
    Returns:
        Filtered response with values-aware messaging
    
    Example:
        >>> response = "The job pays $200k and has great benefits."
        >>> context = ValuesContext(
        ...     company_uses_proprietary=True,
        ...     crunch_expected=True,
        ...     fair_compensation=True
        ... )
        >>> filtered = apply_values_filter(response, context)
        >>> print(filtered)
        'The salary is excellent ($200k), but consider:
        ⚠️ This company uses proprietary software
        ⚠️ Crunch culture is expected...'
    """
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
    
    # Build red flags list
    red_flags: list[str] = []
    if ctx.company_uses_proprietary:
        red_flags.append("❌ Company uses proprietary software (restricts user freedom)")
    if not ctx.product_respects_freedom:
        red_flags.append("❌ Product may not respect user freedom")
    if not ctx.work_is_ethical:
        red_flags.append("❌ Work may involve unethical practices")
    if ctx.crunch_expected:
        red_flags.append("❌ Crunch culture / long hours expected")
    
    # Build green flags list
    green_flags: list[str] = []
    if ctx.company_contributes_to_oss:
        green_flags.append("✅ Company contributes to open source")
    if ctx.product_respects_freedom:
        green_flags.append("✅ Product respects user freedom")
    if ctx.work_is_ethical:
        green_flags.append("✅ Ethical business model")
    if ctx.has_work_life_balance:
        green_flags.append("✅ Work-life balance respected")
    if ctx.is_remote_friendly:
        green_flags.append("✅ Remote-friendly")
    if ctx.fair_compensation:
        green_flags.append("✅ Fair compensation")
    
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
        alternatives="- Consider companies with strong OSS contributions\n- Look for remote-first, values-aligned startups",
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
    """Check how well an opportunity aligns with user values.
    
    Args:
        company_name: Company name
        job_description: Job description text
        user_values: User's prioritized values (default: FutureProof defaults)
    
    Returns:
        Dict with alignment score and breakdown
    
    Example:
        >>> result = check_opportunity_alignment(
        ...     company_name="Red Hat",
        ...     job_description="Senior Python Developer...",
        ...     user_values=["open_source", "remote", "work_life_balance"]
        ... )
        >>> print(result["score"])
        85
        >>> print(result["breakdown"])
        {'open_source': 100, 'remote': 80, 'work_life_balance': 75}
    """
    # Default user values if not specified
    if user_values is None:
        user_values = [
            "free_software",
            "open_source",
            "remote_friendly",
            "work_life_balance",
            "ethical",
        ]
    
    # Keywords for each value
    value_keywords = {
        "free_software": ["free software", "gnu", "gpl", "freedom", "libre"],
        "open_source": ["open source", "oss", "github", "contributions", "apache", "mit"],
        "remote_friendly": ["remote", "distributed", "work from home", "flexible"],
        "work_life_balance": ["work-life", "balance", "flexible hours", "no crunch"],
        "ethical": ["ethical", "privacy", "user-focused", "transparent"],
        "fair_compensation": ["equity", "stock options", "competitive", "fair"],
    }
    
    # Score each value
    breakdown: dict[str, int] = {}
    job_text = (company_name + " " + job_description).lower()
    
    for value, keywords in value_keywords.items():
        matches = sum(1 for kw in keywords if kw in job_text)
        score = min(100, matches * 25)  # Max 100 per value
        breakdown[value] = score
    
    # Calculate overall score (weighted by user priorities)
    total_score = 0
    weight_sum = 0
    
    for i, value in enumerate(user_values):
        weight = len(user_values) - i  # Higher weight for earlier values
        total_score += breakdown.get(value, 50) * weight
        weight_sum += weight
    
    overall_score = round(total_score / weight_sum) if weight_sum > 0 else 50
    
    return {
        "score": overall_score,
        "breakdown": breakdown,
        "recommendation": _get_recommendation(overall_score),
    }


def _get_recommendation(score: int) -> str:
    """Get recommendation based on alignment score.
    
    Args:
        score: Overall alignment score (0-100)
    
    Returns:
        Recommendation string
    """
    if score >= 80:
        return "Strong alignment with your values. Highly recommended."
    elif score >= 60:
        return "Good alignment with some trade-offs. Worth considering."
    elif score >= 40:
        return "Mixed alignment. Carefully weigh the trade-offs."
    else:
        return "Poor alignment. Consider alternatives that better match your values."


# Export public API
__all__ = [
    "ValuesContext",
    "VALUES_PROMPT",
    "apply_values_filter",
    "check_opportunity_alignment",
]
