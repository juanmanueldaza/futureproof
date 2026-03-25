"""Learning Agent — Skill development and expertise building specialist."""


from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.tools.analysis import analyze_skill_gaps
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
from fu7ur3pr00f.agents.tools.market import analyze_market_skills, get_tech_trends
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
    # Analysis — skill focus
    analyze_skill_gaps,
    # Market — tech trends and in-demand skills
    get_tech_trends,
    analyze_market_skills,
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


class LearningAgent(BaseAgent):
    """Skill development, learning roadmaps, and expertise building.

    Specialises in:
    - Personalised learning roadmaps for target roles
    - Identifying the highest-leverage skills to learn next
    - Technology trend analysis (what the market values)
    - Building expertise through teaching (blogs, talks, OSS)
    """

    KEYWORDS = frozenset(
        {
            "learning",
            "study",
            "learn",
            "skills",
            "courses",
            "certification",
            "expert",
            "authority",
            "teaching",
            "conference",
            "talk",
            "blog",
            "write",
            "publish",
            "training",
            "tutorial",
            "practice",
            "improve",
            "master",
            "specialize",
            "roadmap",
            "curriculum",
            "knowledge",
        }
    )

    @property
    def name(self) -> str:
        return "learning"

    @property
    def description(self) -> str:
        return "Skill development and expertise building"

    @property
    def system_prompt(self) -> str:
        return (
            "You are an expert learning strategist for software developers.\n\n"
            "Focus:\n"
            "- Designing personalised learning roadmaps based on the user's goals\n"
            "- Identifying highest-leverage skills using market trend data\n"
            "- Recommending specific resources (courses, books, projects, talks)\n"
            "- Building public expertise through teaching and contribution\n\n"
            "Always: check tech trends and market data, compare current skills against "
            "requirements for the target role, give concrete timelines "
            "(1 month / 3 months / 6 months), and suggest demonstrable outputs."
        )

    @property
    def tools(self) -> list:
        return _TOOLS

    def can_handle(self, intent: str) -> bool:
        return any(kw in intent.lower() for kw in self.KEYWORDS)


__all__ = ["LearningAgent"]
