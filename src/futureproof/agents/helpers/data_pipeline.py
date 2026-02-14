"""Data preparation for orchestrator nodes."""

from functools import partial
from typing import Any


def prepare_data(
    state: dict[str, Any],
    *,
    include_analysis: bool = False,
    preserve_professional_emails: bool = True,
) -> str:
    """Combine and anonymize career data for LLM consumption.

    Args:
        state: CareerState dict with career data fields
        include_analysis: Whether to include analysis results
        preserve_professional_emails: Whether to preserve work emails

    Returns:
        Combined and anonymized career data string, or empty string if no data
    """
    from ...utils.data_loader import combine_career_data
    from ...utils.security import anonymize_career_data

    combined = combine_career_data(state, include_analysis=include_analysis)
    if not combined:
        return ""

    return anonymize_career_data(
        combined,
        preserve_professional_emails=preserve_professional_emails,
    )


# Pre-configured callables for common use cases
default_pipeline = prepare_data
advice_pipeline = partial(prepare_data, include_analysis=True)
