"""LinkedIn data gatherer — direct CSV parsing from ZIP export.

Parses up to 19 career-relevant CSV files organized in 3 tiers:
- Tier 1 (core): Profile, Positions, Education, Skills, Certifications,
  Languages, Projects, Recommendations, Endorsements
- Tier 2 (intelligence): Learning, Job Applications, Job Preferences,
  Posts/Shares, LinkedIn Inferences, Connections (full), Messages
- Tier 3 (network summary): Companies Followed count

Returns a list of Section tuples for direct indexing to ChromaDB.
"""

import csv
import io
import logging
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from ..memory.chunker import Section

logger = logging.getLogger(__name__)


def _read_csv(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    """Read a single CSV from a ZIP, returning rows as dicts.

    Handles LinkedIn's notes preamble (e.g., in Connections.csv) by skipping
    lines until a valid multi-column CSV header is found.
    """
    try:
        with zf.open(name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8-sig")
            lines = text.readlines()

        # Skip LinkedIn's notes preamble (e.g., Connections.csv starts with
        # "Notes:" + a quoted explanation + blank line before the real header).
        # Detect: if line 0 has no commas, skip until after the first blank line.
        start = 0
        if lines and "," not in lines[0].strip():
            for i, line in enumerate(lines):
                if not line.strip():
                    start = i + 1
                    break

        csv_text = io.StringIO("".join(lines[start:]))
        return list(csv.DictReader(csv_text))
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
    p = Path(base_name)

    for i in range(1, 11):
        variant = str(p.with_stem(f"{p.stem}_{i}"))
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


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Strip HTML tags from text, collapsing whitespace."""
    return _HTML_TAG_RE.sub(" ", text).strip()


def _get_name(row: dict[str, str]) -> str:
    """Build full name from First Name + Last Name columns."""
    return f"{_get(row, 'First Name')} {_get(row, 'Last Name')}".strip()


# =============================================================================
# Tier 1 — Core Career Data
# =============================================================================


def _parse_profile(rows: list[dict[str, str]]) -> list[Section]:
    """Parse Profile.csv → profile and summary sections."""
    if not rows:
        return []
    row = rows[0]
    name = _get_name(row)
    headline = _get(row, "Headline")
    summary = _get(row, "Summary")
    industry = _get(row, "Industry")
    geo = _get(row, "Geo Location")

    sections: list[Section] = []

    # Profile section — headline, industry, location
    profile_lines: list[str] = []
    if name:
        profile_lines.append(f"**{name}**")
    if headline:
        profile_lines.append(f"**Headline:** {headline}")
    if industry:
        profile_lines.append(f"**Industry:** {industry}")
    if geo:
        profile_lines.append(f"**Location:** {geo}")
    if profile_lines:
        sections.append(Section("Profile", "\n".join(profile_lines)))

    if summary:
        sections.append(Section("Summary", summary))

    return sections


def _parse_positions(rows: list[dict[str, str]]) -> Section | None:
    """Parse Positions.csv → Experience section."""
    if not rows:
        return None
    lines: list[str] = []
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
    return Section("Experience", "\n\n".join(lines))


def _parse_education(rows: list[dict[str, str]]) -> Section | None:
    """Parse Education.csv → Education section."""
    if not rows:
        return None
    lines: list[str] = []
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
    return Section("Education", "\n\n".join(lines))


def _parse_skills(rows: list[dict[str, str]]) -> Section | None:
    """Parse Skills.csv → Skills section."""
    if not rows:
        return None
    skills = [_get(row, "Name") for row in rows if _get(row, "Name")]
    if not skills:
        return None
    return Section("Skills", ", ".join(skills))


def _parse_certifications(rows: list[dict[str, str]]) -> Section | None:
    """Parse Certifications.csv → Certifications section."""
    if not rows:
        return None
    lines: list[str] = []
    for row in rows:
        name = _get(row, "Name")
        authority = _get(row, "Authority")
        started = _get(row, "Started On")
        url = _get(row, "Url")

        entry = f"- **{name}**" if name else "- Certification"
        if authority:
            entry += f" ({authority})"
        if started:
            entry += f" — {started}"
        if url:
            entry += f" — [link]({url})"
        lines.append(entry)
    return Section("Certifications", "\n".join(lines))


def _parse_languages(rows: list[dict[str, str]]) -> Section | None:
    """Parse Languages.csv → Languages section."""
    if not rows:
        return None
    lines: list[str] = []
    for row in rows:
        name = _get(row, "Name")
        prof = _get(row, "Proficiency")
        if name:
            lines.append(f"- {name}: {prof}" if prof else f"- {name}")
    if not lines:
        return None
    return Section("Languages", "\n".join(lines))


def _parse_projects(rows: list[dict[str, str]]) -> Section | None:
    """Parse Projects.csv → Projects section."""
    if not rows:
        return None
    lines: list[str] = []
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
    return Section("Projects", "\n\n".join(lines))


def _parse_recommendations(
    rows: list[dict[str, str]], section_name: str, prefix: str, company_join: str,
) -> Section | None:
    """Parse a recommendations CSV → blockquote section."""
    if not rows:
        return None
    lines: list[str] = []
    for row in rows:
        name = _get_name(row)
        company = _get(row, "Company")
        text = _get(row, "Text", "Recommendation")
        attribution = f"{prefix}{name}" if name else ""
        if company:
            attribution += f"{company_join}{company}"
        lines.append(f'> "{text}" {attribution}'.strip())
    return Section(section_name, "\n\n".join(lines))


def _parse_recommendations_received(rows: list[dict[str, str]]) -> Section | None:
    return _parse_recommendations(rows, "Recommendations Received", "— ", ", ")


def _parse_recommendations_given(rows: list[dict[str, str]]) -> Section | None:
    return _parse_recommendations(rows, "Recommendations Given", "To ", " at ")


def _parse_endorsements(rows: list[dict[str, str]]) -> Section | None:
    """Parse Endorsement_Received_Info.csv → Endorsements section."""
    if not rows:
        return None
    lines: list[str] = []
    for row in rows:
        skill = _get(row, "Skill Name")
        endorser = _get(row, "Endorser First Name", "Endorser")
        endorser_last = _get(row, "Endorser Last Name")
        name = f"{endorser} {endorser_last}".strip()
        if skill:
            lines.append(f"- {skill}: endorsed by {name}" if name else f"- {skill}")
    if not lines:
        return None
    return Section("Endorsements", "\n".join(lines))


# =============================================================================
# Tier 2 — Career Intelligence
# =============================================================================


def _parse_learning(rows: list[dict[str, str]]) -> Section | None:
    """Parse Learning.csv → Learning section (courses/certifications)."""
    if not rows:
        return None
    lines: list[str] = []
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
    return Section("Learning", "\n".join(lines))


def _parse_job_applications(rows: list[dict[str, str]]) -> Section | None:
    """Parse Job Applications CSV(s) → Job Applications section."""
    if not rows:
        return None
    lines: list[str] = []
    for row in rows:
        date = _get(row, "Application Date", "Applied On")
        title = _get(row, "Job Title", "Title")
        company = _get(row, "Company Name", "Company")

        entry = f"- {date}: " if date else "- "
        entry += f"**{title}**" if title else "Application"
        if company:
            entry += f" at {company}"
        lines.append(entry)
    return Section("Job Applications", "\n".join(lines))


def _parse_job_preferences(rows: list[dict[str, str]]) -> Section | None:
    """Parse Job Seeker Preferences.csv → Job Search Preferences section."""
    if not rows:
        return None
    lines: list[str] = []
    for row in rows:
        for key, val in row.items():
            val = val.strip()
            if val:
                lines.append(f"- {key}: {val}")
    if not lines:
        return None
    return Section("Job Search Preferences", "\n".join(lines))


def _parse_shares(rows: list[dict[str, str]]) -> Section | None:
    """Parse Shares.csv (posts) → Posts section."""
    if not rows:
        return None
    lines: list[str] = []
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
    if not lines:
        return None
    return Section("Posts", "\n\n".join(lines))


def _parse_inferences(rows: list[dict[str, str]]) -> Section | None:
    """Parse Inferences_about_you.csv → LinkedIn Inferences section."""
    if not rows:
        return None
    lines: list[str] = []
    for row in rows:
        inf_type = _get(row, "Type", "Category")
        inference = _get(row, "Inference", "Description", "Value")
        if inference:
            lines.append(f"- {inf_type}: {inference}" if inf_type else f"- {inference}")
    if not lines:
        return None
    return Section("LinkedIn Inferences", "\n".join(lines))


def _parse_connections(rows: list[dict[str, str]]) -> Section | None:
    """Parse Connections.csv → individual connection records + network summary.

    Outputs each connection as a compact paragraph so the chunker splits
    by paragraph — each connection becomes a separate chunk with
    section="Connections", enabling section filtering.
    """
    if not rows:
        return None

    # Individual connection records
    entries: list[str] = []
    company_counter: Counter[str] = Counter()
    position_counter: Counter[str] = Counter()

    for row in rows:
        company = _get(row, "Company")
        position = _get(row, "Position")
        connected_on = _get(row, "Connected On")
        email = _get(row, "Email Address", "Email")
        url = _get(row, "URL")

        if company:
            company_counter[company] += 1
        if position:
            position_counter[position] += 1

        name = _get_name(row)
        if not name:
            continue

        # Compact single-line format per connection
        details = [f"**{name}**"]
        if company:
            details.append(f"Company: {company}")
        if position:
            details.append(f"Position: {position}")
        if connected_on:
            details.append(f"Connected: {connected_on}")
        if email:
            details.append(f"Email: {email}")
        if url:
            details.append(f"URL: {url}")
        entries.append(" | ".join(details))

    # Network summary (aggregate stats)
    count = len(rows)
    summary_lines = [f"**Network Summary**: {count} connections"]
    if company_counter:
        top = company_counter.most_common(10)
        companies = ", ".join(f"{c} ({n})" for c, n in top)
        summary_lines.append(f"Top companies: {companies}")
    if position_counter:
        top = position_counter.most_common(10)
        positions = ", ".join(f"{p} ({n})" for p, n in top)
        summary_lines.append(f"Top positions: {positions}")

    parts: list[str] = []
    if entries:
        parts.append("\n\n".join(entries))
    parts.append(" | ".join(summary_lines))
    return Section("Connections", "\n\n".join(parts))


def _parse_messages(rows: list[dict[str, str]]) -> Section | None:
    """Parse messages.csv → Messages section grouped by conversation.

    LinkedIn exports messages with columns: CONVERSATION ID,
    CONVERSATION TITLE, FROM, SENDER PROFILE URL, DATE, SUBJECT, CONTENT.
    Messages are grouped by conversation and ordered chronologically.
    """
    if not rows:
        return None

    # Group messages by conversation
    conversations: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        conv_id = _get(row, "CONVERSATION ID", "Conversation ID")
        if not conv_id:
            continue
        conversations.setdefault(conv_id, []).append(row)

    if not conversations:
        return None

    sections: list[str] = []

    for conv_id, messages in conversations.items():
        title = _get(messages[0], "CONVERSATION TITLE", "Conversation Title")
        header = f"### Conversation: {title}" if title else f"### Conversation {conv_id}"
        msg_lines = [header]

        for msg in messages:
            sender = _get(msg, "FROM", "From")
            date = _get(msg, "DATE", "Date")
            content = _strip_html(_get(msg, "CONTENT", "Content"))
            subject = _get(msg, "SUBJECT", "Subject")

            if not content:
                continue
            if date:
                msg_lines.append(f"\n_{date}_")
            if subject:
                msg_lines.append(f"**Subject: {subject}**")
            sender_label = f"**{sender}**" if sender else "**Unknown**"
            msg_lines.append(f"{sender_label}: {content}")

        sections.append("\n".join(msg_lines))

    if not sections:
        return None
    return Section("Messages", "\n\n".join(sections))


# =============================================================================
# Tier 3 — Network Summary
# =============================================================================


def _parse_company_follows(rows: list[dict[str, str]]) -> Section | None:
    """Extract company follow count as Network section."""
    if not rows:
        return None
    return Section("Network", f"- Following {len(rows)} companies")


# =============================================================================
# Main Gatherer
# =============================================================================


# CSV file mappings: (tier, zip_path, parser_function, use_variants)
_CSV_PARSERS: list[tuple[str, str, Any, bool]] = [
    # Tier 1 — Core Career Data
    ("Tier 1", "Profile.csv", _parse_profile, False),
    ("Tier 1", "Positions.csv", _parse_positions, False),
    ("Tier 1", "Education.csv", _parse_education, False),
    ("Tier 1", "Skills.csv", _parse_skills, False),
    ("Tier 1", "Certifications.csv", _parse_certifications, False),
    ("Tier 1", "Languages.csv", _parse_languages, False),
    ("Tier 1", "Projects.csv", _parse_projects, False),
    ("Tier 1", "Recommendations_Received.csv", _parse_recommendations_received, False),
    ("Tier 1", "Endorsement_Received_Info.csv", _parse_endorsements, False),
    ("Tier 1", "Recommendations_Given.csv", _parse_recommendations_given, False),
    # Tier 2 — Career Intelligence
    ("Tier 2", "Learning.csv", _parse_learning, False),
    ("Tier 2", "Jobs/Job Applications.csv", _parse_job_applications, True),
    ("Tier 2", "Jobs/Job Seeker Preferences.csv", _parse_job_preferences, False),
    ("Tier 2", "Shares.csv", _parse_shares, False),
    ("Tier 2", "Inferences_about_you.csv", _parse_inferences, False),
    ("Tier 2", "Connections.csv", _parse_connections, False),
    ("Tier 2", "messages.csv", _parse_messages, False),
    # Tier 3 — Network Summary
    ("Tier 3", "Company Follows.csv", _parse_company_follows, False),
]


class LinkedInGatherer:
    """Gather data from LinkedIn export ZIP — direct CSV parsing.

    Parses up to 19 career-relevant CSV files organized in 3 tiers:
    - Tier 1 (core): Profile, Positions, Education, Skills, Certifications,
      Languages, Projects, Recommendations, Endorsements
    - Tier 2 (intelligence): Learning, Job Applications, Job Preferences,
      Posts/Shares, LinkedIn Inferences, Connections (full), Messages
    - Tier 3 (network summary): Companies Followed count
    """

    def gather(self, zip_path: Path) -> list[Section]:
        """Parse LinkedIn ZIP and return labeled sections.

        Args:
            zip_path: Path to the LinkedIn data export ZIP file

        Returns:
            List of Section(name, content) tuples
        """
        if not zip_path.exists():
            raise FileNotFoundError(f"LinkedIn export not found: {zip_path}")

        logger.info("Parsing LinkedIn ZIP: %s", zip_path)
        sections: list[Section] = []

        with zipfile.ZipFile(zip_path, "r") as zf:
            for tier, csv_name, parser, use_variants in _CSV_PARSERS:
                rows = (
                    _read_csv_variants(zf, csv_name) if use_variants
                    else _read_csv(zf, csv_name)
                )
                result = parser(rows)
                if result is None:
                    continue
                # _parse_profile returns list[Section], others return Section
                if isinstance(result, list):
                    sections.extend(result)
                else:
                    sections.append(result)
                logger.debug("%s: %s → %d rows", tier, csv_name, len(rows))

        logger.info(
            "LinkedIn parsing complete: %d sections",
            len(sections),
        )
        return sections
