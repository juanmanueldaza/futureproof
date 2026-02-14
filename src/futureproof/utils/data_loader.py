"""Unified career data loading utilities.

Database-first: all career data is loaded from ChromaDB knowledge base.
No file I/O — gatherers index content directly to ChromaDB.
"""

import logging
from collections.abc import Mapping
from typing import Any

logger = logging.getLogger(__name__)


def load_career_data() -> dict[str, str]:
    """Load all career data from the knowledge base.

    Returns:
        Dictionary with keys like 'linkedin_data', 'portfolio_data', etc.
        Only includes sources that have indexed content.
    """
    from ..services.knowledge_service import KnowledgeService

    service = KnowledgeService()
    return service.get_all_content()


def load_career_data_for_cv() -> str:
    """Load career data formatted for CV generation.

    Returns:
        Combined markdown string of all career data with section headers
    """
    data = load_career_data()
    if not data:
        return ""

    source_names = {
        "linkedin_data": "LinkedIn",
        "portfolio_data": "Portfolio",
        "assessment_data": "CliftonStrengths Assessment",
    }

    parts = []
    for key, name in source_names.items():
        value = data.get(key)
        if value:
            parts.append(f"### {name}\n{value}")

    return "\n\n".join(parts) if parts else ""


def combine_career_data(
    data: Mapping[str, Any],
    header_prefix: str = "##",
    include_analysis: bool = False,
) -> str:
    """Combine career data dict into formatted string.

    Args:
        data: Dictionary with career data (linkedin_data, portfolio_data, etc.)
        header_prefix: Markdown header prefix (default "##")
        include_analysis: Whether to include 'analysis' field if present

    Returns:
        Combined markdown string
    """
    parts = []
    source_names = {
        "linkedin_data": "LinkedIn Data",
        "portfolio_data": "Portfolio Data",
        "assessment_data": "CliftonStrengths Assessment",
    }

    if include_analysis:
        source_names["analysis"] = "Previous Analysis"

    for key, name in source_names.items():
        value = data.get(key)
        if value:
            parts.append(f"{header_prefix} {name}\n{value}")

    return "\n\n".join(parts)
