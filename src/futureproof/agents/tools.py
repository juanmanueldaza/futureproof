"""Career intelligence tools for the ReAct agent.

These tools wrap existing FutureProof services and make them available
to the LLM agent for dynamic invocation during conversations.

Tools are organized by category:
- Profile Management: get/update user profile and goals
- Data Gathering: collect data from GitHub, GitLab, portfolio
- Analysis: skill gaps, market analysis, career advice
- Generation: CV drafts and documents
- Market Intelligence: job search, tech trends
"""

import logging
import uuid
from typing import Literal

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.types import interrupt

from futureproof.memory.profile import CareerGoal, load_profile, save_profile

logger = logging.getLogger(__name__)


# =============================================================================
# Profile Management Tools
# =============================================================================


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
    profile = load_profile()

    new_goal = CareerGoal(
        description=goal_description,
        priority=priority,
    )
    profile.goals.append(new_goal)
    save_profile(profile)

    return f"Added career goal: '{goal_description}' with {priority} priority."


@tool
def update_user_skills(skills: list[str], skill_type: str = "technical") -> str:
    """Update the user's skill list.

    Args:
        skills: List of skills to add
        skill_type: Either 'technical' or 'soft'

    Use this when the user mentions skills they have or want to track.
    """
    profile = load_profile()

    if skill_type == "technical":
        existing = set(profile.technical_skills)
        existing.update(skills)
        profile.technical_skills = sorted(existing)
    else:
        existing = set(profile.soft_skills)
        existing.update(skills)
        profile.soft_skills = sorted(existing)

    save_profile(profile)
    return f"Updated {skill_type} skills. Current {skill_type} skills: {', '.join(skills)}"


@tool
def set_target_roles(roles: list[str]) -> str:
    """Set the user's target job roles.

    Args:
        roles: List of job roles the user is targeting

    Use this when the user mentions roles they're interested in.
    """
    profile = load_profile()
    profile.target_roles = roles
    save_profile(profile)

    return f"Set target roles to: {', '.join(roles)}"


@tool
def update_user_name(name: str) -> str:
    """Set or update the user's name in their profile.

    Args:
        name: The user's full name

    Use this when the user introduces themselves or wants to update their name.
    """
    profile = load_profile()
    profile.name = name
    save_profile(profile)
    return f"Updated profile name to: {name}"


@tool
def update_current_role(role: str, years_experience: int | None = None) -> str:
    """Update the user's current job role and experience.

    Args:
        role: Current job title/role
        years_experience: Optional years of experience in this role

    Use this when the user mentions their current position.
    """
    profile = load_profile()
    profile.current_role = role
    if years_experience is not None:
        profile.years_experience = years_experience
    save_profile(profile)

    exp_str = f" ({years_experience} years)" if years_experience else ""
    return f"Updated current role to: {role}{exp_str}"


# =============================================================================
# Data Gathering Tools
# =============================================================================


@tool
def gather_github_data(username: str | None = None) -> str:
    """Gather the user's GitHub profile data including repositories and contributions.

    Args:
        username: Optional GitHub username. If not provided, uses config setting.

    Use this when you need current information about the user's GitHub activity,
    projects, or technical contributions. This fetches fresh data from GitHub.
    """
    try:
        from futureproof.services import GathererService

        service = GathererService()
        output_path = service.gather_github(username)

        # Load the gathered data to provide a summary
        from futureproof.utils.data_loader import load_career_data

        data = load_career_data()
        github_data = data.get("github", {})

        if github_data and isinstance(github_data, dict):
            repos = github_data.get("repositories", [])
            contributions = github_data.get("contributions", {})

            summary_parts = [f"Successfully gathered GitHub data. Saved to: {output_path}"]
            if repos:
                summary_parts.append(f"\nFound {len(repos)} repositories:")
                top_repos = repos[:5] if len(repos) > 5 else repos
                for repo in top_repos:
                    name = repo.get("name", "unknown")
                    lang = repo.get("language", "unknown")
                    stars = repo.get("stars", 0)
                    summary_parts.append(f"  - {name} ({lang}) ⭐{stars}")

            if contributions:
                total = contributions.get("total_contributions", 0)
                summary_parts.append(f"\nTotal contributions: {total}")

            return "\n".join(summary_parts)

        return f"GitHub data gathered successfully. Saved to: {output_path}"

    except Exception as e:
        logger.exception("Error gathering GitHub data")
        return f"Error gathering GitHub data: {e}"


