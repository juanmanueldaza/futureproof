"""Market intelligence tools for the career agent."""

from typing import TYPE_CHECKING

from langchain_core.tools import tool

from ._async import run_async

if TYPE_CHECKING:
    from futureproof.services.analysis_service import AnalysisAction


def _analyze_with_market_data(action: "AnalysisAction", label: str) -> str:
    """Shared helper for market-aware analysis tools."""
    from futureproof.gatherers.market import TechTrendsGatherer
    from futureproof.services import AnalysisService

    gatherer = TechTrendsGatherer()
    market_data = run_async(gatherer.gather_with_cache())

    service = AnalysisService()
    result = service.analyze(action, market_data=market_data)

    if result.success:
        return f"{label}:\n\n{result.content}"
    return f"Could not complete {label.lower()}: {result.error}"


@tool
def search_jobs(
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
    from futureproof.gatherers.market import JobMarketGatherer

    gatherer = JobMarketGatherer()
    data = run_async(gatherer.gather(role=query, location=location, limit=limit))

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


@tool
def get_tech_trends(topic: str = "") -> str:
    """Get current technology trends and hiring patterns from Hacker News.

    Args:
        topic: Optional topic to focus on (e.g., "Python", "Rust", "AI")

    Use this to understand what technologies are trending and what companies are hiring for.
    """
    from futureproof.gatherers.market import TechTrendsGatherer

    gatherer = TechTrendsGatherer()
    data = run_async(gatherer.gather(topic=topic))

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


@tool
def get_salary_insights(role: str, location: str = "remote") -> str:
    """Get salary information for a specific role and location.

    Args:
        role: Job role to research (e.g., "Senior Python Developer")
        location: Location for salary data (e.g., "remote", "San Francisco")

    Use this when the user asks about salary expectations or compensation.
    """
    from futureproof.gatherers.market import JobMarketGatherer

    gatherer = JobMarketGatherer()
    data = run_async(
        gatherer.gather(
            role=role,
            location=location,
            include_salary=True,
            limit=10,
        )
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


@tool
def analyze_market_fit() -> str:
    """Analyze how the user's profile aligns with current market demands.

    Compares skills and experience against trending technologies and job
    requirements. Requires career data to be gathered first.

    Use this when the user asks how well they fit the current job market
    or wants to know if their skills are in demand.
    """
    return _analyze_with_market_data("analyze_market", "Market fit analysis")


@tool
def analyze_market_skills() -> str:
    """Identify skill gaps based on current market demands.

    Shows which skills are trending and which the user should learn
    to stay competitive. Requires career data to be gathered first.

    Use this when the user asks what skills they should learn or
    how to stay competitive in the job market.
    """
    return _analyze_with_market_data("analyze_skills", "Market skills analysis")


@tool
def gather_market_data(source: str = "all") -> str:
    """Gather comprehensive market intelligence from all sources.

    Args:
        source: What to gather — "all", "trends", "jobs", or "content"

    Sources:
    - trends: Hacker News tech discussions and hiring patterns
    - jobs: Job listings from multiple boards (JobSpy, RemoteOK, etc.)
    - content: Dev.to articles and Stack Overflow tag popularity

    Use this when the user wants a full market intelligence report
    or wants to refresh market data.
    """
    result_parts = [f"Market intelligence gathering (source={source}):"]

    if source in ("all", "trends"):
        from futureproof.gatherers.market import TechTrendsGatherer

        gatherer = TechTrendsGatherer()
        data = run_async(gatherer.gather_with_cache(refresh=True))
        stories = data.get("trending_stories", [])
        hiring = data.get("hiring_trends", {})
        hn_jobs = data.get("hn_job_postings", [])
        result_parts.append(f"\n**Tech Trends:** {len(stories)} trending stories")
        if hiring:
            total_jobs = hiring.get("total_job_postings", 0)
            result_parts.append(f"  Hiring threads: {total_jobs} job posts analyzed")
        if hn_jobs:
            result_parts.append(f"  HN job postings: {len(hn_jobs)} extracted")

    if source in ("all", "jobs"):
        from futureproof.gatherers.market import JobMarketGatherer

        gatherer = JobMarketGatherer()
        data = run_async(gatherer.gather_with_cache(refresh=True, role="Software Developer"))
        listings = data.get("job_listings", [])
        sources_list = data.get("summary", {}).get("sources", [])
        remote = data.get("summary", {}).get("remote_positions", 0)
        result_parts.append(
            f"\n**Job Market:** {len(listings)} listings from {len(sources_list)} sources"
        )
        result_parts.append(f"  Remote positions: {remote}")

    if source in ("all", "content"):
        from futureproof.gatherers.market import ContentTrendsGatherer

        gatherer = ContentTrendsGatherer()
        data = run_async(gatherer.gather_with_cache(refresh=True, focus="all"))
        articles = data.get("devto_articles", [])
        so_trends = data.get("stackoverflow_trends", {})
        topic_pop = so_trends.get("topic_popularity", [])
        result_parts.append(f"\n**Content Trends:** {len(articles)} Dev.to articles")
        if topic_pop:
            result_parts.append(f"  Stack Overflow: {len(topic_pop)} tags tracked")

    return "\n".join(result_parts)
