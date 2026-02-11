"""Job normalization schema and utilities.

Provides a standardized job posting schema and normalizer utilities
to eliminate duplicate job parsing code across MCP clients.

DRY module to consolidate:
- NormalizedJob Pydantic model for consistent job structure
- SalaryInfo nested model for salary data
- JobNormalizer utilities for common transformations
- Helper functions for ID generation and HTML cleaning
"""

import hashlib
import re
from html import unescape
from typing import Any

from pydantic import BaseModel

from .salary_parser import ParsedSalary


class SalaryInfo(BaseModel):
    """Structured salary information."""

    min_amount: int | None = None
    max_amount: int | None = None
    currency: str = "USD"
    period: str = "year"  # "hour", "month", "year"
    raw: str | None = None


class NormalizedJob(BaseModel):
    """Standardized job posting schema across all sources.

    This model defines the canonical structure for job listings,
    ensuring consistency across RemoteOK, Himalayas, Jobicy,
    WeWorkRemotely, Remotive, Dice, and other sources.
    """

    id: str
    title: str
    company: str
    company_logo: str | None = None
    location: str = "Remote"
    remote: bool = True
    salary: SalaryInfo | None = None
    tags: list[str] = []
    categories: list[str] = []
    employment_type: str | None = None  # full_time, part_time, contract
    seniority: str | None = None  # junior, mid, senior, lead
    description: str = ""
    url: str = ""
    apply_url: str | None = None
    date_posted: str | None = None
    source: str  # e.g., "remoteok", "himalayas", "jobicy"


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


class JobNormalizer:
    """Centralizes job field normalization from all sources.

    Provides static methods to normalize raw job data from various
    APIs into a consistent structure. Each source has its own
    normalization method that handles source-specific field names.
    """

    @staticmethod
    def to_salary_info(salary_data: ParsedSalary | None) -> SalaryInfo | None:
        """Convert ParsedSalary to SalaryInfo model."""
        if not salary_data:
            return None
        return SalaryInfo(
            min_amount=salary_data.min_amount,
            max_amount=salary_data.max_amount,
            currency=salary_data.currency,
            period=salary_data.period,
            raw=salary_data.raw,
        )

    @staticmethod
    def from_remoteok(raw: dict[str, Any]) -> NormalizedJob:
        """Normalize RemoteOK API response."""
        return NormalizedJob(
            id=str(raw.get("id", raw.get("slug", ""))),
            title=raw.get("position", ""),
            company=raw.get("company", ""),
            company_logo=raw.get("company_logo") or raw.get("logo"),
            location=raw.get("location", "Remote"),
            remote=True,
            salary=SalaryInfo(
                min_amount=raw.get("salary_min"),
                max_amount=raw.get("salary_max"),
            )
            if raw.get("salary_min") or raw.get("salary_max")
            else None,
            tags=raw.get("tags", []),
            description=clean_html_description(raw.get("description", "")),
            url=raw.get("url", ""),
            apply_url=raw.get("apply_url"),
            date_posted=raw.get("date"),
            source="remoteok",
        )

    @staticmethod
    def from_himalayas(raw: dict[str, Any]) -> NormalizedJob:
        """Normalize Himalayas API response."""
        min_sal = raw.get("minSalary")
        max_sal = raw.get("maxSalary")
        currency = raw.get("currency", "USD")

        return NormalizedJob(
            id=raw.get("guid", ""),
            title=raw.get("title", ""),
            company=raw.get("companyName", ""),
            company_logo=raw.get("companyLogo"),
            location=", ".join(raw.get("locationRestrictions", [])) or "Worldwide",
            remote=True,
            salary=SalaryInfo(
                min_amount=min_sal,
                max_amount=max_sal,
                currency=currency,
            )
            if min_sal or max_sal
            else None,
            tags=[],
            categories=raw.get("categories", []),
            employment_type=raw.get("employmentType"),
            seniority=", ".join(raw.get("seniority", [])) if raw.get("seniority") else None,
            description=clean_html_description(
                raw.get("excerpt", "") or raw.get("description", "")
            ),
            url=raw.get("applicationLink", ""),
            date_posted=raw.get("pubDate"),
            source="himalayas",
        )

    @staticmethod
    def from_jobicy(raw: dict[str, Any], salary_data: ParsedSalary | None = None) -> NormalizedJob:
        """Normalize Jobicy API response."""
        title = clean_html_entities(raw.get("jobTitle", ""))

        salary = JobNormalizer.to_salary_info(salary_data)

        return NormalizedJob(
            id=str(raw.get("id", "")),
            title=title,
            company=raw.get("companyName", ""),
            company_logo=raw.get("companyLogo"),
            location=raw.get("jobGeo", "Remote"),
            remote=True,
            salary=salary,
            categories=raw.get("jobIndustry", []),
            employment_type=", ".join(raw.get("jobType", []))
            if isinstance(raw.get("jobType"), list)
            else raw.get("jobType"),
            seniority=raw.get("jobLevel"),
            description=clean_html_description(raw.get("jobExcerpt", "")),
            url=raw.get("url", ""),
            date_posted=raw.get("pubDate"),
            source="jobicy",
        )

    @staticmethod
    def from_remotive(
        raw: dict[str, Any], salary_data: ParsedSalary | None = None
    ) -> NormalizedJob:
        """Normalize Remotive API response."""
        salary = JobNormalizer.to_salary_info(salary_data)

        return NormalizedJob(
            id=str(raw.get("id", "")),
            title=raw.get("title", ""),
            company=raw.get("company_name", ""),
            company_logo=raw.get("company_logo"),
            location=raw.get("candidate_required_location", "Worldwide"),
            remote=True,
            salary=salary,
            tags=raw.get("tags", []),
            categories=[raw.get("category", "")] if raw.get("category") else [],
            employment_type=raw.get("job_type"),
            url=raw.get("url", ""),
            date_posted=raw.get("publication_date"),
            source="remotive",
        )

    @staticmethod
    def from_weworkremotely(
        raw: dict[str, Any],
        guid: str,
        salary_data: ParsedSalary | None = None,
    ) -> NormalizedJob:
        """Normalize WeWorkRemotely RSS item."""
        title_raw = raw.get("title", "")
        company, title = parse_company_title(title_raw)

        salary = JobNormalizer.to_salary_info(salary_data)

        return NormalizedJob(
            id=generate_job_id("weworkremotely", guid),
            title=title,
            company=company,
            location=raw.get("region", "Remote"),
            remote=True,
            salary=salary,
            categories=[raw.get("category", "")] if raw.get("category") else [],
            description=clean_html_description(raw.get("description", "")),
            url=raw.get("link", ""),
            date_posted=raw.get("pubDate"),
            source="weworkremotely",
        )

    @staticmethod
    def from_dice(raw: dict[str, Any]) -> NormalizedJob:
        """Normalize Dice MCP response."""
        return NormalizedJob(
            id=str(raw.get("id", "")),
            title=raw.get("title", raw.get("jobTitle", "")),
            company=raw.get("company", raw.get("companyName", "")),
            location=raw.get("location", ""),
            remote="remote" in raw.get("location", "").lower(),
            employment_type=raw.get("employmentType"),
            url=raw.get("url", raw.get("jobUrl", "")),
            date_posted=raw.get("postedDate", raw.get("datePosted")),
            source="dice",
        )
