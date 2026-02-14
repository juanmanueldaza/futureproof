"""CV generator using LLM."""

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from ..config import settings
from ..llm.fallback import get_model_with_fallback
from ..prompts import GENERATE_CV_PROMPT
from ..utils.console import console
from ..utils.data_loader import combine_career_data, load_career_data_for_cv
from ..utils.security import anonymize_career_data

logger = logging.getLogger(__name__)


def render_pdf(markdown_path: Path) -> Path:
    """Convert markdown to styled PDF.

    Args:
        markdown_path: Path to the markdown file to convert

    Returns:
        Path to the generated PDF, or markdown_path if PDF is unavailable.
    """
    try:
        import markdown
        from weasyprint import HTML

        md_content = markdown_path.read_text()

        html_content = markdown.markdown(
            md_content,
            extensions=["tables", "fenced_code"],
        )

        styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px;
            color: #333;
        }}
        h1 {{
            font-size: 24pt;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            font-size: 14pt;
            color: #555;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
            margin-top: 25px;
        }}
        h3 {{
            font-size: 12pt;
            color: #666;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 5px;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        .contact {{
            color: #666;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""

        pdf_path = markdown_path.with_suffix(".pdf")
        HTML(string=styled_html).write_pdf(pdf_path)
        os.chmod(pdf_path, 0o600)  # Owner read/write only
        console.print(f"  [dim]PDF generated: {pdf_path}[/dim]")
        return pdf_path

    except ImportError as e:
        console.print(f"  [yellow]PDF generation skipped: {e}[/yellow]")
        return markdown_path
    except Exception as e:
        console.print(f"  [yellow]PDF generation failed: {e}[/yellow]")
        return markdown_path


class CVGenerator:
    """Generate CVs in multiple languages and formats."""

    def __init__(
        self,
        llm_factory: Callable[..., tuple] | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.output_dir = output_dir or settings.output_dir
        self._llm_factory = llm_factory or get_model_with_fallback

    def _generate_with_llm(
        self,
        career_data: str,
        language: Literal["en", "es"],
        format: Literal["ats", "creative"],
    ) -> str:
        """Generate CV content using LLM."""
        model, _config = self._llm_factory(temperature=settings.cv_temperature, purpose="analysis")

        lang_instruction = {
            "en": "Generate the CV in English.",
            "es": "Generate the CV in Spanish (Español). All content should be in Spanish.",
        }

        format_instruction = {
            "ats": """Focus on ATS optimization:
- Use standard section headers
- Include keywords naturally
- Simple, clean formatting
- No tables or columns""",
            "creative": """Use a more creative format:
- Compelling narrative in summary
- Highlight unique achievements
- Show personality while remaining professional""",
        }

        # Anonymize PII before sending to external LLM
        # For CV generation, we preserve professional email domains for context
        safe_career_data = anonymize_career_data(career_data, preserve_professional_emails=True)

        prompt = f"""{GENERATE_CV_PROMPT}

{lang_instruction[language]}

{format_instruction[format]}

CAREER DATA:
{safe_career_data}

Generate a complete, professional CV in Markdown format."""

        try:
            response = model.invoke(prompt)
            return str(response.content)
        except Exception:
            # Log full error, show sanitized message to user
            logger.exception("LLM invocation failed")
            console.print("[red]CV generation failed. Check logs for details.[/red]")
            raise

    def generate(
        self,
        language: Literal["en", "es"] = "en",
        format: Literal["ats", "creative"] = "ats",
        state: dict[str, Any] | None = None,
    ) -> Path:
        """
        Generate CV in specified language and format.

        Args:
            language: Output language (en or es)
            format: CV format (ats or creative)
            state: Optional state dict with pre-loaded data

        Returns:
            Path to generated CV file
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load data from state or files
        if state:
            career_data = combine_career_data(state, header_prefix="###")
        else:
            career_data = load_career_data_for_cv()

        if not career_data:
            console.print("[yellow]No career data found. Run 'gather' first.[/yellow]")
            return Path()

        console.print(f"  Generating {language}/{format} CV...")

        # Generate content
        cv_content = self._generate_with_llm(career_data, language, format)

        # Save markdown with secure permissions
        filename = f"cv_{language}_{format}.md"
        output_path = self.output_dir / filename
        output_path.write_text(cv_content)
        os.chmod(output_path, 0o600)  # Owner read/write only
        console.print(f"  [dim]Markdown saved: {output_path}[/dim]")

        # Convert to PDF
        render_pdf(output_path)

        return output_path
