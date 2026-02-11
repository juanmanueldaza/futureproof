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

    def generate_all_cvs(self) -> list[Path]:
        """Generate all CV variants (all languages and formats).

        Generates all 4 combinations (2 languages x 2 formats).
        Continues on error to try all variants.

        Returns:
            List of paths to successfully generated files
        """
        from ..generators import CVGenerator

        generator = CVGenerator()
        paths: list[Path] = []

        for language in ("en", "es"):
            for cv_format in ("ats", "creative"):
                try:
                    path = generator.generate(
                        language=language,  # type: ignore[arg-type]
                        format=cv_format,  # type: ignore[arg-type]
                    )
                    paths.append(path)
                except Exception:
                    pass  # Continue with other variants

        return paths
