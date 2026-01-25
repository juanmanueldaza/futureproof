"""FutureProof CLI - Career Intelligence System."""

import logging
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError as PydanticValidationError
from rich.panel import Panel

from . import __version__
from .config import settings
from .utils.console import console
from .validation.models import (
    AdviseInput,
    GatherGitHubInput,
    GatherGitLabInput,
    GatherLinkedInInput,
    GatherPortfolioInput,
    GenerateCVInput,
)

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="futureproof",
    help="Career Intelligence System - gather data, generate CVs, analyze alignment",
    no_args_is_help=True,
)

# Sub-commands
gather_app = typer.Typer(help="Gather professional data from various sources")
generate_app = typer.Typer(help="Generate CVs and reports")
analyze_app = typer.Typer(help="Analyze career data and alignment")
advise_app = typer.Typer(help="Get strategic career advice")
market_app = typer.Typer(help="Market intelligence and trends")

app.add_typer(gather_app, name="gather")
app.add_typer(generate_app, name="generate")
app.add_typer(analyze_app, name="analyze")
app.add_typer(advise_app, name="advise")
app.add_typer(market_app, name="market")


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold blue]FutureProof[/bold blue] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """FutureProof - Know thyself through your data."""
    settings.ensure_directories()


# ============================================================================
# GATHER COMMANDS
# ============================================================================


@gather_app.command("all")
def gather_all() -> None:
    """Gather data from all configured sources."""
    from .services import CareerService

    console.print(Panel("[bold]Gathering all professional data...[/bold]", style="blue"))

    service = CareerService()

    console.print("\n[yellow]GitHub[/yellow]")
    try:
        service.gather_github()
        console.print("  [green]Success[/green]")
    except Exception as e:
        console.print(f"  [red]Failed: {e}[/red]")

    console.print("\n[yellow]GitLab[/yellow]")
    try:
        service.gather_gitlab()
        console.print("  [green]Success[/green]")
    except Exception as e:
        console.print(f"  [red]Failed: {e}[/red]")

    console.print("\n[yellow]Portfolio[/yellow]")
    try:
        service.gather_portfolio()
        console.print("  [green]Success[/green]")
    except Exception as e:
        console.print(f"  [red]Failed: {e}[/red]")

    console.print("\n[green]Data gathering complete![/green]")
    console.print(f"Data saved to: {settings.processed_dir}")


@gather_app.command("linkedin")
def gather_linkedin(
    zip_path: Annotated[Path, typer.Argument(help="Path to LinkedIn data export ZIP file")],
    output_dir: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
) -> None:
    """Gather data from LinkedIn export ZIP file."""
    from .services import CareerService

    # Validate input
    try:
        GatherLinkedInInput(zip_path=zip_path)
    except PydanticValidationError as e:
        console.print(f"[red]Validation error: {e.errors()[0]['msg']}[/red]")
        raise typer.Exit(code=1)

    console.print(Panel("[bold]Gathering LinkedIn data...[/bold]", style="blue"))
    service = CareerService()
    service.gather_linkedin(zip_path, output_dir)
    console.print("[green]LinkedIn data gathered successfully![/green]")


@gather_app.command("github")
def gather_github(
    username: Annotated[
        str | None,
        typer.Option("--username", "-u", help="GitHub username"),
    ] = None,
) -> None:
    """Gather data from GitHub profile."""
    from .services import CareerService

    # Validate input if provided
    if username:
        try:
            GatherGitHubInput(username=username)
        except PydanticValidationError as e:
            console.print(f"[red]Validation error: {e.errors()[0]['msg']}[/red]")
            raise typer.Exit(code=1)

    console.print(Panel("[bold]Gathering GitHub data...[/bold]", style="blue"))
    service = CareerService()
    service.gather_github(username)
    console.print("[green]GitHub data gathered successfully![/green]")


