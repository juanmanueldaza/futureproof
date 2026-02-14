"""Analysis tools for the career agent."""

from langchain_core.tools import tool

from futureproof.memory.profile import load_profile


@tool
def analyze_skill_gaps(target_role: str) -> str:
    """Analyze the gap between current skills and a target role's requirements.

    Args:
        target_role: The job role to analyze gaps for (e.g., "ML Engineer", "Staff Developer")

    Use this when the user asks about skill gaps, career transitions, or what they need to learn.
    This uses AI to compare the user's skills against typical role requirements.
    """
    try:
        from futureproof.services import AnalysisService

        service = AnalysisService()
        result = service.analyze(action="analyze_gaps", target=target_role)

        if result.success:
            return f"Skill gap analysis for '{target_role}':\n\n{result.content}"
        else:
            return f"Could not complete gap analysis: {result.error}"

    except Exception as e:
        # Fallback to profile-based analysis
        profile = load_profile()
        current_skills = profile.technical_skills + profile.soft_skills

        if not current_skills:
            return (
                f"Cannot analyze gaps for '{target_role}' - no skills recorded. "
                "Please tell me about your technical and soft skills first."
            )

        return (
            f"Skill gap analysis for '{target_role}':\n\n"
            f"Your current skills: {', '.join(current_skills)}\n\n"
            f"Note: Full AI-powered gap analysis requires gathered career data. "
            f"Error: {e}"
        )


@tool
def analyze_career_alignment() -> str:
    """Analyze how well the user's current trajectory aligns with their goals.

    Use this for a comprehensive career analysis including goals, skills, and market fit.
    """
    try:
        from futureproof.services import AnalysisService

        service = AnalysisService()
        result = service.analyze(action="analyze_full")

        if result.success:
            return f"Career alignment analysis:\n\n{result.content}"
        return f"Could not complete analysis: {result.error}"
    except Exception as e:
        return f"Career alignment analysis encountered an error: {e}"


@tool
def get_career_advice(target: str) -> str:
    """Get strategic career advice for reaching a specific goal or role.

    Args:
        target: The target role, goal, or career question

    Use this when the user asks for advice on career decisions or paths.
    """
    try:
        from futureproof.services import AnalysisService

        service = AnalysisService()
        advice = service.get_advice(target)
        return f"Career advice for '{target}':\n\n{advice}"
    except Exception as e:
        return f"Career advice for '{target}' encountered an error: {e}"
