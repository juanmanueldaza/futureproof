"""Input validation models using Pydantic.

These models validate user inputs before they reach business logic,
preventing invalid states and providing user-friendly error messages.
"""

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass


class GatherGitHubInput(BaseModel):
    """Validated input for GitHub gathering."""

    username: str = Field(
        min_length=1,
        max_length=39,
        description="GitHub username",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate GitHub username format."""
        # GitHub username rules:
        # - Can only contain alphanumeric characters and hyphens
        # - Cannot start or end with a hyphen
        # - Cannot have consecutive hyphens
        pattern = r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$"
        if not re.match(pattern, v):
            raise ValueError(
                "Invalid GitHub username. Must contain only alphanumeric "
                "characters and hyphens, cannot start/end with hyphen."
            )
        return v


class GatherGitLabInput(BaseModel):
    """Validated input for GitLab gathering."""

    username: str = Field(
        min_length=1,
        max_length=255,
        description="GitLab username",
    )
    groups: list[str] = Field(
        default_factory=list,
        description="GitLab groups to include",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate GitLab username format."""
        # GitLab usernames: alphanumeric, underscores, dots, hyphens
        pattern = r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$"
        if not re.match(pattern, v):
            raise ValueError(
                "Invalid GitLab username. Must start with alphanumeric "
                "and contain only alphanumeric, dots, underscores, and hyphens."
            )
        return v


class GatherPortfolioInput(BaseModel):
    """Validated input for portfolio gathering."""

    url: HttpUrl = Field(description="Portfolio website URL")


class GatherLinkedInInput(BaseModel):
    """Validated input for LinkedIn gathering."""

    zip_path: Path = Field(description="Path to LinkedIn data export ZIP file")

    @field_validator("zip_path")
    @classmethod
    def validate_zip_exists(cls, v: Path) -> Path:
        """Validate ZIP file exists and has correct extension."""
        if not v.exists():
            raise ValueError(f"ZIP file not found: {v}")
        if not v.suffix.lower() == ".zip":
            raise ValueError(f"Expected .zip file, got: {v.suffix}")
        return v


class GenerateCVInput(BaseModel):
    """Validated input for CV generation."""

    language: Literal["en", "es"] = Field(
        default="en",
        description="Output language",
    )
    format: Literal["ats", "creative"] = Field(
        default="ats",
        description="CV format",
    )


class AdviseInput(BaseModel):
    """Validated input for career advice."""

    target: str = Field(
        min_length=3,
        max_length=500,
        description="Target role or career goal",
    )

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        """Sanitize and validate target input.

        Checks for prompt injection attempts and sanitizes the input.
        """
        from ..utils.security import sanitize_user_input

        # Basic sanitization - strip whitespace
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Target must be at least 3 characters")

        # Check for prompt injection attempts
        result = sanitize_user_input(v, strict=True)
        if not result.is_safe:
            raise ValueError(
                f"Input contains disallowed patterns: {', '.join(result.blocked_patterns)}. "
                "Please provide a simple career goal description."
            )

        return result.text