@gather_app.command("gitlab")
def gather_gitlab(
    username: Annotated[
        str | None,
        typer.Option("--username", "-u", help="GitLab username"),
    ] = None,
) -> None:
    """Gather data from GitLab profile."""
    from .services import CareerService

    # Validate input if provided
    if username:
        try:
            GatherGitLabInput(username=username)
        except PydanticValidationError as e:
            console.print(f"[red]Validation error: {e.errors()[0]['msg']}[/red]")
            raise typer.Exit(code=1)

    console.print(Panel("[bold]Gathering GitLab data...[/bold]", style="blue"))
    service = CareerService()
    service.gather_gitlab(username)
    console.print("[green]GitLab data gathered successfully![/green]")


@gather_app.command("portfolio")
def gather_portfolio(
    url: Annotated[
        str | None,
        typer.Option("--url", help="Portfolio URL to scrape"),
    ] = None,
) -> None:
    """Gather data from personal portfolio website."""
    from .services import CareerService

    # Validate input if provided
    if url:
        try:
            GatherPortfolioInput(url=url)  # type: ignore[arg-type]
        except PydanticValidationError as e:
            console.print(f"[red]Validation error: {e.errors()[0]['msg']}[/red]")
            raise typer.Exit(code=1)

    console.print(Panel("[bold]Gathering portfolio data...[/bold]", style="blue"))
    service = CareerService()
    service.gather_portfolio(url)
    console.print("[green]Portfolio data gathered successfully![/green]")


# ============================================================================
# GENERATE COMMANDS
# ============================================================================


@generate_app.command("cv")
def generate_cv(
    lang: Annotated[
        str,
        typer.Option("--lang", "-l", help="Language (en or es)"),
    ] = "en",
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="CV format (ats or creative)"),
    ] = "ats",
    all_variants: Annotated[
        bool,
        typer.Option("--all", help="Generate all language and format combinations"),
    ] = False,
) -> None:
    """Generate CV in specified language and format."""
    from .services import CareerService

    # Validate input
    if not all_variants:
        try:
            GenerateCVInput(language=lang, format=format)  # type: ignore[arg-type]
        except PydanticValidationError as e:
            console.print(f"[red]Validation error: {e.errors()[0]['msg']}[/red]")
            raise typer.Exit(code=1)

    console.print(Panel("[bold]Generating CV...[/bold]", style="blue"))

    service = CareerService()

    if all_variants:
        paths = service.generate_all_cvs()
        console.print(f"\n[green]Generated {len(paths)} CV variant(s)![/green]")
    else:
        service.generate_cv(
            language=lang,  # type: ignore[arg-type]
            format=format,  # type: ignore[arg-type]
        )
        console.print("\n[green]CV generated successfully![/green]")

    console.print(f"Output saved to: {settings.output_dir}")


# ============================================================================
# ANALYZE COMMANDS - Using service layer (DRY fix)
# ============================================================================


def _run_analysis(action: str, panel_msg: str) -> None:
    """Generic analysis runner - eliminates code duplication."""
    from .services import CareerService, NoDataError

    console.print(Panel(f"[bold]{panel_msg}[/bold]", style="blue"))

    service = CareerService()
    try:
        result = service.analyze(action)  # type: ignore[arg-type]
        if result.success:
            console.print(result.content)
        else:
            console.print(f"[red]Error: {result.error}[/red]")
    except NoDataError as e:
        console.print(f"[yellow]{e}[/yellow]")


@analyze_app.command("full")
def analyze_full() -> None:
    """Run full career analysis."""
    _run_analysis("analyze_full", "Running full career analysis...")


@analyze_app.command("goals")
def analyze_goals() -> None:
    """Extract and display stated career goals."""
    _run_analysis("analyze_goals", "Extracting career goals...")


@analyze_app.command("reality")
def analyze_reality() -> None:
    """Analyze actual activities and output."""
    _run_analysis("analyze_reality", "Analyzing actual activities...")


@analyze_app.command("gaps")
def analyze_gaps() -> None:
    """Show gaps between goals and reality."""
    _run_analysis("analyze_gaps", "Identifying gaps...")


