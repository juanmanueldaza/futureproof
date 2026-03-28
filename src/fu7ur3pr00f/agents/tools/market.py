"""Market intelligence tools for the career agent."""

from langchain_core.tools import tool

from fu7ur3pr00f.agents.tools._analysis_helpers import run_market_analysis
from fu7ur3pr00f.prompts import load_prompt

from ._async import run_async


@tool
def search_jobs(
    query: str,
    location: str = "remote",
    limit: int = 50,
) -> str:
    """Search for job opportunities matching the query.

    Args:
        query: Job search query (e.g., "ML Engineer", "Python Developer")
        location: Where the user wants to work. Use the country/city the user
            mentions (e.g., "Argentina", "Spain", "Berlin"). If the user says
            "remote job from Argentina", use "Argentina" — NOT "remote".
            Only use "remote" when NO specific location is mentioned.
        limit: Maximum number of results to return

    Use this when the user asks about job opportunities or wants to see what's
        available.
    """
    from fu7ur3pr00f.gatherers.market import JobMarketGatherer

    gatherer = JobMarketGatherer()
    data = run_async(gatherer.gather(role=query, location=location, limit=limit))

    jobs = data.get("job_listings", [])
    summary = data.get("summary", {})
    errors = data.get("errors", [])

    result_parts = [f"Job search results for {query!r} in {location!r}:"]
    total = summary.get("total_jobs", 0)
    sources = summary.get("sources", [])
    result_parts.append(
        f"\nFound {total} jobs from {len(sources)} sources: {', '.join(sources)}"
    )

    if summary.get("remote_positions"):
        result_parts.append(f"Remote positions: {summary['remote_positions']}")

    if jobs:
        # Deduplicate by title+company (LinkedIn posts same job in multiple cities)
        seen: set[str] = set()
        unique_jobs: list[dict] = []
        for job in jobs:
            key = f"{job.get('title', '')}|{job.get('company', '')}".lower()
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        jobs = unique_jobs

        result_parts.append(f"\n**Top opportunities:** ({len(jobs)} found)")
        for job in jobs[:25]:
            title = job.get("title") or "Unknown"
            company = job.get("company") or "Unknown"
            loc_raw = job.get("location")
            job_loc = loc_raw if isinstance(loc_raw, str) and loc_raw else "Remote"
            salary = job.get("salary", "")
            salary_str = f" - {salary}" if salary else ""
            url = job.get("url") or job.get("job_url") or job.get("apply_url") or ""
            source = job.get("site", "")
            source_str = f" [{source}]" if source else ""
            result_parts.append(f"\n- **{title}** at {company}{source_str}")
            result_parts.append(f"  Location: {job_loc}{salary_str}")
            if url:
                result_parts.append(f"  Apply: {url}")

    if errors:
        result_parts.append(f"\nNote: Some sources had issues: {len(errors)} errors")

    return "\n".join(result_parts)


@tool
def get_tech_trends(topic: str = "") -> str:
    """Get current technology trends and hiring patterns from Hacker News.

    Args:
        topic: Optional topic to focus on (e.g., "Python", "Rust", "AI")

    Use this to understand what technologies are trending and what companies are hiring
        for.
    """
    from fu7ur3pr00f.gatherers.market import TechTrendsGatherer

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
    from fu7ur3pr00f.gatherers.market import JobMarketGatherer

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

    result_parts = [f"Salary insights for {role!r} ({location}):"]

    if jobs_with_salary:
        result_parts.append(
            f"\n**From job listings:** ({len(jobs_with_salary)} with salary)"
        )
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
        result_parts.append(
            "\nNo specific salary data found. Try broadening the search."
        )

    return "\n".join(result_parts)


@tool
def analyze_market_fit() -> str:
    """Analyze how the user's profile aligns with current market demands.

    Compares skills and experience against trending technologies and job
    requirements. Requires career data to be gathered first.

    Use this when the user asks how well they fit the current job market
    or wants to know if their skills are in demand.
    """
    return run_market_analysis(
        search_query="skills experience",
        prompt_fn=lambda tech: load_prompt("tool_market_fit").replace("{tech}", tech),
        noun="Market fit analysis",
    )


@tool
def analyze_market_skills() -> str:
    """Identify skill gaps based on current market demands.

    Shows which skills are trending and which the user should learn
    to stay competitive. Requires career data to be gathered first.

    Use this when the user asks what skills they should learn or
    how to stay competitive in the job market.
    """
    return run_market_analysis(
        search_query="skills learning",
        prompt_fn=lambda tech: load_prompt("tool_market_skills").replace(
            "{tech}", tech
        ),
        noun="Market skills analysis",
    )


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
        from fu7ur3pr00f.gatherers.market import TechTrendsGatherer

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
        from fu7ur3pr00f.gatherers.market import JobMarketGatherer

        gatherer = JobMarketGatherer()
        data = run_async(
            gatherer.gather_with_cache(refresh=True, role="Software Developer")
        )
        listings = data.get("job_listings", [])
        sources_list = data.get("summary", {}).get("sources", [])
        remote = data.get("summary", {}).get("remote_positions", 0)
        result_parts.append(
            f"\n**Job Market:** {len(listings)} listings "
            f"from {len(sources_list)} sources"
        )
        result_parts.append(f"  Remote positions: {remote}")

    if source in ("all", "content"):
        from fu7ur3pr00f.gatherers.market import ContentTrendsGatherer

        gatherer = ContentTrendsGatherer()
        data = run_async(gatherer.gather_with_cache(refresh=True, focus="all"))
        articles = data.get("devto_articles", [])
        so_trends = data.get("stackoverflow_trends", {})
        topic_pop = so_trends.get("topic_popularity", [])
        result_parts.append(f"\n**Content Trends:** {len(articles)} Dev.to articles")
        if topic_pop:
            result_parts.append(f"  Stack Overflow: {len(topic_pop)} tags tracked")

    return "\n".join(result_parts)
