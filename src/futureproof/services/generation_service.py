"""Generation service - CV and content generation.

Single responsibility: Generate CVs in various formats and languages.
"""

from pathlib import Path
from typing import Literal

from .exceptions import GenerationError


class GenerationService:
    """Service for CV generation operations.

    Encapsulates CV generation logic, making it testable and reusable.
    """

    def generate_cv(
        self,
        language: Literal["en", "es"] = "en",
        format: Literal["ats", "creative"] = "ats",
    ) -> Path:
        """Generate CV and return path to output file.

        Args:
            language: Output language ("en" or "es")
            format: CV format ("ats" or "creative")

        Returns:
            Path to generated CV file

        Raises:
            GenerationError: If generation fails
        """
        from ..generators import CVGenerator

        try:
            generator = CVGenerator()
            output_path = generator.generate(language=language, format=format)
            return output_path
        except Exception as e:
            raise GenerationError(f"CV generation failed: {e}") from e
