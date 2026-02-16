"""LLM prompts for career intelligence."""

from .builders import get_prompt_builder
from .loader import load_prompt

_PROMPT_MAP = {
    "GENERATE_CV_PROMPT": "generate_cv",
    "ANALYZE_CAREER_PROMPT": "analyze_career",
    "STRATEGIC_ADVICE_PROMPT": "strategic_advice",
    "SYSTEM_PROMPT": "system",
    "MARKET_FIT_PROMPT": "market_fit",
    "MARKET_SKILL_GAP_PROMPT": "market_skill_gap",
    "TRENDING_SKILLS_PROMPT": "trending_skills",
}


def __getattr__(name: str) -> str:
    if name in _PROMPT_MAP:
        return load_prompt(_PROMPT_MAP[name])
    raise AttributeError(f"module 'futureproof.prompts' has no attribute {name!r}")


GENERATE_CV_PROMPT: str  # populated lazily via __getattr__

__all__ = [
    "GENERATE_CV_PROMPT",
    "get_prompt_builder",
    "load_prompt",
]
