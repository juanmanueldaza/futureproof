"""LLM prompts for career intelligence."""

from .builders import PromptBuilder, get_prompt_builder
from .system import SYSTEM_PROMPT
from .templates import (
    ANALYZE_CAREER_PROMPT,
    GENERATE_CV_PROMPT,
    MARKET_FIT_PROMPT,
    MARKET_SKILL_GAP_PROMPT,
    STRATEGIC_ADVICE_PROMPT,
    TRENDING_SKILLS_PROMPT,
)

__all__ = [
    "ANALYZE_CAREER_PROMPT",
    "GENERATE_CV_PROMPT",
    "MARKET_FIT_PROMPT",
    "MARKET_SKILL_GAP_PROMPT",
    "PromptBuilder",
    "STRATEGIC_ADVICE_PROMPT",
    "SYSTEM_PROMPT",
    "TRENDING_SKILLS_PROMPT",
    "get_prompt_builder",
]
