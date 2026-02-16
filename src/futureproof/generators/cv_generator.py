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


def _clean_llm_output(text: str) -> str:
    """Clean LLM-generated CV content for PDF rendering.

    Strips code fences and trailing disclaimers that LLMs add on their own.
    """
    import re

    stripped = text.strip()

    # Strip wrapping code fences (```markdown ... ```)
    if stripped.startswith("```"):
        first_newline = stripped.index("\n")
        stripped = stripped[first_newline + 1 :]
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3].rstrip()

    # Remove trailing LLM disclaimers (italic or plain text about accuracy/assumptions)
    stripped = re.sub(
        r"\n+\*?This CV[^*\n]*\*?\s*$",
        "",
        stripped,
        flags=re.IGNORECASE,
    )

    # Remove stray trailing code fences (``` on its own line near end)
    stripped = re.sub(r"\n```\s*$", "", stripped)

    return stripped.rstrip()


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
    <link
      href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&display=swap"
      rel="stylesheet"
    >
    <style>
        @page {{
            size: A4;
            margin: 1.8cm 2.2cm;
        }}
        body {{
            font-family: 'Cormorant Garamond', Georgia, serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #2c2416;
            margin: 0;
            padding: 0;
        }}
        h1 {{
            font-size: 24pt;
            font-weight: 700;
            color: #0d1b2a;
            margin: 0 0 4px 0;
            letter-spacing: -0.5px;
        }}
        h1 + p {{
            color: #415a77;
            font-size: 11pt;
            margin-top: 0;
            margin-bottom: 2px;
        }}
        h1 + p + p {{
            color: #6b5c4c;
            font-size: 9.5pt;
            margin-top: 0;
        }}
        hr {{
            border: none;
            border-top: 1.5px solid #b8860b;
            margin: 14px 0;
        }}
        h2 {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 9.5pt;
            font-weight: 700;
            color: #0d1b2a;
            text-transform: uppercase;
            letter-spacing: 2px;
            border-bottom: 1.5px solid #b8860b;
            padding-bottom: 3px;
            margin-top: 16px;
            margin-bottom: 8px;
        }}
        h3 {{
            font-size: 11.5pt;
            font-weight: 600;
            color: #1b263b;
            margin-bottom: 1px;
            margin-top: 10px;
        }}
        h3 + p {{
            margin-top: 0;
            margin-bottom: 0;
        }}
        p {{
            margin: 4px 0;
        }}
        em {{
            font-style: italic;
            color: #6b5c4c;
            font-size: 9.5pt;
        }}
        strong {{
            font-weight: 600;
            color: #1b263b;
        }}
        ul {{
            padding-left: 16px;
            margin: 4px 0 8px 0;
        }}
        li {{
            margin-bottom: 2px;
            color: #3d3428;
            font-size: 10pt;
            line-height: 1.45;
        }}
        a {{
            color: #1b4f72;
            text-decoration: none;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 8px 0;
            font-size: 10pt;
        }}
        th {{
            text-align: left;
            font-weight: 600;
            border-bottom: 1.5px solid #b8860b;
            padding: 4px 8px;
            color: #0d1b2a;
        }}
        td {{
            padding: 3px 8px;
            border-bottom: 1px solid #d4c5a9;
            color: #3d3428;
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

        # Generate content and strip code fences if LLM wrapped the output
        cv_content = self._generate_with_llm(career_data, language, format)
        cv_content = _clean_llm_output(cv_content)

        # Save markdown with secure permissions
        filename = f"cv_{language}_{format}.md"
        output_path = self.output_dir / filename
        output_path.write_text(cv_content)
        os.chmod(output_path, 0o600)  # Owner read/write only
        console.print(f"  [dim]Markdown saved: {output_path}[/dim]")

        # Convert to PDF
        render_pdf(output_path)

        return output_path