@tool
def gather_gitlab_data(username: str | None = None) -> str:
    """Gather the user's GitLab profile data including projects and merge requests.

    Args:
        username: Optional GitLab username. If not provided, uses config setting.

    Use this when you need information about the user's GitLab activity and projects.
    """
    try:
        from futureproof.services import GathererService

        service = GathererService()
        output_path = service.gather_gitlab(username)
        return f"GitLab data gathered successfully. Saved to: {output_path}"

    except Exception as e:
        logger.exception("Error gathering GitLab data")
        return f"Error gathering GitLab data: {e}"


@tool
def gather_portfolio_data(url: str | None = None) -> str:
    """Gather data from the user's portfolio website.

    Args:
        url: Optional portfolio URL. If not provided, uses config setting.

    Use this to collect information from the user's personal website or portfolio.
    """
    try:
        from futureproof.services import GathererService

        service = GathererService()
        output_path = service.gather_portfolio(url)
        return f"Portfolio data gathered successfully. Saved to: {output_path}"

    except Exception as e:
        logger.exception("Error gathering portfolio data")
        return f"Error gathering portfolio data: {e}"


@tool
def gather_all_career_data() -> str:
    """Gather data from all configured sources (GitHub, GitLab, Portfolio).

    Use this to refresh all career data at once. This may take a minute.
    """
    # Human-in-the-loop: confirm before gathering from all sources
    approved = interrupt(
        {
            "question": "Gather data from all configured sources?",
            "details": "This will fetch from GitHub, GitLab, and Portfolio. May take a minute.",
        }
    )
    if not approved:
        return "Data gathering cancelled."

    try:
        from futureproof.services import GathererService

        service = GathererService()
        results = service.gather_all()

        summary_parts = ["Career data gathering complete:"]
        for source, success in results.items():
            status = "✓" if success else "✗"
            summary_parts.append(f"  {status} {source}")

        successful = sum(1 for s in results.values() if s)
        total = len(results)
        summary_parts.append(f"\n{successful}/{total} sources gathered successfully.")

        return "\n".join(summary_parts)

    except Exception as e:
        logger.exception("Error gathering career data")
        return f"Error gathering career data: {e}"


@tool
def get_stored_career_data() -> str:
    """Get a summary of all stored career data without fetching new data.

    Use this to see what career data is already available locally.
    """
    try:
        from futureproof.utils.data_loader import load_career_data

        data = load_career_data()

        summary_parts = ["Stored career data summary:"]

        # Data is stored as markdown strings, not parsed dicts
        # Check what data sources are available

        github_data = data.get("github_data", "")
        if github_data:
            # Count approximate repos by looking for repo markers in markdown
            lines = github_data.count("\n")
            summary_parts.append(f"\n**GitHub:** Data available ({lines} lines)")

        gitlab_data = data.get("gitlab_data", "")
        if gitlab_data:
            lines = gitlab_data.count("\n")
            summary_parts.append(f"\n**GitLab:** Data available ({lines} lines)")

        portfolio_data = data.get("portfolio_data", "")
        if portfolio_data:
            lines = portfolio_data.count("\n")
            summary_parts.append(f"\n**Portfolio:** Data available ({lines} lines)")

        linkedin_data = data.get("linkedin_data", "")
        if linkedin_data:
            lines = linkedin_data.count("\n")
            summary_parts.append(f"\n**LinkedIn:** Data available ({lines} lines)")

        assessment_data = data.get("assessment_data", "")
        if assessment_data:
            lines = assessment_data.count("\n")
            summary_parts.append(f"\n**CliftonStrengths:** Assessment available ({lines} lines)")

        if len(summary_parts) == 1:
            return "No career data stored yet. Use gather_all_career_data() to collect data."

        return "\n".join(summary_parts)

    except Exception as e:
        logger.exception("Error loading career data")
        return f"Error loading career data: {e}"


