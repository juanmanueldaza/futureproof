"""Career intelligence tools for the ReAct agent.

Tools are organized by domain:
- profile: get/update user profile and goals
- gathering: collect data from GitHub, GitLab, portfolio, LinkedIn, assessments
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
    gather_github_data,
    gather_gitlab_data,
    gather_linkedin_data,
    gather_portfolio_data,
    get_stored_career_data,
)
from .generation import generate_cv, generate_cv_draft
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

__all__ = [
    # Profile
    "get_user_profile",
    "update_user_goal",
    "update_user_skills",
    "set_target_roles",
    "update_user_name",
    "update_current_role",
    # Gathering
    "gather_github_data",
    "gather_gitlab_data",
    "gather_portfolio_data",
    "gather_linkedin_data",
    "gather_assessment_data",
    "gather_all_career_data",
    "get_stored_career_data",
    # Analysis
    "analyze_skill_gaps",
    "analyze_career_alignment",
    "get_career_advice",
    # Market
    "search_jobs",
    "get_tech_trends",
    "get_salary_insights",
    "analyze_market_fit",
    "analyze_market_skills",
    "gather_market_data",
    # Generation
    "generate_cv",
    "generate_cv_draft",
    # Knowledge
    "search_career_knowledge",
    "get_knowledge_stats",
    "index_career_knowledge",
    "clear_career_knowledge",
    # Memory
    "remember_decision",
    "remember_job_application",
    "recall_memories",
    "get_memory_stats",
    # Registry
    "get_all_tools",
]


def get_all_tools() -> list:
    """Get all career intelligence tools for the agent.

    Returns all 32 tools: profile, gathering, analysis, market, generation,
    knowledge, and memory.
    """
    return [
        # Profile
        get_user_profile,
        update_user_name,
        update_current_role,
        update_user_skills,
        set_target_roles,
        update_user_goal,
        # Gathering
        gather_github_data,
        gather_gitlab_data,
        gather_portfolio_data,
        gather_linkedin_data,
        gather_assessment_data,
        gather_all_career_data,
        get_stored_career_data,
        # Knowledge
        search_career_knowledge,
        get_knowledge_stats,
        index_career_knowledge,
        clear_career_knowledge,
        # Analysis
        analyze_skill_gaps,
        analyze_career_alignment,
        get_career_advice,
        analyze_market_fit,
        analyze_market_skills,
        # Generation
        generate_cv,
        generate_cv_draft,
        # Market Intelligence
        search_jobs,
        get_tech_trends,
        get_salary_insights,
        gather_market_data,
        # Memory
        remember_decision,
        remember_job_application,
        recall_memories,
        get_memory_stats,
    ]
