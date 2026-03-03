"""Security utilities for PII protection and secure file operations.

This module provides career data anonymization before sending data to external LLMs,
secure file I/O (no TOCTOU), and prompt boundary sanitization.
"""

import contextlib
import os
import re
from collections.abc import Generator
from pathlib import Path


def anonymize_career_data(data: str, preserve_professional_emails: bool = False) -> str:
    """Anonymize career data while preserving professional context.

    This is a specialized anonymization for career/CV data that:
    - Removes personal contact info (phone, personal email)
    - Optionally preserves work email domains for context
    - Keeps professional information (company names, job titles, etc.)

    Args:
        data: Career data text (markdown or plain text)
        preserve_professional_emails: If True, replaces only the local part
                                     of work emails (e.g., [USER]@company.com)

    Returns:
        Anonymized career data
    """
    result = data

    if preserve_professional_emails:
        # Replace local part but keep domain for professional emails
        # e.g., john.doe@company.com -> [USER]@company.com
        result = re.sub(
            r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b", r"[USER]@\2", result
        )
    else:
        # Full email anonymization
        result = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", result)

    # Phone numbers
    result = re.sub(
        r"\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b", "[PHONE]", result
    )
    result = re.sub(
        r"\+?[0-9]{1,3}[-.\s]?[0-9]{2,4}[-.\s]?[0-9]{2,4}[-.\s]?[0-9]{2,4}\b", "[PHONE]", result
    )

    # Physical addresses with apartment/unit numbers (likely personal addresses)
    result = re.sub(
        r"\b\d{1,5}\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)\.?(?:\s*,?\s*(?:Apt|Suite|Unit|#)\.?\s*\w+)\b",
        "[HOME_ADDRESS]",
        result,
        flags=re.IGNORECASE,
    )

    # Social media profile URLs with usernames (preserve platform name)
    result = re.sub(
        r"(https?://(?:www\.)?(?:linkedin|github|gitlab|twitter|x)\.com/(?:in/)?)[a-zA-Z0-9._-]+",
        r"\1[USERNAME]",
        result,
        flags=re.IGNORECASE,
    )

    # SSN (US Social Security Number) — dashed, spaced, or contiguous
    result = re.sub(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "[SSN]", result)

    # Date of birth (only labeled — bare dates preserved as they may be employment dates)
    # Captures: "DOB: 1990-01-15", "Date of Birth: January 1, 1990", "Born: 01/15/1990"
    result = re.sub(
        r"\b(?:DOB|Date of Birth|Born|Birthday)[:\s]+\S+(?:[,\s]+\d{1,2}[,\s]+\d{4})?",
        "[DOB]",
        result,
        flags=re.IGNORECASE,
    )

    # Street addresses without apartment/unit (negative lookahead avoids
    # double-matching addresses already caught by the apt/unit pattern above)
    result = re.sub(
        r"\b\d{1,5}\s+[\w\s]{1,40}"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)"
        r"\.?(?!\s*,?\s*(?:Apt|Suite|Unit|#))",
        "[ADDRESS]",
        result,
        flags=re.IGNORECASE,
    )

    return result


@contextlib.contextmanager
def secure_open(
    path: str | Path, mode: str = "w", *, file_mode: int = 0o600,
) -> Generator[object, None, None]:
    """Open file for writing with atomic restrictive permissions.

    Uses ``os.open()`` so the file is *never* world-readable, even for a
    microsecond (no TOCTOU window between create and chmod).

    Args:
        path: File path to open.
        mode: Python file mode (e.g. ``"w"``, ``"wb"``).
        file_mode: Unix permission bits (default ``0o600``).
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(str(path), flags, file_mode)
    os.fchmod(fd, file_mode)  # Also update perms on existing files
    try:
        with os.fdopen(fd, mode) as f:
            yield f
    except BaseException:
        # fd is already closed by fdopen on success; only close on error
        # if fdopen itself failed before taking ownership
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def secure_mkdir(path: str | Path, *, mode: int = 0o700) -> Path:
    """Create directory with restrictive permissions.

    Args:
        path: Directory to create (parents created as needed).
        mode: Unix permission bits (default ``0o700``).

    Returns:
        The directory path.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    p.chmod(mode)
    return p


def sanitize_for_prompt(text: str) -> str:
    """Escape closing XML tags that could break prompt data boundaries.

    Prevents injected content from closing ``<career_data>``,
    ``<tool_results>``, or similar XML-style boundary markers used in
    system prompts.

    Args:
        text: Raw text to sanitize.

    Returns:
        Text with closing XML tags escaped (``</tag>`` → ``<\\/tag>``).
    """
    return re.sub(r"</([\w_]+)>", r"<\\/\1>", text)
