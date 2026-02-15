"""LLM prompts for career intelligence."""

from .builders import get_prompt_builder
from .templates import GENERATE_CV_PROMPT

__all__ = [
    "GENERATE_CV_PROMPT",
    "get_prompt_builder",
]
