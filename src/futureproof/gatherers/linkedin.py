"""LinkedIn data gatherer — direct CSV parsing from ZIP export.

Parses 17 career-relevant CSV files organized in 3 tiers:
- Tier 1 (core): Profile, Positions, Education, Skills, Certifications,
  Languages, Projects, Recommendations, Endorsements
- Tier 2 (intelligence): Learning, Job Applications, Job Preferences,
  Posts/Shares, LinkedIn Inferences
- Tier 3 (network summary): Connections count, Companies Followed count

Returns a single markdown string for direct indexing to ChromaDB.
"""

import csv
import io
import logging
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from .base import BaseGatherer

logger = logging.getLogger(__name__)


def _read_csv(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    """Read a single CSV from a ZIP, returning rows as dicts."""
    try:
        with zf.open(name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8-sig")
            return list(csv.DictReader(text))
    except KeyError:
        logger.debug("CSV not found in ZIP: %s", name)
        return []
    except Exception as e:
        logger.warning("Error reading %s: %s", name, e)
        return []


def _read_csv_variants(zf: zipfile.ZipFile, base_name: str) -> list[dict[str, str]]:
    """Read a CSV and its numbered variants (e.g., Job Applications_1.csv).

    LinkedIn splits large CSVs into numbered files.
    """
    rows = _read_csv(zf, base_name)
    stem = Path(base_name).stem
    parent = str(Path(base_name).parent)
    suffix = Path(base_name).suffix

    # Try _1, _2, ... up to _10
    for i in range(1, 11):
        variant = f"{parent}/{stem}_{i}{suffix}" if parent != "." else f"{stem}_{i}{suffix}"
        extra = _read_csv(zf, variant)
        if not extra:
            break
        rows.extend(extra)

    return rows


def _get(row: dict[str, str], *keys: str) -> str:
    """Get the first non-empty value from a row by trying multiple keys."""
    for key in keys:
        val = row.get(key, "").strip()
        if val:
            return val
    return ""


# =============================================================================
# Tier 1 — Core Career Data
# =============================================================================


def _parse_profile(rows: list[dict[str, str]]) -> str:
    """Parse Profile.csv → markdown header with headline and summary."""
    if not rows:
        return ""
    row = rows[0]
    first = _get(row, "First Name")
    last = _get(row, "Last Name")
    name = f"{first} {last}".strip()
    headline = _get(row, "Headline")
    summary = _get(row, "Summary")
    industry = _get(row, "Industry")
    geo = _get(row, "Geo Location")

    parts = [f"# {name}"] if name else ["# LinkedIn Profile"]
    if headline:
        parts.append(headline)
    if industry or geo:
        details = " | ".join(filter(None, [industry, geo]))
        parts.append(f"_{details}_")
    if summary:
        parts.append(f"\n## Summary\n\n{summary}")
    return "\n\n".join(parts)


def _parse_positions(rows: list[dict[str, str]]) -> str:
    """Parse Positions.csv → Experience section."""
    if not rows:
        return ""
    lines = ["## Experience"]
    for row in rows:
        company = _get(row, "Company Name", "Company")
        title = _get(row, "Title")
        location = _get(row, "Location")
        started = _get(row, "Started On")
        finished = _get(row, "Finished On")
        description = _get(row, "Description")

        period = f"{started} – {finished}" if finished else f"{started} – Present"
        header = f"### {company}" if company else "### Position"
        entry = [header, f"**{title}**" if title else ""]
        if location:
            entry.append(f"_{location}_")
        if started:
            entry.append(f"_{period}_")
        if description:
            entry.append(f"\n{description}")
        lines.append("\n".join(filter(None, entry)))
    return "\n\n".join(lines)


def _parse_education(rows: list[dict[str, str]]) -> str:
    """Parse Education.csv → Education section."""
    if not rows:
        return ""
    lines = ["## Education"]
    for row in rows:
        school = _get(row, "School Name", "School")
        degree = _get(row, "Degree Name", "Degree")
        field = _get(row, "Field Of Study", "Fields of Study")
        start = _get(row, "Start Date")
        end = _get(row, "End Date")
        notes = _get(row, "Notes")
        activities = _get(row, "Activities and Societies", "Activities")

        header = f"### {school}" if school else "### Education"
        entry = [header]
        if degree or field:
            entry.append(f"**{degree}** — {field}" if field else f"**{degree}**")
        if start or end:
            entry.append(f"_{start} – {end}_")
        if notes:
            entry.append(notes)
        if activities:
            entry.append(f"Activities: {activities}")
        lines.append("\n".join(filter(None, entry)))
    return "\n\n".join(lines)


def _parse_skills(rows: list[dict[str, str]]) -> str:
    """Parse Skills.csv → Skills section."""
    if not rows:
        return ""
    skills = [_get(row, "Name") for row in rows if _get(row, "Name")]
    if not skills:
        return ""
    return f"## Skills\n\n{', '.join(skills)}"


def _parse_certifications(rows: list[dict[str, str]]) -> str:
    """Parse Certifications.csv → Certifications section."""
    if not rows:
        return ""
    lines = ["## Certifications"]
    for row in rows:
        name = _get(row, "Name")
        authority = _get(row, "Authority")
        started = _get(row, "Started On")
        url = _get(row, "Url")

        parts = [f"- **{name}**" if name else "- Certification"]
        if authority:
            parts[0] += f" ({authority})"
        if started:
            parts[0] += f" — {started}"
        if url:
            parts[0] += f" — [link]({url})"
        lines.append(parts[0])
    return "\n".join(lines)


def _parse_languages(rows: list[dict[str, str]]) -> str:
    """Parse Languages.csv → Languages section."""
    if not rows:
        return ""
    lines = ["## Languages"]
    for row in rows:
        name = _get(row, "Name")
        prof = _get(row, "Proficiency")
        if name:
            lines.append(f"- {name}: {prof}" if prof else f"- {name}")
    return "\n".join(lines)


def _parse_projects(rows: list[dict[str, str]]) -> str:
    """Parse Projects.csv → Projects section."""
    if not rows:
        return ""
    lines = ["## Projects"]
    for row in rows:
        title = _get(row, "Title")
        description = _get(row, "Description")
        url = _get(row, "Url")
        started = _get(row, "Started On")

        header = f"### {title}" if title else "### Project"
        entry = [header]
        if started:
            entry.append(f"_{started}_")
        if description:
            entry.append(description)
        if url:
            entry.append(f"[Link]({url})")
        lines.append("\n".join(filter(None, entry)))
    return "\n\n".join(lines)


def _parse_recommendations_received(rows: list[dict[str, str]]) -> str:
    """Parse Recommendations_Received.csv → Recommendations section."""
    if not rows:
        return ""
    lines = ["## Recommendations Received"]
    for row in rows:
        first = _get(row, "First Name")
        last = _get(row, "Last Name")
        company = _get(row, "Company")
        text = _get(row, "Text", "Recommendation")
        name = f"{first} {last}".strip()
        attribution = f"— {name}" if name else ""
        if company:
            attribution += f", {company}"
        lines.append(f'> "{text}" {attribution}'.strip())
    return "\n\n".join(lines)


def _parse_endorsements(rows: list[dict[str, str]]) -> str:
    """Parse Endorsement_Received_Info.csv → Endorsements section."""
    if not rows:
        return ""
    lines = ["## Endorsements"]
    for row in rows:
        skill = _get(row, "Skill Name")
        endorser = _get(row, "Endorser First Name", "Endorser")
        endorser_last = _get(row, "Endorser Last Name")
        name = f"{endorser} {endorser_last}".strip()
        if skill:
            lines.append(f"- {skill}: endorsed by {name}" if name else f"- {skill}")
    return "\n".join(lines)


def _parse_recommendations_given(rows: list[dict[str, str]]) -> str:
    """Parse Recommendations_Given.csv → Recommendations Given section."""
    if not rows:
        return ""
    lines = ["## Recommendations Given"]
    for row in rows:
        first = _get(row, "First Name")
        last = _get(row, "Last Name")
        company = _get(row, "Company")
        text = _get(row, "Text", "Recommendation")
        name = f"{first} {last}".strip()
        attribution = f"To {name}" if name else ""
        if company:
            attribution += f" at {company}"
        lines.append(f'> "{text}" {attribution}'.strip())
    return "\n\n".join(lines)


# =============================================================================
# Tier 2 — Career Intelligence
# =============================================================================


def _parse_learning(rows: list[dict[str, str]]) -> str:
    """Parse Learning.csv → Learning section (courses/certifications)."""
    if not rows:
        return ""
    lines = ["## Learning"]
    for row in rows:
        title = _get(row, "Title", "Content Title")
        content_type = _get(row, "Content Type", "Type")
        completed = _get(row, "Completed Date", "Completed At")

        entry = f"- {title}" if title else "- Course"
        if content_type:
            entry += f" ({content_type})"
        if completed:
            entry += f" — Completed: {completed}"
        lines.append(entry)
    return "\n".join(lines)


def _parse_job_applications(rows: list[dict[str, str]]) -> str:
    """Parse Job Applications CSV(s) → Job Applications section."""
    if not rows:
        return ""
    lines = ["## Job Applications"]
    for row in rows:
        date = _get(row, "Application Date", "Applied On")
        title = _get(row, "Job Title", "Title")
        company = _get(row, "Company Name", "Company")

        entry = f"- {date}: " if date else "- "
        entry += f"**{title}**" if title else "Application"
        if company:
            entry += f" at {company}"
        lines.append(entry)
    return "\n".join(lines)


def _parse_job_preferences(rows: list[dict[str, str]]) -> str:
    """Parse Job Seeker Preferences.csv → Job Search Preferences section."""
    if not rows:
        return ""
    lines = ["## Job Search Preferences"]
    for row in rows:
        for key, val in row.items():
            val = val.strip()
            if val:
                lines.append(f"- {key}: {val}")
    return "\n".join(lines)


def _parse_shares(rows: list[dict[str, str]]) -> str:
    """Parse Shares.csv (posts) → Posts section."""
    if not rows:
        return ""
    lines = ["## Posts"]
    for row in rows:
        date = _get(row, "Date", "SharedDate")
        commentary = _get(row, "Commentary", "ShareCommentary")
        url = _get(row, "ShareLink", "Url")

        if not commentary:
            continue
        entry = [f"### {date}" if date else "### Post"]
        entry.append(commentary)
        if url:
            entry.append(f"[Link]({url})")
        lines.append("\n".join(entry))
    return "\n\n".join(lines)


def _parse_inferences(rows: list[dict[str, str]]) -> str:
    """Parse Inferences_about_you.csv → LinkedIn Inferences section."""
    if not rows:
        return ""
    lines = ["## LinkedIn Inferences"]
    for row in rows:
        inf_type = _get(row, "Type", "Category")
        inference = _get(row, "Inference", "Description", "Value")
        if inference:
            lines.append(f"- {inf_type}: {inference}" if inf_type else f"- {inference}")
    return "\n".join(lines)


# =============================================================================
# Tier 3 — Network Summary (aggregate stats only)
# =============================================================================


def _parse_connections_summary(rows: list[dict[str, str]]) -> str:
    """Extract connection count + top companies/positions."""
    if not rows:
        return ""
    count = len(rows)
    company_counter: Counter[str] = Counter()
    position_counter: Counter[str] = Counter()
    for row in rows:
        company = _get(row, "Company")
        position = _get(row, "Position")
        if company:
            company_counter[company] += 1
        if position:
            position_counter[position] += 1

    lines = [f"## Network\n\n- {count} connections"]
    if company_counter:
        top = company_counter.most_common(10)
        companies = ", ".join(f"{c} ({n})" for c, n in top)
        lines.append(f"- Top companies: {companies}")
    if position_counter:
        top = position_counter.most_common(10)
        positions = ", ".join(f"{p} ({n})" for p, n in top)
        lines.append(f"- Top positions: {positions}")
    return "\n".join(lines)


def _parse_company_follows(rows: list[dict[str, str]]) -> str:
    """Extract company follow count."""
    if not rows:
        return ""
    return f"- Following {len(rows)} companies"


# =============================================================================
# Main Gatherer
# =============================================================================


# CSV file mappings: (zip_path, parser_function, use_variants)
_TIER1_CSVS: list[tuple[str, Any, bool]] = [
    ("Profile.csv", _parse_profile, False),
    ("Positions.csv", _parse_positions, False),
    ("Education.csv", _parse_education, False),
    ("Skills.csv", _parse_skills, False),
    ("Certifications.csv", _parse_certifications, False),
    ("Languages.csv", _parse_languages, False),
    ("Projects.csv", _parse_projects, False),
    ("Recommendations_Received.csv", _parse_recommendations_received, False),
    ("Endorsement_Received_Info.csv", _parse_endorsements, False),
    ("Recommendations_Given.csv", _parse_recommendations_given, False),
]

_TIER2_CSVS: list[tuple[str, Any, bool]] = [
    ("Learning.csv", _parse_learning, False),
    ("Jobs/Job Applications.csv", _parse_job_applications, True),
    ("Jobs/Job Seeker Preferences.csv", _parse_job_preferences, False),
    ("Shares.csv", _parse_shares, False),
    ("Inferences_about_you.csv", _parse_inferences, False),
]


class LinkedInGatherer(BaseGatherer):
    """Gather data from LinkedIn export ZIP — direct CSV parsing.

    Parses 17 career-relevant CSV files organized in 3 tiers:
    - Tier 1 (core): Profile, Positions, Education, Skills, Certifications,
      Languages, Projects, Recommendations, Endorsements
    - Tier 2 (intelligence): Learning, Job Applications, Job Preferences,
      Posts/Shares, LinkedIn Inferences
    - Tier 3 (network summary): Connections count, Companies Followed count
    """

    def gather(self, zip_path: Path, output_dir: Path | None = None) -> str:
        """Parse LinkedIn ZIP and return markdown content.

        Args:
            zip_path: Path to the LinkedIn data export ZIP file
            output_dir: Unused (kept for interface compatibility)

        Returns:
            Markdown string with all career-relevant data
        """
        if not zip_path.exists():
            raise FileNotFoundError(f"LinkedIn export not found: {zip_path}")

        logger.info("Parsing LinkedIn ZIP: %s", zip_path)
        sections: list[str] = []

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Tier 1 — Core Career Data
            for csv_name, parser, use_variants in _TIER1_CSVS:
                rows = _read_csv_variants(zf, csv_name) if use_variants else _read_csv(zf, csv_name)
                section = parser(rows)
                if section:
                    sections.append(section)
                    logger.debug("Tier 1: %s → %d rows", csv_name, len(rows))

            # Tier 2 — Career Intelligence
            for csv_name, parser, use_variants in _TIER2_CSVS:
                rows = _read_csv_variants(zf, csv_name) if use_variants else _read_csv(zf, csv_name)
                section = parser(rows)
                if section:
                    sections.append(section)
                    logger.debug("Tier 2: %s → %d rows", csv_name, len(rows))

            # Tier 3 — Network Summary (aggregate stats only)
            conn_rows = _read_csv(zf, "Connections.csv")
            conn_section = _parse_connections_summary(conn_rows)
            if conn_section:
                sections.append(conn_section)
                logger.debug("Tier 3: Connections → %d rows", len(conn_rows))

            follows_rows = _read_csv(zf, "Company Follows.csv")
            follows_section = _parse_company_follows(follows_rows)
            if follows_section:
                # Append to network section if it exists
                if conn_section:
                    sections[-1] += f"\n{follows_section}"
                else:
                    sections.append(f"## Network\n\n{follows_section}")
                logger.debug("Tier 3: Company Follows → %d rows", len(follows_rows))

        content = "\n\n".join(sections)
        logger.info("LinkedIn parsing complete: %d sections, %d chars", len(sections), len(content))
        return content