# =============================================================================
# Analysis Tools
# =============================================================================


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
        result = service.analyze(action="analyze_gaps")

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
        else:
            return f"Could not complete analysis: {result.error}"

    except Exception as e:
        logger.exception("Error in career analysis")
        return f"Error performing career analysis: {e}"


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
        logger.exception("Error getting career advice")
        return f"Error getting career advice: {e}. I can still provide general guidance."


# =============================================================================
# Market Intelligence Tools
# =============================================================================


@tool
async def search_jobs(
    query: str,
    location: str = "remote",
    limit: int = 20,
) -> str:
    """Search for job opportunities matching the query.

    Args:
        query: Job search query (e.g., "ML Engineer", "Python Developer")
        location: Location filter (e.g., "remote", "New York", "Europe")
        limit: Maximum number of results to return

    Use this when the user asks about job opportunities or wants to see what's available.
    """
    try:
        from futureproof.gatherers.market import JobMarketGatherer

        gatherer = JobMarketGatherer()
        data = await gatherer.gather(role=query, location=location, limit=limit)

        # Convert to readable summary
        jobs = data.get("job_listings", [])
        summary = data.get("summary", {})
        errors = data.get("errors", [])

        result_parts = [f"Job search results for '{query}' in '{location}':"]
        total = summary.get("total_jobs", 0)
        src_count = len(summary.get("sources", []))
        result_parts.append(f"\nFound {total} jobs from {src_count} sources")

        if summary.get("remote_positions"):
            result_parts.append(f"Remote positions: {summary['remote_positions']}")

        if jobs:
            result_parts.append("\n**Top opportunities:**")
            for job in jobs[:10]:
                title = job.get("title", "Unknown")
                company = job.get("company", "Unknown")
                job_loc = job.get("location", location)
                salary = job.get("salary", "")
                salary_str = f" - {salary}" if salary else ""
                result_parts.append(f"\n- **{title}** at {company}")
                result_parts.append(f"  Location: {job_loc}{salary_str}")

        if errors:
            result_parts.append(f"\nNote: Some sources had issues: {len(errors)} errors")

        return "\n".join(result_parts)

    except Exception as e:
        logger.exception("Error searching jobs")
        return f"Error searching jobs: {e}"


@tool
async def get_tech_trends(topic: str = "") -> str:
    """Get current technology trends and hiring patterns from Hacker News.

    Args:
        topic: Optional topic to focus on (e.g., "Python", "Rust", "AI")

    Use this to understand what technologies are trending and what companies are hiring for.
    """
    try:
        from futureproof.gatherers.market import TechTrendsGatherer

        gatherer = TechTrendsGatherer()
        data = await gatherer.gather(topic=topic)

        # Convert to readable summary
        stories = data.get("trending_stories", [])
        hiring = data.get("hiring_trends", {})
        hn_jobs = data.get("hn_job_postings", [])
        errors = data.get("errors", [])

        result_parts = [f"Tech trends report{f' for {topic}' if topic else ''}:"]

        if stories:
            result_parts.append(f"\n**Trending discussions:** {len(stories)} stories")
            for story in stories[:5]:
                title = story.get("title", "")
                points = story.get("points", 0)
                result_parts.append(f"  - {title} ({points} pts)")

        if hiring:
            result_parts.append("\n**Hiring trends:**")
            if hiring.get("top_technologies"):
                techs = [t[0] for t in hiring["top_technologies"][:8]]
                result_parts.append(f"  Top technologies: {', '.join(techs)}")
            if hiring.get("remote_percentage"):
                result_parts.append(f"  Remote-friendly: {hiring['remote_percentage']}%")

        if hn_jobs:
            result_parts.append(f"\n**HN Job postings:** {len(hn_jobs)} found")
            with_salary = sum(1 for j in hn_jobs if j.get("salary_min"))
            result_parts.append(f"  With salary info: {with_salary}")

        if errors:
            result_parts.append(f"\nNote: Some data unavailable ({len(errors)} errors)")

        return "\n".join(result_parts)

    except Exception as e:
        logger.exception("Error getting tech trends")
        return f"Error getting tech trends: {e}"


