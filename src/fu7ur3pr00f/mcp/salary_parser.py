"""Salary parsing utilities for extracting structured salary data from text.

Used by RSS-based job clients to extract salary information from
job descriptions and dedicated salary fields.
"""

import re
from typing import NamedTuple


class ParsedSalary(NamedTuple):
    """Structured salary data extracted from text."""

    min_amount: int | None
    max_amount: int | None
    currency: str
    period: str  # "hour", "year", "month"
    raw: str


def parse_salary(text: str) -> ParsedSalary | None:
    """Extract salary from text.

    Handles various formats:
    - "$65.00 - $70.00 per hour"
    - "$120,000 - $150,000"
    - "$70304/year"
    - "120k - 150k"
    - "Compensation: $X - $Y"
    - "€50,000 - €70,000"

    Args:
        text: Text containing salary information

    Returns:
        ParsedSalary if found, None otherwise
    """
    if not text:
        return None

    # Normalize text
    text_clean = text.replace("\n", " ").replace("\r", " ")

    # Try different patterns in order of specificity
    patterns = [
        # Range with currency and period: "$65.00 - $70.00 per hour"
        (
            r"[\$€£](?P<min>[\d,]+(?:\.\d+)?)\s*[-–to]+\s*[\$€£]?(?P<max>[\d,]+(?:\.\d+)?)"
            r"\s*(?:per\s+)?(?P<period>hour|hr|year|yr|month|mo|annually|annual)",
            "range_with_period",
        ),
        # Range without period: "$120,000 - $150,000"
        (
            r"[\$€£](?P<min>[\d,]+(?:\.\d+)?)\s*[-–to]+\s*[\$€£]?(?P<max>[\d,]+(?:\.\d+)?)",
            "range_no_period",
        ),
        # Single value with period: "$70304/year" or "$50/hour"
        (
            r"[\$€£](?P<min>[\d,]+(?:\.\d+)?)\s*[/]?\s*(?P<period>hour|hr|year|yr|month|mo|annually)",
            "single_with_period",
        ),
        # K notation range: "120k - 150k" or "$120K-$150K"
        (
            r"[\$€£]?(?P<min>\d+)\s*[kK]\s*[-–to]+\s*[\$€£]?(?P<max>\d+)\s*[kK]",
            "k_range",
        ),
        # Single K notation: "$120k" or "120K/year"
        (
            r"[\$€£]?(?P<min>\d+)\s*[kK](?:\s*[/]?\s*(?P<period>year|yr|annually))?",
            "k_single",
        ),
    ]

    for pattern, pattern_type in patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            groups = match.groupdict()

            # Parse min amount
            min_str = groups.get("min", "")
            min_amount = _parse_amount(min_str, pattern_type)

            # Parse max amount
            max_str = groups.get("max", "")
            max_amount = _parse_amount(max_str, pattern_type) if max_str else None

            # Determine period
            period_raw = groups.get("period", "")
            period = _normalize_period(period_raw, min_amount)

            # Detect currency from original text
            currency = _detect_currency(text_clean)

            return ParsedSalary(
                min_amount=min_amount,
                max_amount=max_amount,
                currency=currency,
                period=period,
                raw=match.group(0).strip(),
            )

    return None


def _parse_amount(amount_str: str, pattern_type: str) -> int | None:
    """Parse amount string to integer."""
    if not amount_str:
        return None

    # Remove commas and convert
    clean = amount_str.replace(",", "")

    try:
        value = float(clean)

        # Handle K notation
        if pattern_type in ("k_range", "k_single"):
            value *= 1000

        return int(value)
    except ValueError:
        return None


def _normalize_period(period_raw: str, amount: int | None) -> str:
    """Normalize period string and infer if missing."""
    if not period_raw:
        # Infer period from amount
        if amount is not None:
            # Amounts > 1000 are likely yearly, < 500 are likely hourly
            if amount >= 1000:
                return "year"
            elif amount <= 500:
                return "hour"
        return "year"  # Default to yearly

    period_lower = period_raw.lower()

    if period_lower in ("hour", "hr", "hourly"):
        return "hour"
    elif period_lower in ("month", "mo", "monthly"):
        return "month"
    else:  # year, yr, annually, annual
        return "year"


def _detect_currency(text: str) -> str:
    """Detect currency from text."""
    if "€" in text:
        return "EUR"
    elif "£" in text:
        return "GBP"
    else:
        return "USD"  # Default


def extract_salary_from_html(html: str) -> ParsedSalary | None:
    """Extract salary from HTML content.

    Looks for salary in common patterns used by job boards.

    Args:
        html: HTML content (may contain tags)

    Returns:
        ParsedSalary if found, None otherwise
    """
    # Common salary indicators in HTML
    salary_indicators = [
        r"compensation[:\s]+",
        r"salary[:\s]+",
        r"pay[:\s]+",
        r"rate[:\s]+",
        r"\bpay\b[:\s]*",
    ]

    for indicator in salary_indicators:
        # Find text after indicator
        match = re.search(
            indicator + r"([^<\n]{10,100})",
            html,
            re.IGNORECASE,
        )
        if match:
            result = parse_salary(match.group(1))
            if result:
                return result

    # Fall back to searching entire text
    return parse_salary(html)
