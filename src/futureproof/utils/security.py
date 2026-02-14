"""Security utilities for input sanitization and PII protection.

This module provides:
- Prompt injection detection and sanitization
- Career data anonymization before sending data to external LLMs
"""

import re
from dataclasses import dataclass
from typing import Final

# Patterns that may indicate prompt injection attempts
INJECTION_PATTERNS: Final[list[tuple[str, str]]] = [
    (
        r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
        "ignore instructions",
    ),
    (
        r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
        "disregard instructions",
    ),
    (
        r"forget\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
        "forget instructions",
    ),
    (
        r"(reveal|show|display|output)\s+(your\s+)?(system\s+)?(prompt|instructions?)",
        "reveal prompt",
    ),
    (r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?)", "query prompt"),
    (r"(print|echo|output)\s+(the\s+)?(system\s+)?(prompt|instructions?)", "print prompt"),
    (
        r"act\s+as\s+(if\s+)?(you\s+(are|were)\s+)?(?!a\s+career)",
        "role manipulation",
    ),  # Allow "act as a career advisor"
    (r"pretend\s+(you\s+are|to\s+be)\s+(?!a\s+career)", "role manipulation"),
    (r"you\s+are\s+now\s+(?!analyzing|reviewing|assessing)", "role override"),
    (r"new\s+(instructions?|rules?|prompt)\s*:", "new instructions"),
    (r"override\s+(previous\s+)?(instructions?|rules?|prompt)", "override instructions"),
    (r"\[system\]|\[INST\]|<<SYS>>|<\|system\|>", "system tag injection"),
    (r"```\s*(system|prompt|instructions?)", "code block injection"),
]

# Compiled patterns for performance
_COMPILED_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern, re.IGNORECASE), desc) for pattern, desc in INJECTION_PATTERNS
]


@dataclass
class SanitizationResult:
    """Result of input sanitization."""

    text: str
    is_safe: bool
    blocked_patterns: list[str]


def detect_prompt_injection(text: str) -> list[str]:
    """Detect potential prompt injection patterns in text.

    Args:
        text: Input text to analyze

    Returns:
        List of detected injection pattern descriptions
    """
    detected = []
    for pattern, description in _COMPILED_INJECTION_PATTERNS:
        if pattern.search(text):
            detected.append(description)
    return detected


def sanitize_user_input(text: str, strict: bool = True) -> SanitizationResult:
    """Sanitize user input for safe inclusion in LLM prompts.

    Args:
        text: User input to sanitize
        strict: If True, reject inputs with injection patterns.
                If False, only log warnings but allow the input.

    Returns:
        SanitizationResult with sanitized text and safety status
    """
    # Basic cleanup
    text = text.strip()

    # Detect injection attempts
    blocked = detect_prompt_injection(text)

    if blocked and strict:
        return SanitizationResult(
            text="",
            is_safe=False,
            blocked_patterns=blocked,
        )

    # Even if not strict, we can do some basic sanitization
    # Remove potential system tag injections
    sanitized = re.sub(r"\[system\]|\[INST\]|<<SYS>>|<\|system\|>", "", text, flags=re.IGNORECASE)

    return SanitizationResult(
        text=sanitized,
        is_safe=len(blocked) == 0,
        blocked_patterns=blocked,
    )


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

    return result
