"""Profile management tools for the career agent."""

import logging

from langchain_core.tools import tool

from futureproof.memory.profile import CareerGoal, load_profile, save_profile

logger = logging.getLogger(__name__)


@tool
def get_user_profile() -> str:
    """Get the current user's career profile including skills, goals, and preferences.

    Use this to understand the user's background before giving advice or searching for jobs.
    """
    profile = load_profile()

    if not profile.name:
        return (
            "No profile configured yet. The user should set up their profile with "
            "their name, current role, skills, and career goals. You can help them "
            "by asking about these details."
        )

    return profile.summary()


@tool
def update_user_goal(goal_description: str, priority: str = "medium") -> str:
    """Add or update a career goal for the user.

    Args:
        goal_description: Description of the career goal
        priority: Priority level (low, medium, high)

    Use this when the user mentions a new career goal or aspiration.
    """
    profile = load_profile()

    new_goal = CareerGoal(
        description=goal_description,
        priority=priority,
    )
    profile.goals.append(new_goal)
    save_profile(profile)

    return f"Added career goal: '{goal_description}' with {priority} priority."


@tool
def update_user_skills(skills: list[str], skill_type: str = "technical") -> str:
    """Update the user's skill list.

    Args:
        skills: List of skills to add
        skill_type: Either 'technical' or 'soft'

    Use this when the user mentions skills they have or want to track.
    """
    profile = load_profile()

    if skill_type == "technical":
        existing = set(profile.technical_skills)
        existing.update(skills)
        profile.technical_skills = sorted(existing)
    else:
        existing = set(profile.soft_skills)
        existing.update(skills)
        profile.soft_skills = sorted(existing)

    save_profile(profile)
    return f"Updated {skill_type} skills. Current {skill_type} skills: {', '.join(skills)}"


@tool
def set_target_roles(roles: list[str]) -> str:
    """Set the user's target job roles.

    Args:
        roles: List of job roles the user is targeting

    Use this when the user mentions roles they're interested in.
    """
    profile = load_profile()
    profile.target_roles = roles
    save_profile(profile)

    return f"Set target roles to: {', '.join(roles)}"


@tool
def update_user_name(name: str) -> str:
    """Set or update the user's name in their profile.

    Args:
        name: The user's full name

    Use this when the user introduces themselves or wants to update their name.
    """
    profile = load_profile()
    profile.name = name
    save_profile(profile)
    return f"Updated profile name to: {name}"


@tool
def update_current_role(role: str, years_experience: int | None = None) -> str:
    """Update the user's current job role and experience.

    Args:
        role: Current job title/role
        years_experience: Optional years of experience in this role

    Use this when the user mentions their current position.
    """
    profile = load_profile()
    profile.current_role = role
    if years_experience is not None:
        profile.years_experience = years_experience
    save_profile(profile)

    exp_str = f" ({years_experience} years)" if years_experience else ""
    return f"Updated current role to: {role}{exp_str}"