@tool
async def get_salary_insights(role: str, location: str = "remote") -> str:
    """Get salary information for a specific role and location.

    Args:
        role: Job role to research (e.g., "Senior Python Developer")
        location: Location for salary data (e.g., "remote", "San Francisco")

    Use this when the user asks about salary expectations or compensation.
    """
    try:
        from futureproof.gatherers.market import JobMarketGatherer

        gatherer = JobMarketGatherer()
        data = await gatherer.gather(
            role=role,
            location=location,
            include_salary=True,
            limit=10,
        )

        salary_data = data.get("salary_data", [])
        jobs_with_salary = [j for j in data.get("job_listings", []) if j.get("salary")]

        result_parts = [f"Salary insights for '{role}' ({location}):"]

        if jobs_with_salary:
            result_parts.append(f"\n**From job listings:** ({len(jobs_with_salary)} with salary)")
            for job in jobs_with_salary[:5]:
                company = job.get("company", "Unknown")
                salary = job.get("salary", "")
                result_parts.append(f"  - {company}: {salary}")

        if salary_data:
            result_parts.append("\n**Salary research:**")
            for item in salary_data[:3]:
                title = item.get("title", "")
                snippet = item.get("description", item.get("snippet", ""))[:200]
                if title:
                    result_parts.append(f"  - {title}")
                if snippet:
                    result_parts.append(f"    {snippet}...")

        if not salary_data and not jobs_with_salary:
            result_parts.append("\nNo specific salary data found. Try broadening the search.")

        return "\n".join(result_parts)

    except Exception as e:
        logger.exception("Error getting salary insights")
        return f"Error getting salary insights: {e}"


# =============================================================================
# Generation Tools
# =============================================================================


@tool
def generate_cv(
    target_role: str | None = None,
    language: Literal["en", "es"] = "en",
    format: Literal["ats", "creative"] = "ats",
) -> str:
    """Generate a CV/resume tailored for a specific role.

    Args:
        target_role: Optional role to tailor the CV for
        language: Output language - 'en' for English, 'es' for Spanish
        format: CV format - 'ats' for ATS-friendly, 'creative' for visual

    Use this when the user wants to create or update their CV.
    Returns the path to the generated CV file.
    """
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

    try:
        from futureproof.services import GenerationService

        service = GenerationService()
        output_path = service.generate_cv(language=language, format=format)

        return (
            f"CV generated successfully{role_note}!\n\n"
            f"**Format:** {format.upper()}\n"
            f"**Language:** {lang_name}\n"
            f"**Output:** {output_path}\n\n"
            "The CV has been saved. You can review and edit it as needed."
        )

    except Exception as e:
        logger.exception("Error generating CV")
        return f"Error generating CV: {e}"


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


# =============================================================================
# Knowledge Base Tools (RAG)
# =============================================================================


@tool
def search_career_knowledge(
    query: str,
    sources: list[str] | None = None,
    limit: int = 5,
) -> str:
    """Search the career knowledge base for relevant information.

    Args:
        query: What to search for (e.g., "Python projects", "leadership experience")
        sources: Optional filter by source (github, gitlab, linkedin, portfolio, assessment)
        limit: Maximum results to return

    Use this to find specific information from the user's career history
    instead of relying on general context. More efficient than loading
    all career data. Examples:
    - "Python projects" to find Python-related work
    - "leadership" to find management or leadership experience
    - "recent contributions" for recent activity
    """
    try:
        from futureproof.services.knowledge_service import KnowledgeService

        service = KnowledgeService()
        results = service.search(query, limit=limit, sources=sources)

        if not results:
            return (
                f"No results found for '{query}'. "
                "Try a different query or check if career data has been indexed."
            )

        parts = [f"Found {len(results)} relevant results for '{query}':"]
        for i, result in enumerate(results, 1):
            source = result.get("source", "unknown")
            section = result.get("section", "")
            content = result.get("content", "")[:500]  # Truncate for display
            parts.append(f"\n**{i}. [{source}] {section}**")
            parts.append(content)

        return "\n".join(parts)

    except ImportError:
        return "Knowledge base not available (ChromaDB not installed)."
    except Exception as e:
        logger.exception("Error searching knowledge base")
        return f"Error searching knowledge base: {e}"