# ============================================================================
# ADVISE COMMANDS
# ============================================================================


@advise_app.callback(invoke_without_command=True)
def advise_main(
    target: Annotated[
        str | None,
        typer.Option("--target", "-t", help="Target role or goal"),
    ] = None,
) -> None:
    """Get strategic career advice."""
    if target:
        from .services import AnalysisError, CareerService

        # Validate input
        try:
            validated = AdviseInput(target=target)
        except PydanticValidationError as e:
            console.print(f"[red]Validation error: {e.errors()[0]['msg']}[/red]")
            raise typer.Exit(code=1)

        console.print(
            Panel(f"[bold]Getting advice for target: {validated.target}[/bold]", style="blue")
        )

        service = CareerService()
        try:
            advice = service.get_advice(validated.target)
            console.print(advice)
        except AnalysisError:
            logger.exception("Advice generation failed")
            console.print("[red]Failed to generate advice. Check logs for details.[/red]")
    else:
        console.print("[yellow]Use --target to specify your career goal[/yellow]")
        console.print("Example: futureproof advise --target 'AI Engineer in Europe'")


# ============================================================================
# MARKET COMMANDS - Market intelligence and trends
# ============================================================================


@market_app.command("trends")
def market_trends(
    topic: Annotated[
        str | None,
        typer.Option("--topic", "-t", help="Technology topic to focus on (e.g., Python, Rust, AI)"),
    ] = None,
    refresh: Annotated[
        bool,
        typer.Option("--refresh", "-r", help="Bypass cache and fetch fresh data"),
    ] = False,
) -> None:
    """Get current technology trends from Hacker News.

    Shows trending discussions and hiring patterns in the tech industry.
    """
    import asyncio

    from .gatherers.market import TechTrendsGatherer

    console.print(Panel("[bold]Fetching tech trends...[/bold]", style="blue"))

    gatherer = TechTrendsGatherer()

    try:
        data = asyncio.run(gatherer.gather_with_cache(refresh=refresh, topic=topic or ""))
        markdown = gatherer.to_markdown(data)
        console.print(markdown)

        if not refresh:
            console.print("\n[dim]Using cached data. Use --refresh to fetch fresh data.[/dim]")
    except Exception as e:
        logger.exception("Error fetching trends")
        console.print(f"[red]Error: {e}[/red]")


@market_app.command("jobs")
def market_jobs(
    role: Annotated[
        str,
        typer.Option("--role", "-r", help="Job role to search for"),
    ] = "Software Developer",
    location: Annotated[
        str,
        typer.Option("--location", "-l", help="Location (e.g., Berlin, Remote)"),
    ] = "Remote",
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Bypass cache and fetch fresh data"),
    ] = False,
    include_salary: Annotated[
        bool,
        typer.Option("--salary", "-s", help="Include salary data search"),
    ] = True,
) -> None:
    """Search job market data for a specific role and location.

    Aggregates listings from LinkedIn, Indeed, Glassdoor, and ZipRecruiter.
    """
    import asyncio

    from .gatherers.market import JobMarketGatherer

    console.print(Panel(f"[bold]Searching jobs: {role} in {location}...[/bold]", style="blue"))

    gatherer = JobMarketGatherer()

    try:
        data = asyncio.run(
            gatherer.gather_with_cache(
                refresh=refresh,
                role=role,
                location=location,
                include_salary=include_salary,
            )
        )
        markdown = gatherer.to_markdown(data)
        console.print(markdown)

        if not refresh:
            console.print("\n[dim]Using cached data. Use --refresh to fetch fresh data.[/dim]")
    except Exception as e:
        logger.exception("Error searching jobs")
        console.print(f"[red]Error: {e}[/red]")


