"""LLM prompts for career intelligence."""

from .builders import PromptBuilder, get_prompt_builder
from .templates import (
    ANALYZE_CAREER_PROMPT,
    COMPARE_ALIGNMENT_PROMPT,
    GENERATE_CV_PROMPT,
    MARKET_FIT_PROMPT,
    MARKET_SKILL_GAP_PROMPT,
    STRATEGIC_ADVICE_PROMPT,
    TRENDING_SKILLS_PROMPT,
)

__all__ = [
    "ANALYZE_CAREER_PROMPT",
    "COMPARE_ALIGNMENT_PROMPT",
    "GENERATE_CV_PROMPT",
    "MARKET_FIT_PROMPT",
    "MARKET_SKILL_GAP_PROMPT",
    "PromptBuilder",
    "STRATEGIC_ADVICE_PROMPT",
    "TRENDING_SKILLS_PROMPT",
    "get_prompt_builder",
]
