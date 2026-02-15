"""User profile management for FutureProof.

Provides YAML-based storage for user identity, goals, and preferences.
The profile is human-readable and editable, stored at ~/.futureproof/profile.yaml.

This is the "semantic memory" layer - persistent facts about the user that
should be available across all conversations.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from futureproof.memory.checkpointer import get_data_dir
from futureproof.utils.logging import get_logger

# Serialize concurrent profile reads/writes (parallel tool calls)
_profile_lock = threading.Lock()
logger = get_logger(__name__)


@dataclass
class CareerGoal:
    """A career goal with timeline and status."""

    description: str
    target_date: str | None = None
    priority: str = "medium"  # low, medium, high
    status: str = "active"  # active, completed, abandoned
    notes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UserProfile:
    """User profile containing identity, skills, and career context."""

    # Identity
    name: str = ""
    email: str = ""
    location: str = ""

    # Professional summary
    current_role: str = ""
    years_experience: int = 0
    industries: list[str] = field(default_factory=list)

    # Skills and strengths
    technical_skills: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)

    # Career context
    goals: list[CareerGoal] = field(default_factory=list)
    target_roles: list[str] = field(default_factory=list)
    target_companies: list[str] = field(default_factory=list)
    deal_breakers: list[str] = field(default_factory=list)  # e.g., "no relocation", "remote only"

    # Preferences
    preferred_work_style: str = ""  # remote, hybrid, onsite
    salary_expectations: str = ""

    # Metadata
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary for YAML serialization."""
        data = {
            "identity": {
                "name": self.name,
                "email": self.email,
                "location": self.location,
            },
            "professional": {
                "current_role": self.current_role,
                "years_experience": self.years_experience,
                "industries": self.industries,
            },
            "skills": {
                "technical": self.technical_skills,
                "soft": self.soft_skills,
                "languages": self.languages,
                "certifications": self.certifications,
            },
            "career": {
                "goals": [
                    {
                        "description": g.description,
                        "target_date": g.target_date,
                        "priority": g.priority,
                        "status": g.status,
                        "notes": g.notes,
                        "created_at": g.created_at,
                    }
                    for g in self.goals
                ],
                "target_roles": self.target_roles,
                "target_companies": self.target_companies,
                "deal_breakers": self.deal_breakers,
            },
            "preferences": {
                "work_style": self.preferred_work_style,
                "salary_expectations": self.salary_expectations,
            },
            "metadata": {
                "last_updated": self.last_updated,
            },
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserProfile":
        """Create profile from dictionary (loaded from YAML)."""
        identity = data.get("identity", {})
        professional = data.get("professional", {})
        skills = data.get("skills", {})
        career = data.get("career", {})
        preferences = data.get("preferences", {})
        metadata = data.get("metadata", {})

        goals = [
            CareerGoal(
                description=g.get("description", ""),
                target_date=g.get("target_date"),
                priority=g.get("priority", "medium"),
                status=g.get("status", "active"),
                notes=g.get("notes", []),
                created_at=g.get("created_at", datetime.now().isoformat()),
            )
            for g in career.get("goals", [])
        ]

        return cls(
            name=identity.get("name", ""),
            email=identity.get("email", ""),
            location=identity.get("location", ""),
            current_role=professional.get("current_role", ""),
            years_experience=professional.get("years_experience", 0),
            industries=professional.get("industries", []),
            technical_skills=skills.get("technical", []),
            soft_skills=skills.get("soft", []),
            languages=skills.get("languages", []),
            certifications=skills.get("certifications", []),
            goals=goals,
            target_roles=career.get("target_roles", []),
            target_companies=career.get("target_companies", []),
            deal_breakers=career.get("deal_breakers", []),
            preferred_work_style=preferences.get("work_style", ""),
            salary_expectations=preferences.get("salary_expectations", ""),
            last_updated=metadata.get("last_updated", datetime.now().isoformat()),
        )

    def summary(self) -> str:
        """Generate a concise summary for agent context."""
        parts = []

        if self.name:
            parts.append(f"Name: {self.name}")
        if self.current_role:
            parts.append(f"Current Role: {self.current_role}")
        if self.years_experience:
            parts.append(f"Experience: {self.years_experience} years")
        if self.technical_skills:
            parts.append(f"Skills: {', '.join(self.technical_skills[:10])}")
        if self.target_roles:
            parts.append(f"Target Roles: {', '.join(self.target_roles)}")
        if self.deal_breakers:
            parts.append(f"Deal Breakers: {', '.join(self.deal_breakers)}")

        return "\n".join(parts) if parts else "No profile information available."


def get_profile_path() -> Path:
    """Get the path to the user profile YAML file."""
    return get_data_dir() / "profile.yaml"


def load_profile() -> UserProfile:
    """Load user profile from YAML file.

    Returns:
        UserProfile instance. Returns empty profile if file doesn't exist.

    Note:
        For read-modify-write operations, use ``edit_profile`` instead
        to avoid race conditions when tools run in parallel.
    """
    path = get_profile_path()

    if not path.exists():
        return UserProfile()

    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return UserProfile.from_dict(data)
    except (yaml.YAMLError, OSError) as e:
        # Log error but return empty profile to avoid breaking the app
        logger.warning("Could not load profile: %s", e)
        return UserProfile()


def save_profile(profile: UserProfile) -> None:
    """Save user profile to YAML file.

    Args:
        profile: The UserProfile instance to save.

    Note:
        For read-modify-write operations, use ``edit_profile`` instead
        to avoid race conditions when tools run in parallel.
    """
    path = get_profile_path()
    profile.last_updated = datetime.now().isoformat()

    # Write with restricted permissions (owner read/write only)
    with open(path, "w") as f:
        yaml.dump(
            profile.to_dict(),
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    # Set file permissions to 0600 (owner read/write only)
    path.chmod(0o600)


def edit_profile(modifier: Callable[["UserProfile"], None]) -> "UserProfile":
    """Atomically load, modify, and save the profile.

    Holds a lock so that parallel tool calls don't clobber each other.

    Args:
        modifier: A callable that mutates the profile in place.

    Returns:
        The modified profile (after saving).
    """
    with _profile_lock:
        profile = load_profile()
        modifier(profile)
        save_profile(profile)
        return profile
