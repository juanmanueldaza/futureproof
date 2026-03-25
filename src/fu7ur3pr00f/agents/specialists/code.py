"""Code Agent — GitHub, GitLab, and open source strategy specialist."""


from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.tools.gathering import (
    gather_all_career_data,
    gather_assessment_data,
    gather_cv_data,
    gather_linkedin_data,
    gather_portfolio_data,
)
from fu7ur3pr00f.agents.tools.github import (
    get_github_profile,
    get_github_repo,
    search_github_repos,
)
from fu7ur3pr00f.agents.tools.gitlab import (
    get_gitlab_file,
    get_gitlab_project,
    search_gitlab_projects,
)
from fu7ur3pr00f.agents.tools.knowledge import (
    clear_career_knowledge,
    get_knowledge_stats,
    index_career_knowledge,
    search_career_knowledge,
)
from fu7ur3pr00f.agents.tools.market import get_tech_trends
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
    # GitHub
    search_github_repos,
    get_github_repo,
    get_github_profile,
    # GitLab
    search_gitlab_projects,
    get_gitlab_project,
    get_gitlab_file,
    # Tech trends — what's worth building / contributing to
    get_tech_trends,
    # Memory
    remember_decision,
    remember_job_application,
    recall_memories,
    get_memory_stats,
    # Settings
    get_current_config,
    update_setting,
]


class CodeAgent(BaseAgent):
    """GitHub, GitLab, and open source portfolio specialist.

    Specialises in:
    - GitHub/GitLab profile and repository analysis
    - Open source contribution strategy
    - Portfolio gap identification
    - Project visibility and developer branding
    - Selecting side projects for career impact
    """

    KEYWORDS = frozenset(
        {
            "github",
            "gitlab",
            "repos",
            "repositories",
            "code",
            "commits",
            "open source",
            "oss",
            "contributions",
            "projects",
            "portfolio",
            "side project",
            "developer brand",
            "visibility",
            "pull request",
            "fork",
            "star",
            "gist",
            "readme",
        }
    )

    @property
    def name(self) -> str:
        return "code"

    @property
    def description(self) -> str:
        return "GitHub, GitLab, and open source strategy"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a developer portfolio and open source strategist.\n\n"
            "Focus:\n"
            "- Analyse the user's GitHub/GitLab repos and activity\n"
            "- Identify portfolio gaps for their target role\n"
            "- Recommend specific projects aligned with market trends\n"
            "- Optimise GitHub profile for recruiter visibility\n"
            "- Suggest open source projects to contribute to\n\n"
            "Always: pull real repo and profile data before advising, "
            "check tech trends to align project suggestions with demand, "
            "prioritise quality over quantity."
        )

    @property
    def tools(self) -> list:
        return _TOOLS

    def can_handle(self, intent: str) -> bool:
        return any(kw in intent.lower() for kw in self.KEYWORDS)


__all__ = ["CodeAgent"]