@market_app.command("fit")
def market_fit(
    refresh: Annotated[
        bool,
        typer.Option("--refresh", "-r", help="Refresh market data before analysis"),
    ] = False,
) -> None:
    """Analyze how your profile aligns with current market demands.

    Compares your skills and experience against trending technologies
    and job requirements.
    """
    import asyncio

    from .gatherers.market import TechTrendsGatherer
    from .services import CareerService, NoDataError

    console.print(Panel("[bold]Analyzing market fit...[/bold]", style="blue"))

    # First gather market trends
    console.print("[yellow]Gathering market trends...[/yellow]")
    trends_gatherer = TechTrendsGatherer()
    try:
        market_data = asyncio.run(trends_gatherer.gather_with_cache(refresh=refresh))
    except Exception as e:
        console.print(f"[red]Error fetching market data: {e}[/red]")
        return

    # Then run market fit analysis
    service = CareerService()
    try:
        result = service.analyze("analyze_market", market_data=market_data)
        if result.success:
            console.print(result.content)
        else:
            console.print(f"[red]Error: {result.error}[/red]")
    except NoDataError as e:
        console.print(f"[yellow]{e}[/yellow]")
        console.print("Run 'futureproof gather all' first to collect your career data.")


@market_app.command("skills")
def market_skills(
    refresh: Annotated[
        bool,
        typer.Option("--refresh", "-r", help="Refresh market data before analysis"),
    ] = False,
) -> None:
    """Identify skill gaps based on current market demands.

    Shows which skills are trending and which ones you should learn
    to stay competitive.
    """
    import asyncio

    from .gatherers.market import TechTrendsGatherer
    from .services import CareerService, NoDataError

    console.print(Panel("[bold]Analyzing skill gaps...[/bold]", style="blue"))

    # Gather market trends
    console.print("[yellow]Gathering market trends...[/yellow]")
    trends_gatherer = TechTrendsGatherer()
    try:
        market_data = asyncio.run(trends_gatherer.gather_with_cache(refresh=refresh))
    except Exception as e:
        console.print(f"[red]Error fetching market data: {e}[/red]")
        return

    # Run skill gap analysis
    service = CareerService()
    try:
        result = service.analyze("analyze_skills", market_data=market_data)
        if result.success:
            console.print(result.content)
        else:
            console.print(f"[red]Error: {result.error}[/red]")
    except NoDataError as e:
        console.print(f"[yellow]{e}[/yellow]")
        console.print("Run 'futureproof gather all' first to collect your career data.")


@market_app.command("gather")
def market_gather(
    source: Annotated[
        str,
        typer.Option("--source", "-s", help="Source to gather from (all, trends, jobs)"),
    ] = "all",
    refresh: Annotated[
        bool,
        typer.Option("--refresh", "-r", help="Bypass cache and fetch fresh data"),
    ] = False,
) -> None:
    """Gather market intelligence data from all sources.

    Collects tech trends, job listings, and hiring patterns.
    Data is cached based on source-specific TTLs.
    """
    import asyncio

    from .gatherers.market import JobMarketGatherer, TechTrendsGatherer

    console.print(Panel("[bold]Gathering market intelligence...[/bold]", style="blue"))

    async def gather_all() -> None:
        if source in ("all", "trends"):
            console.print("\n[yellow]Tech Trends (Hacker News)...[/yellow]")
            try:
                trends = TechTrendsGatherer()
                data = await trends.gather_with_cache(refresh=refresh)
                console.print(
                    f"  [green]Success[/green] - {len(data.get('trending_stories', []))} stories"
                )
            except Exception as e:
                console.print(f"  [red]Failed: {e}[/red]")

        if source in ("all", "jobs"):
            console.print("\n[yellow]Job Market (JobSpy)...[/yellow]")
            try:
                jobs = JobMarketGatherer()
                data = await jobs.gather_with_cache(refresh=refresh, role="Software Developer")
                console.print(
                    f"  [green]Success[/green] - {len(data.get('job_listings', []))} listings"
                )
            except Exception as e:
                console.print(f"  [red]Failed: {e}[/red]")

    asyncio.run(gather_all())

    console.print("\n[green]Market data gathering complete![/green]")
    console.print(f"Cache location: {settings.market_cache_dir}")


if __name__ == "__main__":
    app()
