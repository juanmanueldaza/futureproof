"""CV generation tools for the career agent."""

from typing import Literal

from langchain_core.tools import tool
from langgraph.types import interrupt

from futureproof.memory.profile import load_profile


@tool
def generate_cv(
    target_role: str | None = None,
    language: Literal["en", "es"] = "en",
    format: Literal["ats", "creative"] = "ats",
) -> str:
    """Generate a CV/resume for the user.

    Args:
        target_role: Optional role context for the confirmation prompt
        language: Output language - 'en' for English, 'es' for Spanish
        format: CV format - 'ats' for ATS-friendly, 'creative' for visual

    Use this when the user wants to create or update their CV.
    Returns the path to the generated CV file.
    Note: target_role is shown in the confirmation but does not yet tailor
    the CV content. Use the knowledge base and profile to guide CV content.
    """
    # TODO: Pass target_role through to GenerationService for CV tailoring
    # Human-in-the-loop: confirm before generating
    role_note = f" for '{target_role}'" if target_role else ""
    lang_name = "English" if language == "en" else "Spanish"
    approved = interrupt(
        {
            "question": f"Generate {format.upper()} CV{role_note} in {lang_name}?",
            "details": "This will create/overwrite CV files in the output directory.",
        }
    )
    if not approved:
        return "CV generation cancelled."

    from futureproof.generators import create_cv

    output_path = create_cv(language=language, format=format)

    return (
        f"CV generated successfully{role_note}!\n\n"
        f"**Format:** {format.upper()}\n"
        f"**Language:** {lang_name}\n"
        f"**Output:** {output_path}\n\n"
        "The CV has been saved. You can review and edit it as needed."
    )


@tool
def generate_cv_draft(target_role: str) -> str:
    """Generate a quick CV draft/preview for a specific role.

    Args:
        target_role: The role to tailor the CV for

    Use this for a quick preview before generating a full CV.
    """
    profile = load_profile()

    if not profile.name:
        return (
            "Cannot generate a CV without profile information. "
            "Please set up your profile first with your name, experience, and skills."
        )

    # Build a draft summary
    draft_parts = [
        f"# CV Draft for {target_role}",
        "",
        f"**{profile.name}**",
    ]

    if profile.current_role:
        draft_parts.append(f"*{profile.current_role}*")

    draft_parts.append("")

    if profile.technical_skills:
        skills = ", ".join(profile.technical_skills[:12])
        draft_parts.append(f"**Technical Skills:** {skills}")

    if profile.soft_skills:
        soft = ", ".join(profile.soft_skills[:6])
        draft_parts.append(f"**Soft Skills:** {soft}")

    if profile.target_roles:
        targets = ", ".join(profile.target_roles)
        draft_parts.append(f"**Target Roles:** {targets}")

    if profile.goals:
        draft_parts.append("\n**Career Goals:**")
        for goal in profile.goals[:3]:
            draft_parts.append(f"- {goal.description} ({goal.priority} priority)")

    draft_parts.extend(
        [
            "",
            "---",
            "*This is a draft preview. Use generate_cv() for a full, formatted CV.*",
        ]
    )

    return "\n".join(draft_parts)
