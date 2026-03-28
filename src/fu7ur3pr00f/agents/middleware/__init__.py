"""Agent middleware for dynamic prompts, analysis synthesis, and tool call repair.

Middleware modules:
- dynamic_prompt: Injects live profile and knowledge stats into system prompts
- analysis_synthesis: Masks analysis results and synthesizes focused responses
- tool_call_repair: Repairs orphaned tool_calls in message history

Usage:
    from fu7ur3pr00f.agents.middleware import (
        AnalysisSynthesisMiddleware,
        ToolCallRepairMiddleware,
        build_dynamic_prompt,
        make_specialist_prompt,
        _ANALYSIS_MARKER,
    )
"""

from fu7ur3pr00f.agents.middleware.analysis_synthesis import (
    _ANALYSIS_MARKER,
    AnalysisSynthesisMiddleware,
)
from fu7ur3pr00f.agents.middleware.dynamic_prompt import (
    _invalidate_prompt_cache,
    build_dynamic_prompt,
    get_base_prompt,
    invalidate_prompt_cache,
    make_specialist_prompt,
)
from fu7ur3pr00f.agents.middleware.tool_call_repair import ToolCallRepairMiddleware

__all__ = [
    "AnalysisSynthesisMiddleware",
    "ToolCallRepairMiddleware",
    "build_dynamic_prompt",
    "get_base_prompt",
    "make_specialist_prompt",
    "invalidate_prompt_cache",
    "_invalidate_prompt_cache",
    "_ANALYSIS_MARKER",
]
