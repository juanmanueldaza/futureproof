"""Data preparation pipeline for orchestrator nodes.

Consolidates the repeated pattern across analyze_node, analyze_market_node,
and advise_node for combining and anonymizing career data.
"""

from typing import Any


class DataPipeline:
    """Prepares career data for LLM invocation.

    Consolidates the repeated pattern:
        combined = combine_career_data(dict(state))
        combined = anonymize_career_data(combined, preserve_professional_emails=True)

    Usage:
        pipeline = DataPipeline()
        career_data = pipeline.prepare(dict(state))

        # For advice (includes analysis results):
        advice_pipeline = DataPipeline(include_analysis=True)
        career_data = advice_pipeline.prepare(dict(state))
    """

    def __init__(
        self,
        include_analysis: bool = False,
        preserve_professional_emails: bool = True,
    ) -> None:
        """Initialize the data pipeline.

        Args:
            include_analysis: Whether to include analysis results in combined data
            preserve_professional_emails: Whether to preserve work emails during anonymization
        """
        self.include_analysis = include_analysis
        self.preserve_professional_emails = preserve_professional_emails

    def prepare(self, state: dict[str, Any]) -> str:
        """Prepare career data for LLM consumption.

        Combines all available career data and anonymizes PII.

        Args:
            state: CareerState dict with career data fields

        Returns:
            Combined and anonymized career data string, or empty string if no data
        """
        from ...utils.data_loader import combine_career_data
        from ...utils.security import anonymize_career_data

        combined = combine_career_data(state, include_analysis=self.include_analysis)
        if not combined:
            return ""

        return anonymize_career_data(
            combined,
            preserve_professional_emails=self.preserve_professional_emails,
        )


# Pre-configured pipelines for common use cases
default_pipeline = DataPipeline()
advice_pipeline = DataPipeline(include_analysis=True)
