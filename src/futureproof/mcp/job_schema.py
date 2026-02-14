"""Job schema utilities.

Helper functions for job ID generation, HTML cleaning,
salary attachment, and company/title parsing used by MCP clients.
"""

import hashlib
import re
from html import unescape
from typing import Any

from .salary_parser import ParsedSalary


def generate_job_id(source: str, identifier: str) -> str:
    """Generate consistent job ID from source and identifier.

    Used by WeWorkRemotely, JobSpy, and other clients that need
    to generate unique IDs from GUIDs or URLs.

    Args:
        source: Job source name (e.g., "weworkremotely")
        identifier: Unique identifier (GUID, URL, etc.)

    Returns:
        12-character hex ID
    """
    unique_str = f"{source}:{identifier}"
    return hashlib.md5(unique_str.encode()).hexdigest()[:12]


def clean_html_description(html: str, max_length: int = 500) -> str:
    """Clean HTML content to plain text and truncate.

    Removes HTML tags, normalizes whitespace, and unescapes
    HTML entities. Used by WeWorkRemotely and other RSS clients.

    Args:
        html: HTML content string
        max_length: Maximum output length (default 500)

    Returns:
        Cleaned plain text, truncated if necessary
    """
    if not html:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    # Unescape HTML entities
    text = unescape(text).strip()

    return text[:max_length] if len(text) > max_length else text


def clean_html_entities(text: str) -> str:
    """Clean common HTML entities from text.

    Used by Jobicy and other clients that have entity-encoded titles.

    Args:
        text: Text with potential HTML entities

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    return (
        text.replace("&amp;", "&")
        .replace("&#8211;", "-")
        .replace("&#8217;", "'")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )


def attach_salary(job_dict: dict[str, Any], salary_data: ParsedSalary | None) -> None:
    """Attach parsed salary data to job dict.

    Eliminates repeated salary field assignment pattern found in
    Jobicy, Remotive, and WeWorkRemotely clients.

    Args:
        job_dict: Job dictionary to update in place
        salary_data: Parsed salary data from salary_parser
    """
    if salary_data:
        job_dict["salary_min"] = salary_data.min_amount
        job_dict["salary_max"] = salary_data.max_amount
        job_dict["salary_currency"] = salary_data.currency
        job_dict["salary_period"] = salary_data.period
        job_dict["salary_raw"] = salary_data.raw


def parse_company_title(title_raw: str, separator: str = ": ") -> tuple[str, str]:
    """Parse 'Company: Job Title' format into (company, title).

    Used by WeWorkRemotely and similar RSS feeds where company
    and title are combined.

    Args:
        title_raw: Raw title string like "Acme Inc: Senior Developer"
        separator: Separator between company and title

    Returns:
        Tuple of (company, title). Company is empty string if no separator.
    """
    if separator in title_raw:
        parts = title_raw.split(separator, 1)
        return parts[0].strip(), parts[1].strip()
    return "", title_raw.strip()
