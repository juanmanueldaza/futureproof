"""Market intelligence tools for the career agent."""

from typing import TYPE_CHECKING
from unicodedata import normalize

from langchain_core.tools import tool

from ._async import run_async

if TYPE_CHECKING:
    from futureproof.services.analysis_service import AnalysisAction

# Common location translations (non-English → English)
# Covers Spanish, French, German, Portuguese, Italian, and native names
_LOCATION_ALIASES: dict[str, str] = {
    # Countries
    "españa": "spain",
    "espana": "spain",
    "alemania": "germany",
    "deutschland": "germany",
    "francia": "france",
    "italien": "italy",
    "italia": "italy",
    "reino unido": "united kingdom",
    "estados unidos": "united states",
    "países bajos": "netherlands",
    "paises bajos": "netherlands",
    "suiza": "switzerland",
    "schweiz": "switzerland",
    "suecia": "sweden",
    "sverige": "sweden",
    "noruega": "norway",
    "norge": "norway",
    "dinamarca": "denmark",
    "danmark": "denmark",
    "irlanda": "ireland",
    "bélgica": "belgium",
    "belgica": "belgium",
    "austria": "austria",
    "portugal": "portugal",
    "brasil": "brazil",
    "méxico": "mexico",
    "mexico": "mexico",
    "japón": "japan",
    "japon": "japan",
    "corea del sur": "south korea",
    "canadá": "canada",
    "canada": "canada",
    "argentina": "argentina",
    "colombia": "colombia",
    "chile": "chile",
    "perú": "peru",
    "peru": "peru",
    "polska": "poland",
    "polonia": "poland",
    "república checa": "czech republic",
    "republica checa": "czech republic",
    "grecia": "greece",
    "rumanía": "romania",
    "rumania": "romania",
    "hungría": "hungary",
    "hungria": "hungary",
    "finlandia": "finland",
    "suomi": "finland",
    # Cities
    "málaga": "malaga",
    "múnich": "munich",
    "munich": "munich",
    "münchen": "munich",
    "munchen": "munich",
    "milán": "milan",
    "milan": "milan",
    "milano": "milan",
    "lisboa": "lisbon",
    "londres": "london",
    "berlín": "berlin",
    "berlin": "berlin",
    "París": "paris",
    "paris": "paris",
    "bruselas": "brussels",
    "bruxelles": "brussels",
    "ámsterdam": "amsterdam",
    "amsterdam": "amsterdam",
    "copenhague": "copenhagen",
    "estocolmo": "stockholm",
    "varsovia": "warsaw",
    "warszawa": "warsaw",
    "praga": "prague",
    "praha": "prague",
    "viena": "vienna",
    "wien": "vienna",
    "ginebra": "geneva",
    "genève": "geneva",
    "geneve": "geneva",
    "zúrich": "zurich",
    "zurich": "zurich",
    "zürich": "zurich",
    "barcelona": "barcelona",
    "madrid": "madrid",
    "valencia": "valencia",
    "sevilla": "seville",
    "bilbao": "bilbao",
}


def _norm(s: object) -> str:
    """Normalize accented chars for matching (e.g. Málaga → malaga).

    Handles non-string values (e.g. NaN floats from pandas/JobSpy).
    """
    if not isinstance(s, str):
        return ""
    return normalize("NFD", s.lower()).encode("ascii", "ignore").decode()


def _translate_location(location: str) -> str:
    """Translate non-English location to English for API queries.

    Returns the English equivalent if found, otherwise returns original.
    """
    key = _norm(location)
    return _LOCATION_ALIASES.get(key, location)


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

    Use this when the user asks about job opportunities or wants to see what's available.
    """
    from futureproof.gatherers.market import JobMarketGatherer

    # Translate non-English locations for API queries (España → Spain)
    search_location = _translate_location(location)

    gatherer = JobMarketGatherer()
    data = run_async(gatherer.gather(role=query, location=search_location, limit=limit))

    jobs = data.get("job_listings", [])
    summary = data.get("summary", {})
    errors = data.get("errors", [])

    # Show the user's original location in the header
    result_parts = [f"Job search results for '{query}' in '{location}':"]
    total = summary.get("total_jobs", 0)
    sources = summary.get("sources", [])
    result_parts.append(f"\nFound {total} jobs from {len(sources)} sources: {', '.join(sources)}")

    if summary.get("remote_positions"):
        result_parts.append(f"Remote positions: {summary['remote_positions']}")

    if jobs:
        from collections import defaultdict

        # Deduplicate by title+company (LinkedIn posts same job in multiple cities)
        seen: set[str] = set()
        unique_jobs: list[dict] = []
        for job in jobs:
            key = f"{job.get('title', '')}|{job.get('company', '')}".lower()
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        jobs = unique_jobs

        # Filter by role relevance — drop jobs with no keyword overlap in title
        # (e.g. "Medical Claims Negotiator" when searching "AI Engineer")
        query_words = {w.lower() for w in query.split() if len(w) >= 2}
        # Common tech synonyms to broaden matching
        _synonyms = {
            "ai": {"ai", "ml", "machine", "learning", "data", "intelligence"},
            "engineer": {"engineer", "developer", "dev", "architect", "lead"},
            "full": {"full", "fullstack", "full-stack"},
            "stack": {"stack", "fullstack", "full-stack"},
            "frontend": {"frontend", "front-end", "front", "ui", "react", "vue"},
            "backend": {"backend", "back-end", "back", "api", "server"},
            "senior": {"senior", "sr", "staff", "principal", "lead"},
            "software": {"software", "swe"},
        }
        expanded = set(query_words)
        for w in query_words:
            if w in _synonyms:
                expanded.update(_synonyms[w])

        def _is_relevant(job: dict) -> bool:
            title = (job.get("title") or "").lower()
            title_words = set(title.replace("-", " ").split())
            return bool(expanded & title_words)

        before_filter = len(jobs)
        jobs = [j for j in jobs if _is_relevant(j)]
        if before_filter != len(jobs):
            result_parts.append(
                f"Showing {len(jobs)} relevant results (filtered {before_filter - len(jobs)} unrelated)"
            )

        # Separate location-matched vs unmatched jobs
        matched: list[dict] = []
        unmatched = jobs
        if search_location.lower() != "remote":
            # Match against both original and translated location
            loc_norms = {_norm(location), _norm(search_location)}
            matched = [
                j for j in jobs if any(ln in _norm(j.get("location") or "") for ln in loc_norms)
            ]
            unmatched = [j for j in jobs if j not in matched]

        def _fmt_job(job: dict) -> None:
            """Append formatted job lines to result_parts."""
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

        # Display matched jobs first, then round-robin unmatched
        max_display = 25
        if matched:
            result_parts.append(f"\n**Jobs in {location}:** ({len(matched)} found)")
            for job in matched[:max_display]:
                _fmt_job(job)

        remaining = max_display - min(len(matched), max_display)
        if remaining > 0 and unmatched:
            if matched:
                result_parts.append("\n**Remote/other opportunities:**")
            else:
                result_parts.append("\n**Top opportunities:**")

            # Round-robin across sources
            jobs_by_source: dict[str, list[dict]] = defaultdict(list)
            for job in unmatched:
                jobs_by_source[job.get("site", "unknown")].append(job)

            groups = list(jobs_by_source.values())
            idx = 0
            shown = 0
            while shown < remaining and groups:
                group = groups[idx % len(groups)]
                if group:
                    _fmt_job(group.pop(0))
                    shown += 1
                    idx += 1
                else:
                    groups.pop(idx % len(groups))

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
