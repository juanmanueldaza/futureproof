"""CliftonStrengths assessment gatherer.

Extracts and processes Gallup CliftonStrengths assessment data from PDF reports.
Supports multiple report types:
- Top 5 (SF_TOP_5)
- Top 10 (TOP_10)
- All 34 (ALL_34)
- Action Planning (ACTION_PLANNING_TOP_10)
- Leadership Insight (LEADERSHIP_INSIGHT_TOP_10)
- Discovery Development (DISCOVERY_DEVELOPMENT)
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .base import BaseGatherer

logger = logging.getLogger(__name__)

# CliftonStrengths domains
DOMAINS = {
    "EXECUTING": [
        "Achiever",
        "Arranger",
        "Belief",
        "Consistency",
        "Deliberative",
        "Discipline",
        "Focus",
        "Responsibility",
        "Restorative",
    ],
    "INFLUENCING": [
        "Activator",
        "Command",
        "Communication",
        "Competition",
        "Maximizer",
        "Self-Assurance",
        "Significance",
        "Woo",
    ],
    "RELATIONSHIP BUILDING": [
        "Adaptability",
        "Connectedness",
        "Developer",
        "Empathy",
        "Harmony",
        "Includer",
        "Individualization",
        "Positivity",
        "Relator",
    ],
    "STRATEGIC THINKING": [
        "Analytical",
        "Context",
        "Futuristic",
        "Ideation",
        "Input",
        "Intellection",
        "Learner",
        "Strategic",
    ],
}

# Reverse lookup: strength -> domain
STRENGTH_TO_DOMAIN = {
    strength: domain for domain, strengths in DOMAINS.items() for strength in strengths
}


@dataclass
class StrengthInsight:
    """Parsed insight for a single strength."""

    rank: int
    name: str
    domain: str
    description: str = ""
    unique_insights: list[str] = field(default_factory=list)
    why_succeed: str = ""
    action_items: list[str] = field(default_factory=list)
    blind_spots: list[str] = field(default_factory=list)


@dataclass
class CliftonStrengthsData:
    """Parsed CliftonStrengths assessment data."""

    name: str = ""
    date: str = ""
    top_5: list[StrengthInsight] = field(default_factory=list)
    top_10: list[StrengthInsight] = field(default_factory=list)
    all_34: list[str] = field(default_factory=list)
    dominant_domain: str = ""
    raw_text: dict[str, str] = field(default_factory=dict)


class CliftonStrengthsGatherer(BaseGatherer):
    """Gather and process CliftonStrengths assessment data from PDFs.

    Extracts structured data from Gallup CliftonStrengths PDF reports
    and generates a comprehensive markdown summary for career analysis.
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        """Initialize the gatherer.

        Args:
            output_dir: Directory for output files. Defaults to data/processed/assessment
        """
        from ..config import settings

        self.output_dir = output_dir or (settings.data_dir / "processed" / "assessment")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def gather(self, input_dir: Path | None = None) -> Path:
        """Gather CliftonStrengths data from PDF files.

        Args:
            input_dir: Directory containing Gallup PDF files.
                      Defaults to data/raw

        Returns:
            Path to generated markdown file
        """
        from ..config import settings

        input_dir = input_dir or (settings.data_dir / "raw")

        logger.info(f"Gathering CliftonStrengths data from {input_dir}")

        # Find all Gallup PDF files
        pdf_files = list(input_dir.glob("*.pdf"))
        gallup_pdfs = [p for p in pdf_files if self._is_gallup_pdf(p)]

        if not gallup_pdfs:
            raise FileNotFoundError(f"No Gallup CliftonStrengths PDFs found in {input_dir}")

        logger.info(f"Found {len(gallup_pdfs)} Gallup PDF files")

        # Parse all PDFs
        data = CliftonStrengthsData()

        for pdf_path in gallup_pdfs:
            self._parse_pdf(pdf_path, data)

        # Determine dominant domain from top 5
        if data.top_5:
            domain_counts: dict[str, int] = {}
            for strength in data.top_5:
                domain_counts[strength.domain] = domain_counts.get(strength.domain, 0) + 1
            data.dominant_domain = max(domain_counts, key=lambda d: domain_counts[d])

        # Generate markdown
        output_path = self.output_dir / "cliftonstrengths.md"
        markdown = self._generate_markdown(data)
        output_path.write_text(markdown)

        logger.info(f"CliftonStrengths data saved to {output_path}")
        return output_path

    def _is_gallup_pdf(self, path: Path) -> bool:
        """Check if a PDF is a Gallup CliftonStrengths report."""
        name = path.name.lower()
        gallup_indicators = [
            "top_5",
            "top_10",
            "all_34",
            "action_planning",
            "leadership_insight",
            "discovery_development",
            "sf_top",
            "cliftonstrengths",
            "strengthsfinder",
        ]
        return any(indicator in name for indicator in gallup_indicators)

    def _extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF using pdftotext."""
        try:
            result = subprocess.run(
                ["pdftotext", "-layout", str(pdf_path), "-"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout
            else:
                logger.warning(f"pdftotext failed for {pdf_path}: {result.stderr}")
                return ""
        except FileNotFoundError:
            logger.error("pdftotext not found. Install poppler-utils.")
            raise
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout extracting text from {pdf_path}")
            return ""

    def _parse_pdf(self, pdf_path: Path, data: CliftonStrengthsData) -> None:
        """Parse a single PDF and update the data object."""
        filename = pdf_path.name.upper()
        text = self._extract_text(pdf_path)

        if not text:
            logger.warning(f"No text extracted from {pdf_path}")
            return

        # Store raw text by report type
        report_type = self._get_report_type(filename)
        data.raw_text[report_type] = text

        # Extract name and date
        name_match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*\|\s*(\d{2}-\d{2}-\d{4})", text)
        if name_match and not data.name:
            data.name = name_match.group(1).strip()
            data.date = name_match.group(2).strip()

        # Parse based on report type
        if "ALL_34" in filename:
            self._parse_all_34(text, data)
        elif "TOP_5" in filename or "SF_TOP" in filename:
            self._parse_top_5(text, data)
        elif "TOP_10" in filename:
            self._parse_top_10(text, data)

    def _get_report_type(self, filename: str) -> str:
        """Determine report type from filename."""
        if "ALL_34" in filename:
            return "all_34"
        elif "SF_TOP_5" in filename or "TOP_5" in filename.replace("TOP_10", ""):
            return "top_5"
        elif "TOP_10" in filename:
            return "top_10"
        elif "ACTION_PLANNING" in filename:
            return "action_planning"
        elif "LEADERSHIP" in filename:
            return "leadership"
        elif "DISCOVERY" in filename:
            return "discovery"
        return "unknown"

    def _parse_all_34(self, text: str, data: CliftonStrengthsData) -> None:
        """Parse the All 34 report for complete strength ranking."""
        # Look for the ranked list pattern
        # Pattern: number. StrengthName
        strength_pattern = r"(\d{1,2})\.\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)"

        matches = re.findall(strength_pattern, text)

        # Build ordered list
        strengths_found: dict[int, str] = {}
        for rank_str, name in matches:
            rank = int(rank_str)
            # Normalize strength name
            name = name.strip()
            if name in STRENGTH_TO_DOMAIN and rank not in strengths_found:
                strengths_found[rank] = name

        # Sort by rank and store
        data.all_34 = [
            strengths_found[i] for i in sorted(strengths_found.keys()) if i in strengths_found
        ]

        # Also populate top_5 and top_10 if not already done
        if not data.top_5 and len(data.all_34) >= 5:
            for i, name in enumerate(data.all_34[:5], 1):
                insight = StrengthInsight(
                    rank=i,
                    name=name,
                    domain=STRENGTH_TO_DOMAIN.get(name, "Unknown"),
                )
                data.top_5.append(insight)

        if not data.top_10 and len(data.all_34) >= 10:
            for i, name in enumerate(data.all_34[:10], 1):
                insight = StrengthInsight(
                    rank=i,
                    name=name,
                    domain=STRENGTH_TO_DOMAIN.get(name, "Unknown"),
                )
                data.top_10.append(insight)

        # Parse detailed insights for each strength
        self._parse_strength_details(text, data)

    def _parse_top_5(self, text: str, data: CliftonStrengthsData) -> None:
        """Parse Top 5 report."""
        if data.top_5:
            # Already parsed from ALL_34
            return

        # Pattern for top 5 list
        strength_pattern = r"(\d)\.\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*®?"

        matches = re.findall(strength_pattern, text)
        seen_ranks: set[int] = set()

        for rank_str, name in matches:
            rank = int(rank_str)
            name = name.strip()
            if name in STRENGTH_TO_DOMAIN and rank not in seen_ranks and rank <= 5:
                seen_ranks.add(rank)
                insight = StrengthInsight(
                    rank=rank,
                    name=name,
                    domain=STRENGTH_TO_DOMAIN.get(name, "Unknown"),
                )
                data.top_5.append(insight)

        data.top_5.sort(key=lambda x: x.rank)
        self._parse_strength_details(text, data)

    def _parse_top_10(self, text: str, data: CliftonStrengthsData) -> None:
        """Parse Top 10 report."""
        if data.top_10:
            return

        strength_pattern = r"(\d{1,2})\.\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)"

        matches = re.findall(strength_pattern, text)
        seen_ranks: set[int] = set()

        for rank_str, name in matches:
            rank = int(rank_str)
            name = name.strip()
            if name in STRENGTH_TO_DOMAIN and rank not in seen_ranks and rank <= 10:
                seen_ranks.add(rank)
                insight = StrengthInsight(
                    rank=rank,
                    name=name,
                    domain=STRENGTH_TO_DOMAIN.get(name, "Unknown"),
                )
                data.top_10.append(insight)

        data.top_10.sort(key=lambda x: x.rank)
        self._parse_strength_details(text, data)

    def _parse_strength_details(self, text: str, data: CliftonStrengthsData) -> None:
        """Parse detailed insights for each strength from text."""
        # Split text into sections by strength headers
        # Pattern matches "N. StrengthName" at the start of a strength section
        strength_sections = self._split_into_strength_sections(text)

        # For each strength in top_5, try to find its details
        for insight in data.top_5:
            section_key = f"{insight.rank}. {insight.name}"
            section = strength_sections.get(section_key, "")

            if not section:
                # Try alternate key formats
                for key in strength_sections:
                    if insight.name.lower() in key.lower():
                        section = strength_sections[key]
                        break

            if section:
                self._extract_strength_insight(section, insight)

    def _split_into_strength_sections(self, text: str) -> dict[str, str]:
        """Split text into sections keyed by strength name."""
        sections: dict[str, str] = {}

        # Find all strength section headers (e.g., "1. Learner", "2. Woo")
        # These appear as headers in the Gallup PDFs
        header_pattern = r"(\d+)\.\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*®?"

        matches = list(re.finditer(header_pattern, text))

        for i, match in enumerate(matches):
            rank = match.group(1)
            name = match.group(2)
            start = match.end()

            # End is either the next match or end of text
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(text)

            section_text = text[start:end]
            key = f"{rank}. {name}"

            # Only store if this section has meaningful content
            if "HOW YOU CAN THRIVE" in section_text or "WHY YOU SUCCEED" in section_text:
                sections[key] = section_text

        return sections

    def _extract_strength_insight(self, section: str, insight: StrengthInsight) -> None:
        """Extract insight details from a strength section."""
        # Extract description (after "HOW YOU CAN THRIVE")
        desc_match = re.search(
            r"HOW YOU CAN THRIVE\s*(.*?)(?:WHY YOUR|$)",
            section,
            re.DOTALL | re.IGNORECASE,
        )
        if desc_match:
            insight.description = self._clean_text(desc_match.group(1))

        # Extract "WHY YOU SUCCEED" section
        succeed_match = re.search(
            r"WHY YOU SUCCEED.*?\n\s*(.*?)(?:TAKE ACTION|$)",
            section,
            re.DOTALL | re.IGNORECASE,
        )
        if succeed_match:
            insight.why_succeed = self._clean_text(succeed_match.group(1))

        # Extract action items (bullet points after TAKE ACTION)
        action_match = re.search(
            r"TAKE ACTION.*?\n(.*?)(?:WATCH OUT|$)",
            section,
            re.DOTALL | re.IGNORECASE,
        )
        if action_match:
            items = re.findall(r"[•●]\s*(.+?)(?=[•●]|$)", action_match.group(1), re.DOTALL)
            insight.action_items = [self._clean_text(item) for item in items if item.strip()]

        # Extract blind spots
        blind_match = re.search(
            r"WATCH OUT FOR BLIND SPOTS\s*(.*?)(?=\d+\.\s+[A-Z]|StrengthsFinder|$)",
            section,
            re.DOTALL | re.IGNORECASE,
        )
        if blind_match:
            items = re.findall(r"[•●]\s*(.+?)(?=[•●]|$)", blind_match.group(1), re.DOTALL)
            insight.blind_spots = [self._clean_text(item) for item in items if item.strip()]

    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing extra whitespace."""
        # Remove multiple spaces and newlines
        text = re.sub(r"\s+", " ", text)
        # Remove page numbers and copyright
        text = re.sub(r"StrengthsFinder.*?reserved\.", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\d+\s*$", "", text)
        return text.strip()

    def _generate_markdown(self, data: CliftonStrengthsData) -> str:
        """Generate markdown from parsed CliftonStrengths data."""
        lines = ["# CliftonStrengths Assessment\n"]

        # Header info
        if data.name:
            lines.append(f"**Name:** {data.name}")
        if data.date:
            lines.append(f"**Assessment Date:** {data.date}")
        if data.dominant_domain:
            lines.append(f"**Dominant Domain:** {data.dominant_domain}")
        lines.append("")

        # Top 5 Summary
        lines.append("## Top 5 Signature Themes\n")
        lines.append("| Rank | Strength | Domain |")
        lines.append("|------|----------|--------|")
        for insight in data.top_5:
            lines.append(f"| {insight.rank} | **{insight.name}** | {insight.domain} |")
        lines.append("")

        # Domain distribution
        if data.top_5:
            lines.append("### Domain Distribution (Top 5)\n")
            domain_counts: dict[str, list[str]] = {}
            for insight in data.top_5:
                domain_counts.setdefault(insight.domain, []).append(insight.name)
            for domain, strengths in domain_counts.items():
                lines.append(f"- **{domain}:** {', '.join(strengths)}")
            lines.append("")

        # Detailed insights for top 5
        lines.append("## Detailed Strength Insights\n")
        for insight in data.top_5:
            lines.append(f"### {insight.rank}. {insight.name} ({insight.domain})\n")

            if insight.description:
                lines.append(f"**Description:** {insight.description}\n")

            if insight.why_succeed:
                lines.append(f"**Why You Succeed:** {insight.why_succeed}\n")

            if insight.action_items:
                lines.append("**Action Items:**")
                for item in insight.action_items[:3]:  # Limit to top 3
                    lines.append(f"- {item}")
                lines.append("")

            if insight.blind_spots:
                lines.append("**Blind Spots to Watch:**")
                for item in insight.blind_spots[:2]:  # Limit to top 2
                    lines.append(f"- {item}")
                lines.append("")

        # Top 10 (6-10 only)
        if data.top_10 and len(data.top_10) > 5:
            lines.append("## Supporting Strengths (6-10)\n")
            lines.append("| Rank | Strength | Domain |")
            lines.append("|------|----------|--------|")
            for insight in data.top_10[5:]:
                lines.append(f"| {insight.rank} | {insight.name} | {insight.domain} |")
            lines.append("")

        # Full 34 ranking
        if data.all_34:
            lines.append("## Complete Strength Ranking (All 34)\n")

            # Group into sections
            lines.append("### Strengthen (1-10)")
            lines.append(
                ", ".join(f"**{s}**" if i < 5 else s for i, s in enumerate(data.all_34[:10]))
            )
            lines.append("")

            lines.append("### Navigate (11-23)")
            lines.append(", ".join(data.all_34[10:23]))
            lines.append("")

            lines.append("### Lesser Themes (24-34)")
            lines.append(", ".join(data.all_34[23:]))
            lines.append("")

        # Career insights summary
        lines.append("## Career Alignment Insights\n")
        lines.append("Based on your CliftonStrengths profile:\n")

        if data.dominant_domain == "STRATEGIC THINKING":
            lines.append("- **Natural Fit:** Strategy, analysis, research, planning roles")
            value = "Pattern recognition, informed decisions, big-picture thinking"
            lines.append(f"- **Value to Teams:** {value}")
        elif data.dominant_domain == "INFLUENCING":
            lines.append("- **Natural Fit:** Leadership, sales, marketing, public speaking roles")
            lines.append("- **Value to Teams:** Taking charge, driving action, persuading others")
        elif data.dominant_domain == "RELATIONSHIP BUILDING":
            lines.append("- **Natural Fit:** HR, coaching, team leadership, customer success roles")
            lines.append(
                "- **Value to Teams:** Building trust, creating cohesion, developing others"
            )
        elif data.dominant_domain == "EXECUTING":
            lines.append("- **Natural Fit:** Project management, operations, implementation roles")
            lines.append("- **Value to Teams:** Getting things done, reliability, follow-through")

        # Add specific strength-based insights
        strength_names = [s.name for s in data.top_5]
        if "Learner" in strength_names:
            lines.append(
                "- **Growth Orientation:** Thrives in roles with continuous learning opportunities"
            )
        if "Activator" in strength_names:
            lines.append(
                "- **Action Bias:** Excels in fast-paced environments requiring quick decisions"
            )
        if "Strategic" in strength_names:
            lines.append(
                "- **Problem Solving:** Natural ability to see patterns and find optimal paths"
            )
        if "Woo" in strength_names:
            lines.append(
                "- **Networking:** Excellent at building new relationships and connections"
            )
        if "Ideation" in strength_names:
            lines.append("- **Innovation:** Generates creative solutions and novel approaches")
        if "Individualization" in strength_names:
            lines.append(
                "- **Team Building:** Skilled at recognizing and leveraging individual talents"
            )

        lines.append("")

        return "\n".join(lines)
