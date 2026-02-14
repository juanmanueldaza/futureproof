"""Career intelligence tools for the ReAct agent.

Tools are organized by domain:
- profile: get/update user profile and goals
- gathering: collect data from portfolio, LinkedIn, assessments
- analysis: skill gaps, career alignment, advice
- market: job search, tech trends, salary insights, market fit/skills analysis
- generation: CV drafts and documents
- knowledge: RAG search and indexing over career data
- memory: episodic memory (decisions, applications)
"""

from .analysis import analyze_career_alignment, analyze_skill_gaps, get_career_advice
from .gathering import (
    gather_all_career_data,
    gather_assessment_data,
    gather_linkedin_data,
    gather_portfolio_data,
    get_stored_career_data,
)
from .generation import generate_cv, generate_cv_draft
from .github import get_github_profile, get_github_repo, search_github_repos
from .gitlab import get_gitlab_file, get_gitlab_project, search_gitlab_projects
from .knowledge import (
    clear_career_knowledge,
    get_knowledge_stats,
    index_career_knowledge,
    search_career_knowledge,
)
from .market import (
    analyze_market_fit,
    analyze_market_skills,
    gather_market_data,
    get_salary_insights,
    get_tech_trends,
    search_jobs,
)
from .memory import (
    get_memory_stats,
    recall_memories,
    remember_decision,
    remember_job_application,
)
from .profile import (
    get_user_profile,
    set_target_roles,
    update_current_role,
    update_user_goal,
    update_user_name,
    update_user_skills,
)

# Single source of truth for all agent tools.
# Imports above make them available; this list drives __all__ and get_all_tools().
_ALL_TOOLS = [
    # Profile
    get_user_profile,
    update_user_name,
    update_current_role,
    update_user_skills,
    set_target_roles,
    update_user_goal,
    # Gathering
    gather_portfolio_data,
    gather_linkedin_data,
    gather_assessment_data,
    gather_all_career_data,
    get_stored_career_data,
    # GitHub
    search_github_repos,
    get_github_repo,
    get_github_profile,
    # GitLab
    search_gitlab_projects,
    get_gitlab_project,
    get_gitlab_file,
    # Knowledge
    search_career_knowledge,
    get_knowledge_stats,
    index_career_knowledge,
    clear_career_knowledge,
    # Analysis
    analyze_skill_gaps,
    analyze_career_alignment,
    get_career_advice,
    # Market
    search_jobs,
    get_tech_trends,
    get_salary_insights,
    analyze_market_fit,
    analyze_market_skills,
    gather_market_data,
    # Generation
    generate_cv,
    generate_cv_draft,
    # Memory
    remember_decision,
    remember_job_application,
    recall_memories,
    get_memory_stats,
]

__all__ = [getattr(t, "__name__", t.name) for t in _ALL_TOOLS] + ["get_all_tools"]


def get_all_tools() -> list:
    """Get all career intelligence tools for the agent.

    Returns all 36 tools: profile, gathering, github, gitlab, analysis,
    market, generation, knowledge, and memory.
    """
    return list(_ALL_TOOLS)
