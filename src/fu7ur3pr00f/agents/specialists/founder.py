"""Founder Agent — Startups and entrepreneurship specialist."""


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
    # Analysis — founder-market fit
    analyze_skill_gaps,
    analyze_career_alignment,
    get_career_advice,
    # Market — opportunity and demand research
    search_jobs,
    get_salary_insights,
    analyze_market_fit,
    analyze_market_skills,
    get_tech_trends,
    gather_market_data,
    # Financial — runway and revenue modelling
    convert_currency,
    compare_salary_ppp,
    # Memory
    remember_decision,
    remember_job_application,
    recall_memories,
    get_memory_stats,
    # Settings
    get_current_config,
    update_setting,
]


class FounderAgent(BaseAgent):
    """Startups, entrepreneurship, and developer-to-founder transition.

    Specialises in:
    - Idea validation and founder-market fit analysis
    - MVP scoping based on existing skills
    - Bootstrapping vs. fundraising trade-offs
    - Market opportunity research
    - Developer-to-founder transition planning
    """

    KEYWORDS = frozenset(
        {
            "startup",
            "founder",
            "cofounder",
            "co-founder",
            "launch",
            "product",
            "entrepreneur",
            "mvp",
            "side project",
            "business idea",
            "company",
            "bootstrap",
            "fundraising",
            "revenue",
            "saas",
            "indie",
            "solo",
            "validate",
            "build a product",
            "productize",
        }
    )

    @property
    def name(self) -> str:
        return "founder"

    @property
    def description(self) -> str:
        return "Startups and developer-to-founder strategy"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a startup advisor specialising in developer-founders.\n\n"
            "Focus:\n"
            "- Assess founder-market fit from the user's skills and experience\n"
            "- Scope MVPs the user can build with their existing stack\n"
            "- Research market demand and opportunity size\n"
            "- Compare bootstrapping vs. funding scenarios with real numbers\n"
            "- Plan the developer-to-founder transition step by step\n\n"
            "Always: pull real market and salary data, be realistic about timelines "
            "and effort, reference the user's actual technical stack when suggesting "
            "what to build, prefer sustainable bootstrapping over VC by default."
        )

    @property
    def tools(self) -> list:
        return _TOOLS

    def can_handle(self, intent: str) -> bool:
        return any(kw in intent.lower() for kw in self.KEYWORDS)


__all__ = ["FounderAgent"]
