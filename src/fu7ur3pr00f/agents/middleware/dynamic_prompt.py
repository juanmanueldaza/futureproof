"""Dynamic prompt middleware — injects live profile and knowledge stats.

Builds system prompts with real-time data from the user's profile and
knowledge base, using a 5-second TTL cache to avoid repeated I/O.

Usage:
    from fu7ur3pr00f.agents.middleware.dynamic_prompt import (
        build_dynamic_prompt,
        make_specialist_prompt,
        invalidate_prompt_cache,
    )
"""

import contextlib
import logging
import threading
import time

from langchain.agents.middleware import dynamic_prompt
from langchain.agents.middleware.types import ModelRequest

logger = logging.getLogger(__name__)

# TTL cache for build_dynamic_prompt
_prompt_cache: str | None = None
_prompt_cache_time: float = 0.0
_prompt_cache_lock = threading.Lock()
_PROMPT_TTL = 5.0  # seconds


@dynamic_prompt
def build_dynamic_prompt(request: ModelRequest) -> str:
    """Build system prompt with live profile and knowledge base stats.

    Uses a 5-second TTL cache to avoid repeated disk I/O and ChromaDB
    queries across the 3-5 model calls per user message.

    Args:
        request: Model request (unused, prompt is context-based)

    Returns:
        System prompt with live profile and knowledge base data
    """
    global _prompt_cache, _prompt_cache_time

    now = time.monotonic()
    with _prompt_cache_lock:
        if _prompt_cache is not None and (now - _prompt_cache_time) < _PROMPT_TTL:
            return _prompt_cache

    result = _build_prompt_uncached()

    with _prompt_cache_lock:
        _prompt_cache = result
        _prompt_cache_time = time.monotonic()

    return result


def _build_prompt_uncached() -> str:
    """Generate the full system prompt (no caching)."""
    from fu7ur3pr00f.memory.profile import load_profile
    from fu7ur3pr00f.prompts import load_prompt
    from fu7ur3pr00f.services.knowledge_service import KnowledgeService
    from fu7ur3pr00f.utils.security import anonymize_career_data, sanitize_for_prompt

    # Single stats call — reused for auto-populate and data section
    service = KnowledgeService()
    stats = service.get_stats()

    profile = load_profile()
    summary = profile.summary()

    # Auto-populate profile if data exists but profile is empty
    if summary == "No profile information available.":
        if stats.get("total_chunks", 0) > 0:
            with contextlib.suppress(Exception):
                from fu7ur3pr00f.agents.tools.gathering import _auto_populate_profile

                _auto_populate_profile()
                profile = load_profile()
                summary = profile.summary()

    profile_context = (
        summary
        if summary != "No profile information available."
        else "No profile configured yet."
    )
    # Anonymize PII and escape XML boundaries before injecting into system prompt
    if profile_context != "No profile configured yet.":
        profile_context = sanitize_for_prompt(anonymize_career_data(profile_context))

    base = load_prompt("system").format(
        user_profile=profile_context,
    )

    # Append live knowledge base stats
    total = stats.get("total_chunks", 0)

    if total > 0:
        by_source = stats.get("by_source", {})
        sources = [
            f"- {src}: {count} chunks" for src, count in by_source.items() if count > 0
        ]
        data_section = (
            "\n\n## Data Availability (live)\n"
            + "\n".join(sources)
            + "\n\nCareer data is indexed and available. "
            "Use it immediately — do not ask the user to provide "
            "information that is already in the knowledge base."
        )
    else:
        data_section = (
            "\n\n## Data Availability (live)\n"
            "No career data indexed yet. "
            "You CANNOT answer career questions without data. "
            "Call `gather_all_career_data` immediately — the user "
            "will be asked to confirm before it runs."
        )

    return base + data_section


def get_base_prompt() -> str:
    """Get the base system prompt, using the shared TTL cache.

    Shared across all specialist dynamic prompts so the expensive
    profile + ChromaDB stats lookup is only done once per 5s window.

    Returns:
        Cached base system prompt
    """
    global _prompt_cache, _prompt_cache_time

    now = time.monotonic()
    with _prompt_cache_lock:
        if _prompt_cache is not None and (now - _prompt_cache_time) < _PROMPT_TTL:
            return _prompt_cache

    result = _build_prompt_uncached()

    with _prompt_cache_lock:
        _prompt_cache = result
        _prompt_cache_time = time.monotonic()

    return result


def make_specialist_prompt(specialist_addendum: str):
    """Create a dynamic_prompt middleware for a specialist agent.

    Uses the shared base prompt cache (profile + KB stats) and appends
    the specialist's focused system instructions on each call.

    Args:
        specialist_addendum: Specialist persona and instructions to append

    Returns:
        A @dynamic_prompt middleware function for use in create_agent()
    """
    from langchain.agents.middleware import dynamic_prompt as dp_decorator

    @dp_decorator
    def _specialist_prompt(request: ModelRequest) -> str:  # noqa: ARG001
        base = get_base_prompt()
        return base + f"\n\n## Your Specialist Role\n{specialist_addendum}"

    return _specialist_prompt


def invalidate_prompt_cache() -> None:
    """Clear the dynamic prompt TTL cache. For tests."""
    global _prompt_cache
    with _prompt_cache_lock:
        _prompt_cache = None


# Backward compatibility alias
_invalidate_prompt_cache = invalidate_prompt_cache


__all__ = [
    "build_dynamic_prompt",
    "get_base_prompt",
    "make_specialist_prompt",
    "invalidate_prompt_cache",
    "_invalidate_prompt_cache",
]
