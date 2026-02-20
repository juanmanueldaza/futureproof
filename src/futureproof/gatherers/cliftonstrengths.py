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

logger = logging.getLogger(__name__)

# Filename indicators for detecting Gallup CliftonStrengths PDFs
GALLUP_PDF_INDICATORS = [
    "top_5",
    "top_10",
    "all_34",
    "action_planning",
    "leadership_insight",
    "discovery_development",
    "sf_top",
    "cliftonstrengths",
    "strengthsfinder",
    "gallup",
]

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
    sounds_like_quotes: list[str] = field(default_factory=list)


@dataclass
class CliftonStrengthsData:
    """Parsed CliftonStrengths assessment data."""

    name: str = ""
    date: str = ""
    top_5: list[StrengthInsight] = field(default_factory=list)
    top_10: list[StrengthInsight] = field(default_factory=list)
    all_34: list[str] = field(default_factory=list)
    dominant_domain: str = ""


class CliftonStrengthsGatherer:
    """Gather and process CliftonStrengths assessment data from PDFs.

    Extracts structured data from Gallup CliftonStrengths PDF reports
    and generates a comprehensive markdown summary for career analysis.
    """

    def gather(self, input_dir: Path | None = None) -> str:
        """Gather CliftonStrengths data from PDF files.

        Args:
            input_dir: Directory containing Gallup PDF files.
                      Defaults to data/raw

        Returns:
            Markdown content string (indexed directly to ChromaDB by caller)
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
        markdown = self._generate_markdown(data)

        logger.info("CliftonStrengths data gathered successfully")
        return markdown

    def _is_gallup_pdf(self, path: Path) -> bool:
        """Check if a PDF is a Gallup CliftonStrengths report."""
        name = path.name.lower()
        return any(indicator in name for indicator in GALLUP_PDF_INDICATORS)

    def _extract_ranked_strengths(self, text: str, max_rank: int = 34) -> list[StrengthInsight]:
        """Extract ranked strengths from text into StrengthInsight objects.

        Parses "N. StrengthName" patterns, filters valid CliftonStrengths names,
        deduplicates by rank, and returns sorted results.

        Args:
            text: Text containing ranked strength patterns
            max_rank: Maximum rank to include (5 for top_5, 10 for top_10, etc.)

        Returns:
            Sorted list of StrengthInsight objects
        """
        pattern = r"(\d{1,2})\.\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)"
        matches = re.findall(pattern, text)
        seen: set[int] = set()
        results: list[StrengthInsight] = []

        for rank_str, name in matches:
            rank = int(rank_str)
            name = name.strip()
            if name in STRENGTH_TO_DOMAIN and rank not in seen and rank <= max_rank:
                seen.add(rank)
                results.append(
                    StrengthInsight(
                        rank=rank,
                        name=name,
                        domain=STRENGTH_TO_DOMAIN.get(name, "Unknown"),
                    )
                )

        results.sort(key=lambda x: x.rank)
        return results

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

        report_type = self._get_report_type(filename)

        # Extract name and date
        name_match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*\|\s*(\d{2}-\d{2}-\d{4})", text)
        if name_match and not data.name:
            data.name = name_match.group(1).strip()
            data.date = name_match.group(2).strip()

        # Parse based on report type (specific types before generic TOP_10)
        if report_type == "all_34":
            self._parse_all_34(text, data)
        elif report_type == "top_5":
            self._parse_top_5(text, data)
        elif report_type == "action_planning":
            self._parse_action_planning(text, data)
        elif report_type == "leadership":
            self._parse_leadership_insight(text, data)
        elif report_type == "discovery":
            self._parse_discovery_development(text, data)
        elif report_type == "top_10":
            self._parse_top_10(text, data)

    def _get_report_type(self, filename: str) -> str:
        """Determine report type from filename."""
        if "ALL_34" in filename:
            return "all_34"
        elif "SF_TOP_5" in filename or "TOP_5" in filename.replace("TOP_10", ""):
            return "top_5"
        # Specific TOP_10 variants must be checked BEFORE generic TOP_10
        elif "ACTION_PLANNING" in filename:
            return "action_planning"
        elif "LEADERSHIP" in filename:
            return "leadership"
        elif "DISCOVERY" in filename:
            return "discovery"
        elif "TOP_10" in filename:
            return "top_10"
        return "unknown"

    def _parse_all_34(self, text: str, data: CliftonStrengthsData) -> None:
        """Parse the All 34 report for complete strength ranking."""
        all_strengths = self._extract_ranked_strengths(text)
        data.all_34 = [s.name for s in all_strengths]

        # Also populate top_5 and top_10 if not already done
        if not data.top_5 and len(data.all_34) >= 5:
            data.top_5 = list(all_strengths[:5])

        if not data.top_10 and len(data.all_34) >= 10:
            data.top_10 = list(all_strengths[:10])

        # Parse detailed insights for each strength
        self._parse_strength_details(text, data)

    def _parse_top_5(self, text: str, data: CliftonStrengthsData) -> None:
        """Parse Top 5 report."""
        if data.top_5:
            return

        data.top_5 = self._extract_ranked_strengths(text, max_rank=5)
        self._parse_strength_details(text, data)

    def _parse_top_10(self, text: str, data: CliftonStrengthsData) -> None:
        """Parse Top 10 report."""
        if data.top_10:
            return

        data.top_10 = self._extract_ranked_strengths(text, max_rank=10)
        self._parse_strength_details(text, data)

    # -----------------------------------------------------------------
    # Action Planning / Leadership / Discovery parsers
    # -----------------------------------------------------------------

    def _ensure_top_10(self, text: str, data: CliftonStrengthsData) -> None:
        """Populate top_10 from a ranked list in text if not already done."""
        if data.top_10:
            return
        data.top_10 = self._extract_ranked_strengths(text, max_rank=10)
        if not data.top_5 and len(data.top_10) >= 5:
            data.top_5 = list(data.top_10[:5])

    def _split_personalized_insights(self, text: str) -> list[str]:
        """Split personalized insights text into individual paragraphs.

        Each paragraph typically starts with one of these openers:
        "Chances are good that", "Driven by your talents", etc.
        """
        openers = [
            r"Chances are good that",
            r"Driven by your talents",
            r"Because of your strengths",
            r"It's very likely that",
            r"Instinctively",
            r"By nature",
        ]
        pattern = r"(?=" + "|".join(openers) + r")"
        parts = re.split(pattern, text)
        return [p.strip() for p in parts if p.strip() and len(p.strip()) > 30]

    def _clean_copyright(self, text: str) -> str:
        """Remove copyright lines and page numbers from extracted PDF text."""
        text = re.sub(
            r"\d*\s*\n?\s*StrengthsFinder.*?reserved\.\s*\n?",
            " ",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(r"101360652.*?\n", " ", text)
        text = re.sub(r"®", "", text)
        return text

    def _parse_action_planning(self, text: str, data: CliftonStrengthsData) -> None:
        """Parse Action Planning Top 10 report.

        Extracts three types of unique content:
        - Section I: Personalized Strengths Insights (unique_insights)
        - Section II: 10 Ideas for Action per strength (action_items)
        - Section III: "Sounds Like This" quotes (sounds_like_quotes)
        """
        self._ensure_top_10(text, data)
        self._parse_ap_personalized_insights(text, data)
        self._parse_ap_ideas_for_action(text, data)
        self._parse_ap_sounds_like(text, data)

    def _parse_ap_personalized_insights(
        self,
        text: str,
        data: CliftonStrengthsData,
    ) -> None:
        """Parse Section I — personalized insights for each strength."""
        section_i = re.search(r"Section I:\s*Awareness", text)
        section_ii = re.search(r"Section II:\s*Application", text)
        if not section_i:
            return

        start = section_i.end()
        end = section_ii.start() if section_ii else len(text)
        section_text = self._clean_copyright(text[start:end])

        for insight in data.top_10:
            # Find this strength's personalized insights block
            pattern = re.compile(
                rf"{re.escape(insight.name)}\s*\n.*?"
                r"YOUR PERSONALIZED STRENGTHS INSIGHTS",
                re.DOTALL | re.IGNORECASE,
            )
            match = pattern.search(section_text)
            if not match:
                continue

            # Extract from after "What makes you stand out?" to next "QUESTIONS"
            block_start = match.end()
            # Skip the "What makes you stand out?" header if present
            standout = re.search(
                r"What makes you stand out\?",
                section_text[block_start:],
            )
            if standout and standout.start() < 50:
                block_start += standout.end()

            questions_pos = section_text.find("QUESTIONS", block_start)
            if questions_pos == -1:
                questions_pos = len(section_text)

            raw = section_text[block_start:questions_pos]
            paragraphs = self._split_personalized_insights(raw)
            if paragraphs:
                insight.unique_insights = [self._clean_text(p) for p in paragraphs]

    def _parse_ap_ideas_for_action(
        self,
        text: str,
        data: CliftonStrengthsData,
    ) -> None:
        """Parse Section II — 10 Ideas for Action per strength."""
        section_ii = re.search(r"Section II:\s*Application", text)
        section_iii = re.search(r"Section III:\s*Achievement", text)
        if not section_ii:
            return

        start = section_ii.end()
        end = section_iii.start() if section_iii else len(text)
        section_text = self._clean_copyright(text[start:end])

        for insight in data.top_10:
            # Find "StrengthName\nIDEAS FOR ACTION"
            pattern = re.compile(
                rf"(?:^|\n)\s*{re.escape(insight.name)}\s*\n\s*IDEAS FOR ACTION",
                re.IGNORECASE,
            )
            match = pattern.search(section_text)
            if not match:
                continue

            # Extract from after "IDEAS FOR ACTION" to next "QUESTIONS"
            ideas_start = section_text.find("IDEAS FOR ACTION", match.start())
            ideas_start = section_text.find("\n", ideas_start) + 1

            questions_pos = section_text.find("QUESTIONS", ideas_start)
            if questions_pos == -1:
                questions_pos = len(section_text)

            raw = section_text[ideas_start:questions_pos]

            # Split into individual action items by paragraph breaks
            items = [
                self._clean_text(item)
                for item in re.split(r"\n\s*\n", raw)
                if item.strip() and len(item.strip()) > 30
            ]

            # Replace existing (3 from ALL_34) with the richer set
            if items:
                insight.action_items = items

    def _parse_ap_sounds_like(
        self,
        text: str,
        data: CliftonStrengthsData,
    ) -> None:
        """Parse Section III — 'Sounds Like This' real quotes per strength."""
        section_iii = re.search(r"Section III:\s*Achievement", text)
        if not section_iii:
            return

        section_text = self._clean_copyright(text[section_iii.end() :])

        for insight in data.top_10:
            # Find "[STRENGTH] SOUNDS LIKE THIS:"
            pattern = re.compile(
                rf"{re.escape(insight.name.upper())}\s+SOUNDS LIKE THIS:",
                re.IGNORECASE,
            )
            match = pattern.search(section_text)
            if not match:
                continue

            # Find end: next "SOUNDS LIKE THIS:" or "QUESTIONS" or end
            remaining = section_text[match.end() :]
            next_marker = re.search(
                r"[A-Z][A-Z-]+\s+SOUNDS LIKE THIS:|QUESTIONS",
                remaining,
            )
            raw = remaining[: next_marker.start()] if next_marker else remaining

            # Split into individual quotes by attribution pattern:
            # "FirstName L., title:"
            quote_splits = re.split(
                r"(?=\n[A-Z][a-z]+\s+[A-Z]\.?,\s+)",
                raw,
            )
            quotes = []
            for part in quote_splits:
                cleaned = self._clean_text(part)
                if cleaned and len(cleaned) > 40:
                    quotes.append(cleaned)

            if quotes:
                insight.sounds_like_quotes = quotes

    def _parse_leadership_insight(
        self,
        text: str,
        data: CliftonStrengthsData,
    ) -> None:
        """Parse Leadership Insight report (fallback for personalized insights).

        Only extracts if Action Planning hasn't already populated unique_insights.
        """
        self._ensure_top_10(text, data)

        # Skip if insights already populated by Action Planning
        if any(s.unique_insights for s in data.top_10):
            logger.debug(
                "Personalized insights already populated, skipping Leadership Insight",
            )
            return

        # Find "Your Personalized Strengths Insights" header
        header = re.search(r"Your Personalized Strengths Insights", text)
        if not header:
            return

        section_text = self._clean_copyright(text[header.end() :])

        for i, insight in enumerate(data.top_10):
            # Headers are "STRENGTH ®" (uppercase)
            pattern = re.compile(
                rf"{re.escape(insight.name.upper())}\s+",
                re.IGNORECASE,
            )
            match = pattern.search(section_text)
            if not match:
                continue

            # Find end: next strength header or COPYRIGHT STANDARDS
            end_pos = len(section_text)
            if i + 1 < len(data.top_10):
                next_pattern = re.compile(
                    rf"{re.escape(data.top_10[i + 1].name.upper())}\s+",
                    re.IGNORECASE,
                )
                next_match = next_pattern.search(section_text[match.end() :])
                if next_match:
                    end_pos = match.end() + next_match.start()

            copyright_pos = section_text.find("COPYRIGHT STANDARDS", match.end())
            if copyright_pos != -1 and copyright_pos < end_pos:
                end_pos = copyright_pos

            raw = section_text[match.end() : end_pos]
            paragraphs = self._split_personalized_insights(raw)
            if paragraphs:
                insight.unique_insights = [self._clean_text(p) for p in paragraphs]

    def _parse_discovery_development(
        self,
        text: str,
        data: CliftonStrengthsData,
    ) -> None:
        """Parse Discovery Development report (fallback for action items, top 5 only).

        Only extracts if Action Planning hasn't already populated rich action items.
        """
        # Ensure top_5 exists
        if not data.top_5:
            # Extract from "StrengthName ®" headers
            strength_pattern = r"(\w+(?:-\w+)?)\s+®"
            matches = re.findall(strength_pattern, text)
            seen: set[str] = set()
            rank = 1
            for name in matches:
                name = name.strip()
                if name in STRENGTH_TO_DOMAIN and name not in seen and rank <= 5:
                    seen.add(name)
                    data.top_5.append(
                        StrengthInsight(
                            rank=rank,
                            name=name,
                            domain=STRENGTH_TO_DOMAIN.get(name, "Unknown"),
                        )
                    )
                    rank += 1

        # Skip if action items already rich (from Action Planning)
        if any(len(s.action_items) > 5 for s in data.top_5):
            logger.debug(
                "Rich action items already populated, skipping Discovery Development",
            )
            return

        section_text = self._clean_copyright(text)

        for insight in data.top_5:
            # Find "ACTION ITEMS" after strength name
            pattern = re.compile(
                rf"{re.escape(insight.name)}\s+.*?ACTION ITEMS\s*\n",
                re.DOTALL | re.IGNORECASE,
            )
            match = pattern.search(section_text)
            if not match:
                continue

            # Find end: next "StrengthName ®" header or end of text
            remaining = section_text[match.end() :]
            next_strength = re.search(r"\n\s*\w+(?:-\w+)?\s+®", remaining)
            raw = remaining[: next_strength.start()] if next_strength else remaining

            items = [
                self._clean_text(item)
                for item in re.split(r"\n\s*\n", raw)
                if item.strip() and len(item.strip()) > 30
            ]

            if items:
                insight.action_items = items

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
        text = re.sub(r"\s+", " ", text)
        text = self._clean_copyright(text)
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

        # Personalized talent patterns (from Action Planning / Leadership Insight)
        all_strengths = data.top_10 if data.top_10 else data.top_5
        has_personalized = any(s.unique_insights for s in all_strengths)
        if has_personalized:
            lines.append("## Personalized Talent Patterns\n")
            lines.append(
                "Your specific talent manifestations based on your unique"
                " CliftonStrengths combination:\n"
            )
            for insight in all_strengths:
                if insight.unique_insights:
                    lines.append(
                        f"### {insight.rank}. {insight.name} -- What Makes You Stand Out\n"
                    )
                    for paragraph in insight.unique_insights:
                        lines.append(f"{paragraph}\n")

        # Extended Ideas for Action (from Action Planning / Discovery Development)
        has_extended = any(len(s.action_items) > 3 for s in all_strengths)
        if has_extended:
            lines.append("## Extended Ideas for Action\n")
            lines.append("Comprehensive action items for developing each strength:\n")
            for insight in all_strengths:
                if len(insight.action_items) > 3:
                    lines.append(f"### {insight.rank}. {insight.name}\n")
                    for i, item in enumerate(insight.action_items, 1):
                        lines.append(f"{i}. {item}")
                    lines.append("")

        # Strengths in Practice — real-world quotes (from Action Planning)
        has_quotes = any(s.sounds_like_quotes for s in all_strengths)
        if has_quotes:
            lines.append("## Strengths in Practice\n")
            lines.append(
                "Real quotes from people who share your top themes,"
                " showing how these strengths manifest:\n"
            )
            for insight in all_strengths:
                if insight.sounds_like_quotes:
                    lines.append(f"### {insight.rank}. {insight.name}\n")
                    for quote in insight.sounds_like_quotes:
                        lines.append(f"> {quote}\n")

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

        return "\n".join(lines)