@tool
def get_knowledge_stats() -> str:
    """Get statistics about the career knowledge base.

    Shows what career data is indexed and available for search.
    Use this to see if the knowledge base has been populated.
    """
    try:
        from futureproof.services.knowledge_service import KnowledgeService

        service = KnowledgeService()
        stats = service.get_stats()

        total = stats.get("total_chunks", 0)
        if total == 0:
            return (
                "Career knowledge base is empty. "
                "Run `futureproof index` to index your gathered career data."
            )

        parts = ["Career Knowledge Base Statistics:"]
        parts.append(f"\nTotal chunks indexed: {total}")
        parts.append("\nBy source:")
        for source, count in stats.get("by_source", {}).items():
            if count > 0:
                parts.append(f"  - {source}: {count} chunks")

        return "\n".join(parts)

    except ImportError:
        return "Knowledge base not available (ChromaDB not installed)."
    except Exception as e:
        logger.exception("Error getting knowledge stats")
        return f"Error getting stats: {e}"


# =============================================================================
# Episodic Memory Tools
# =============================================================================


@tool
def remember_decision(
    decision: str,
    context: str,
    outcome: str = "",
    runtime: ToolRuntime = None,  # type: ignore[assignment]
) -> str:
    """Store a career decision in long-term memory.

    Args:
        decision: The decision that was made
        context: Context and reasoning behind the decision
        outcome: Optional outcome if known

    Use this when the user makes an important career decision that should be
    remembered across sessions, such as rejecting a job offer, choosing a
    technology stack, or setting a career direction.
    """
    memory_id = str(uuid.uuid4())
    text = f"{decision}. Context: {context}"
    if outcome:
        text += f". Outcome: {outcome}"

    # Write to LangGraph InMemoryStore (cross-thread runtime access)
    if runtime and runtime.store:
        try:
            runtime.store.put(
                ("default", "decisions"),
                memory_id,
                {"text": text, "type": "decision", "outcome": outcome},
            )
        except Exception:
            logger.debug("InMemoryStore write failed (non-critical)", exc_info=True)

    # Write to ChromaDB (persistent storage)
    try:
        from futureproof.memory.episodic import get_episodic_store
        from futureproof.memory.episodic import remember_decision as create_decision

        store = get_episodic_store()
        memory = create_decision(decision, context, outcome)
        store.remember(memory)
    except ImportError:
        logger.warning("ChromaDB not available - episodic memory disabled")
    except Exception as e:
        logger.exception("Error storing decision to ChromaDB")
        return f"Could not store decision: {e}"

    return f"Remembered: '{decision}'. I'll be able to recall this in future conversations."


@tool
def remember_job_application(
    company: str,
    role: str,
    status: str,
    notes: str = "",
    runtime: ToolRuntime = None,  # type: ignore[assignment]
) -> str:
    """Record a job application in long-term memory.

    Args:
        company: Company name
        role: Role applied for
        status: Status (applied, interviewing, rejected, offer, accepted, declined)
        notes: Additional notes about the application

    Use this to track job applications across sessions.
    """
    memory_id = str(uuid.uuid4())
    text = f"Applied to {company} for {role}. Status: {status}"
    if notes:
        text += f". {notes}"

    # Write to LangGraph InMemoryStore
    if runtime and runtime.store:
        try:
            runtime.store.put(
                ("default", "applications"),
                memory_id,
                {
                    "text": text,
                    "type": "application",
                    "company": company,
                    "role": role,
                    "status": status,
                },
            )
        except Exception:
            logger.debug("InMemoryStore write failed (non-critical)", exc_info=True)

    # Write to ChromaDB (persistent storage)
    try:
        from futureproof.memory.episodic import get_episodic_store, remember_application

        store = get_episodic_store()
        memory = remember_application(company, role, status, notes)
        store.remember(memory)
    except ImportError:
        logger.warning("ChromaDB not available")
    except Exception as e:
        logger.exception("Error storing application to ChromaDB")
        return f"Could not store application: {e}"

    return f"Recorded application to {company} for {role} (status: {status})."


