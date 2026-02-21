"""Profile management tools for the career agent."""

import logging

from langchain_core.tools import tool

from futureproof.memory.profile import CareerGoal, edit_profile, load_profile

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
    new_goal = CareerGoal(description=goal_description, priority=priority)
    edit_profile(lambda p: p.goals.append(new_goal))

    return f"Added career goal: '{goal_description}' with {priority} priority."


@tool
def update_user_skills(skills: list[str], skill_type: str = "technical") -> str:
    """Update the user's skill list.

    Args:
        skills: List of skills to add
        skill_type: Either 'technical' or 'soft'

    Use this when the user mentions skills they have or want to track.
    """

    def _update(p):
        if skill_type == "technical":
            existing = set(p.technical_skills)
            existing.update(skills)
            p.technical_skills = sorted(existing)
        else:
            existing = set(p.soft_skills)
            existing.update(skills)
            p.soft_skills = sorted(existing)

    profile = edit_profile(_update)
    merged = profile.technical_skills if skill_type == "technical" else profile.soft_skills
    return f"Updated {skill_type} skills. Current {skill_type} skills: {', '.join(merged)}"


@tool
def set_target_roles(roles: list[str]) -> str:
    """Set the user's target job roles.

    Args:
        roles: List of job roles the user is targeting

    Use this when the user mentions roles they're interested in.
    """
    edit_profile(lambda p: setattr(p, "target_roles", roles))

    return f"Set target roles to: {', '.join(roles)}"


@tool
def update_user_name(name: str) -> str:
    """Set or update the user's name in their profile.

    Args:
        name: The user's full name

    Use this when the user introduces themselves or wants to update their name.
    """
    edit_profile(lambda p: setattr(p, "name", name))
    return f"Updated profile name to: {name}"


@tool
def update_current_role(role: str, years_experience: int | None = None) -> str:
    """Update the user's current job role and experience.

    Args:
        role: Current job title/role
        years_experience: Optional years of experience in this role

    Use this when the user mentions their current position.
    """

    def _update(p):
        p.current_role = role
        if years_experience is not None:
            p.years_experience = years_experience

    edit_profile(_update)

    exp_str = f" ({years_experience} years)" if years_experience else ""
    return f"Updated current role to: {role}{exp_str}"


@tool
def update_salary_info(
    current_salary: str,
    currency: str = "USD",
    includes_bonus: bool = False,
    notes: str = "",
) -> str:
    """Save the user's current compensation information.

    Args:
        current_salary: Current base salary amount or range (e.g., "95000", "90k-100k")
        currency: Currency code (e.g., "USD", "EUR", "GBP")
        includes_bonus: Whether the amount includes bonuses/equity
        notes: Additional compensation details (e.g., "plus 10% annual bonus")

    Use this when the user shares their current salary or compensation details.
    This establishes a baseline for salary recommendations based on market data.
    """
    bonus_note = " (includes bonus/equity)" if includes_bonus else ""
    extra = f" — {notes}" if notes else ""
    info = f"{currency} {current_salary}{bonus_note}{extra}"

    edit_profile(lambda p: setattr(p, "salary_expectations", info))
    return f"Saved current compensation: {info}"
