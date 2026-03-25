"""Jobs Agent — Job search and market intelligence specialist."""


from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.tools.analysis import (
    analyze_career_alignment,
    analyze_skill_gaps,
    get_career_advice,
)
from fu7ur3pr00f.agents.tools.financial import compare_salary_ppp, convert_currency
from fu7ur3pr00f.agents.tools.gathering import (
    gather_all_career_data,
    gather_assessment_data,
    gather_cv_data,
    gather_linkedin_data,
    gather_portfolio_data,
)
from fu7ur3pr00f.agents.tools.generation import generate_cv, generate_cv_draft
from fu7ur3pr00f.agents.tools.knowledge import (
    clear_career_knowledge,
    get_knowledge_stats,
    index_career_knowledge,
    search_career_knowledge,
)
from fu7ur3pr00f.agents.tools.market import (
    analyze_market_fit,
    analyze_market_skills,
    gather_market_data,
    get_salary_insights,
    get_tech_trends,
    search_jobs,
)
from fu7ur3pr00f.agents.tools.memory import (
    get_memory_stats,
    recall_memories,
    remember_decision,
    remember_job_application,
)
from fu7ur3pr00f.agents.tools.profile import (
    get_user_profile,
    set_target_roles,
    update_current_role,
    update_salary_info,
    update_user_goal,
    update_user_name,
    update_user_skills,
)
from fu7ur3pr00f.agents.tools.settings import get_current_config, update_setting

_TOOLS: list = [
    # Profile
    get_user_profile,
    update_user_name,
    update_current_role,
    update_salary_info,
    update_user_skills,
    set_target_roles,
    update_user_goal,
    # Gathering
    gather_portfolio_data,
    gather_linkedin_data,
    gather_assessment_data,
    gather_cv_data,
    gather_all_career_data,
    # Knowledge
    search_career_knowledge,
    get_knowledge_stats,
    index_career_knowledge,
    clear_career_knowledge,
    # Analysis — market alignment
    analyze_skill_gaps,
    analyze_career_alignment,
    get_career_advice,
    # Market — full suite
    search_jobs,
    get_salary_insights,
    analyze_market_fit,
    analyze_market_skills,
    get_tech_trends,
    gather_market_data,
    # Financial — salary comparisons
    convert_currency,
    compare_salary_ppp,
    # Generation
    generate_cv,
    generate_cv_draft,
    # Memory
    remember_decision,
    remember_job_application,
    recall_memories,
    get_memory_stats,
    # Settings
    get_current_config,
    update_setting,
]


class JobsAgent(BaseAgent):
    """Job search, market intelligence, and compensation specialist.

    Specialises in:
    - Job board search across 7 boards + Hacker News
    - Salary benchmarking with PPP-adjusted comparisons
    - Market fit analysis for target roles
    - CV optimisation for specific job openings
    - Offer evaluation and negotiation strategy
    """

    KEYWORDS = frozenset(
        {
            "jobs",
            "job",
            "hiring",
            "interview",
            "salary",
            "compensation",
            "benefits",
            "remote",
            "work from home",
            "job search",
            "apply",
            "resume",
            "cv",
            "negotiate",
            "offer",
            "market",
            "opportunity",
            "recruiter",
            "application",
            "cover letter",
            "market fit",
            "search",
            "find",
            "looking for work",
        }
    )

    @property
    def name(self) -> str:
        return "jobs"

    @property
    def description(self) -> str:
        return "Job search and market intelligence"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a job search strategist for software developers.\n\n"
            "Focus:\n"
            "- Search job boards and Hacker News for live opportunities\n"
            "- Benchmark salary with PPP adjustments for any location\n"
            "- Analyse market fit and identify the user's strongest selling points\n"
            "- Help generate targeted CVs for specific roles\n"
            "- Advise on offer evaluation and negotiation\n\n"
            "Always: search jobs and get salary data before giving advice, "
            "be specific about salary ranges (use the financial tools), "
            "warn about common pitfalls (lowball offers, red-flag job descriptions)."
        )

    @property
    def tools(self) -> list:
        return _TOOLS

    def can_handle(self, intent: str) -> bool:
        return any(kw in intent.lower() for kw in self.KEYWORDS)


__all__ = ["JobsAgent"]
