"""Coach Agent — Career growth and leadership specialist."""


from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.tools.analysis import (
    analyze_career_alignment,
    analyze_skill_gaps,
    get_career_advice,
)
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
    # Analysis (core focus)
    analyze_skill_gaps,
    analyze_career_alignment,
    get_career_advice,
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


class CoachAgent(BaseAgent):
    """Career growth, promotions, and leadership coaching.

    Specialises in:
    - Promotion strategy (Senior → Staff → Principal)
    - CliftonStrengths-based development planning
    - Leadership and influence building
    - Skill gap analysis for target roles
    """

    KEYWORDS = frozenset(
        {
            "promotion",
            "promoted",
            "leadership",
            "lead",
            "manager",
            "staff",
            "principal",
            "senior",
            "career growth",
            "career path",
            "influence",
            "office politics",
            "cliftonstrengths",
            "strengths",
            "coaching",
            "mentor",
            "mentoring",
            "visibility",
            "impact",
            "advice",
            "strategy",
            "next step",
        }
    )

    @property
    def name(self) -> str:
        return "coach"

    @property
    def description(self) -> str:
        return "Career growth and leadership coach"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior career coach for software engineers.\n\n"
            "Focus:\n"
            "- Promotion strategy (IC track: Senior → Staff → Principal)\n"
            "- CliftonStrengths-based coaching when data is available\n"
            "- Leadership development and influence building\n"
            "- Concrete skill gap analysis against the user's target role\n\n"
            "Always: search the knowledge base first, reference the user's actual "
            "experience and strengths, give specific action plans with timelines. "
            "Be direct about gaps — don't just affirm what's already strong."
        )

    @property
    def tools(self) -> list:
        return _TOOLS

    def can_handle(self, intent: str) -> bool:
        return any(kw in intent.lower() for kw in self.KEYWORDS)


__all__ = ["CoachAgent"]