@tool
def recall_memories(
    query: str,
    limit: int = 5,
    runtime: ToolRuntime = None,  # type: ignore[assignment]
) -> str:
    """Search long-term memory for relevant past experiences.

    Args:
        query: What to search for (semantic search)
        limit: Maximum number of memories to return

    Use this to recall past decisions, job applications, or conversations
    that are relevant to the current discussion.
    """
    result_parts: list[str] = []

    # Search ChromaDB (persistent, primary source)
    try:
        from futureproof.memory.episodic import get_episodic_store

        store = get_episodic_store()
        memories = store.recall(query, limit=limit)

        if memories:
            result_parts.append(f"Found {len(memories)} relevant memories:")
            for mem in memories:
                date_str = mem.timestamp.strftime("%Y-%m-%d")
                result_parts.append(f"\n**[{mem.memory_type.value}] {date_str}**")
                result_parts.append(f"  {mem.content}")
                if mem.context:
                    result_parts.append(f"  Context: {mem.context}")

    except ImportError:
        logger.debug("ChromaDB not available")
    except Exception:
        logger.exception("Error recalling from ChromaDB")

    # Also search InMemoryStore for recent session memories
    if runtime and runtime.store:
        try:
            for namespace in [("default", "decisions"), ("default", "applications")]:
                items = runtime.store.search(namespace, query=query, limit=limit)
                for item in items:
                    text = item.value.get("text", "")
                    mem_type = item.value.get("type", "memory")
                    if text and text not in "\n".join(result_parts):
                        result_parts.append(f"\n**[{mem_type}]** {text}")
        except Exception:
            logger.debug("InMemoryStore search failed (non-critical)", exc_info=True)

    if not result_parts:
        return "No relevant memories found."

    return "\n".join(result_parts)


@tool
def get_memory_stats() -> str:
    """Get statistics about what's stored in long-term memory.

    Use this to see an overview of stored memories, including counts
    by type (decisions, applications, conversations, etc.).
    """
    try:
        from futureproof.memory.episodic import get_episodic_store

        store = get_episodic_store()
        stats = store.stats()

        result_parts = ["Long-term memory statistics:"]
        result_parts.append(f"\nTotal memories: {stats['total_memories']}")
        result_parts.append("\nBy type:")
        for mem_type, count in stats["by_type"].items():
            if count > 0:
                result_parts.append(f"  - {mem_type}: {count}")

        return "\n".join(result_parts)

    except ImportError:
        return "Note: Long-term memory is not available (ChromaDB not installed)."
    except Exception as e:
        logger.exception("Error getting memory stats")
        return f"Could not get memory stats: {e}"


# =============================================================================
# Tool Registry
# =============================================================================


def get_research_tools() -> list:
    """Get tools for the research sub-agent.

    Includes data gathering, knowledge search, and market intelligence.
    """
    return [
        gather_github_data,
        gather_gitlab_data,
        gather_portfolio_data,
        gather_all_career_data,
        get_stored_career_data,
        search_career_knowledge,
        get_knowledge_stats,
        search_jobs,
        get_tech_trends,
        get_salary_insights,
    ]


def get_supervisor_tools() -> list:
    """Get tools for the supervisor agent.

    Includes profile management, analysis, generation, and memory.
    """
    return [
        get_user_profile,
        update_user_goal,
        update_user_skills,
        set_target_roles,
        update_user_name,
        update_current_role,
        analyze_skill_gaps,
        analyze_career_alignment,
        get_career_advice,
        generate_cv,
        generate_cv_draft,
        remember_decision,
        remember_job_application,
        recall_memories,
        get_memory_stats,
    ]
