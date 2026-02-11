"""FutureProof CLI - Career Intelligence System."""

import logging
from pathlib import Path
from typing import Annotated, Any

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


def _validate_input(model_class: type, **kwargs: Any) -> None:
    """Validate input using Pydantic model, exit on validation error.

    This helper eliminates duplicate try/except validation blocks
    across CLI commands. (DRY fix)

    Args:
        model_class: Pydantic model class to use for validation
        **kwargs: Keyword arguments to pass to the model constructor

    Raises:
        typer.Exit: If validation fails (exits with code 1)
    """
    try:
        model_class(**kwargs)
    except PydanticValidationError as e:
        console.print(f"[red]Validation error: {e.errors()[0]['msg']}[/red]")
        raise typer.Exit(code=1)


def _print_panel(message: str, style: str = "blue") -> None:
    """Print a styled panel message.

    DRY helper to eliminate repeated Panel creation across CLI commands.

    Args:
        message: Message to display in the panel
        style: Panel style (default: "blue")
    """
    console.print(Panel(f"[bold]{message}[/bold]", style=style))


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
daemon_app = typer.Typer(help="Background daemon for scheduled intelligence gathering")

knowledge_app = typer.Typer(help="Knowledge base management (RAG)")

app.add_typer(gather_app, name="gather")
app.add_typer(generate_app, name="generate")
app.add_typer(analyze_app, name="analyze")
app.add_typer(advise_app, name="advise")
app.add_typer(market_app, name="market")
app.add_typer(knowledge_app, name="knowledge")
app.add_typer(daemon_app, name="daemon")


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
def gather_all(
    skip_index: Annotated[
        bool,
        typer.Option("--skip-index", help="Skip indexing after gathering"),
    ] = False,
) -> None:
    """Gather and index data from ALL sources. One command to rule them all.

    Auto-detects:
    - LinkedIn: ZIP files in data/raw/ matching *LinkedIn*.zip
    - CliftonStrengths: Gallup PDF files in data/raw/

    Also gathers from configured sources:
    - GitHub (if GITHUB_USERNAME set)
    - GitLab (if GITLAB_USERNAME set)
    - Portfolio (if PORTFOLIO_URL set)
    """
    from .mcp import MCPClientFactory
    from .services import CareerService
    from .services.knowledge_service import KnowledgeService

    _print_panel("🔥 Gathering ALL professional data...")

    service = CareerService()
    results: dict[str, tuple[bool, str | None]] = {}

    # GitHub
    console.print("\n[bold cyan]━━━ GitHub ━━━[/bold cyan]")
    if settings.github_username:
        github_method = "MCP" if MCPClientFactory.is_available("github") else "CLI"
        console.print(f"  User: {settings.github_username}")
        console.print(f"  Method: {github_method}")
        try:
            output_path = service.gather_github()
            results["GitHub"] = (True, str(output_path))
            console.print(f"  [green]✓ Saved:[/green] {output_path.name}")
        except Exception as e:
            results["GitHub"] = (False, str(e))
            console.print(f"  [red]✗ Failed: {e}[/red]")
    else:
        results["GitHub"] = (False, "Not configured")
        console.print("  [yellow]⚠ Skipped: GITHUB_USERNAME not set[/yellow]")

    # GitLab
    console.print("\n[bold cyan]━━━ GitLab ━━━[/bold cyan]")
    if settings.gitlab_username:
        gitlab_method = "MCP" if MCPClientFactory.is_available("gitlab") else "CLI (gitlab2md)"
        console.print(f"  User: {settings.gitlab_username}")
        if settings.gitlab_groups_list:
            console.print(f"  Groups: {', '.join(settings.gitlab_groups_list)}")
        console.print(f"  Method: {gitlab_method}")
        try:
            output_path = service.gather_gitlab()
            results["GitLab"] = (True, str(output_path))
            console.print(f"  [green]✓ Saved:[/green] {output_path.name}")
        except Exception as e:
            results["GitLab"] = (False, str(e))
            console.print(f"  [red]✗ Failed: {e}[/red]")
    else:
        results["GitLab"] = (False, "Not configured")
        console.print("  [yellow]⚠ Skipped: GITLAB_USERNAME not set[/yellow]")

    # Portfolio
    console.print("\n[bold cyan]━━━ Portfolio ━━━[/bold cyan]")
    if settings.portfolio_url:
        console.print(f"  URL: {settings.portfolio_url}")
        console.print("  Method: HTTP scraping")
        try:
            output_path = service.gather_portfolio()
            results["Portfolio"] = (True, str(output_path))
            console.print(f"  [green]✓ Saved:[/green] {output_path.name}")
        except Exception as e:
            results["Portfolio"] = (False, str(e))
            console.print(f"  [red]✗ Failed: {e}[/red]")
    else:
        results["Portfolio"] = (False, "Not configured")
        console.print("  [yellow]⚠ Skipped: PORTFOLIO_URL not set[/yellow]")

    # LinkedIn - auto-detect ZIP files in data/raw
    console.print("\n[bold cyan]━━━ LinkedIn ━━━[/bold cyan]")
    raw_dir = settings.data_dir / "raw"
    linkedin_zips = list(raw_dir.glob("*[Ll]inked[Ii]n*.zip"))
    if linkedin_zips:
        # Use the most recent one
        linkedin_zip = max(linkedin_zips, key=lambda p: p.stat().st_mtime)
        console.print(f"  Found: {linkedin_zip.name}")
        try:
            service.gather_linkedin(linkedin_zip)
            results["LinkedIn"] = (True, str(linkedin_zip))
            console.print("  [green]✓ Processed LinkedIn export[/green]")
        except Exception as e:
            results["LinkedIn"] = (False, str(e))
            console.print(f"  [red]✗ Failed: {e}[/red]")
    else:
        results["LinkedIn"] = (False, "No export found")
        console.print("  [yellow]⚠ Skipped: No LinkedIn ZIP in data/raw/[/yellow]")
        console.print("  [dim]   Export from LinkedIn Settings > Data Privacy > Get a copy[/dim]")

    # CliftonStrengths - auto-detect Gallup PDFs in data/raw
    console.print("\n[bold cyan]━━━ CliftonStrengths ━━━[/bold cyan]")
    gallup_pdfs = [
        p
        for p in raw_dir.glob("*.pdf")
        if any(
            indicator in p.name.lower()
            for indicator in ["top_5", "top_10", "all_34", "sf_top", "clifton", "gallup"]
        )
    ]
    if gallup_pdfs:
        console.print(f"  Found: {len(gallup_pdfs)} Gallup PDF(s)")
        for pdf in gallup_pdfs[:3]:  # Show first 3
            console.print(f"    - {pdf.name}")
        if len(gallup_pdfs) > 3:
            console.print(f"    ... and {len(gallup_pdfs) - 3} more")
        try:
            output_path = service.gather_assessment(raw_dir)
            results["CliftonStrengths"] = (True, str(output_path))
            console.print("  [green]✓ Processed CliftonStrengths assessment[/green]")
        except Exception as e:
            results["CliftonStrengths"] = (False, str(e))
            console.print(f"  [red]✗ Failed: {e}[/red]")
    else:
        results["CliftonStrengths"] = (False, "No PDFs found")
        console.print("  [yellow]⚠ Skipped: No Gallup PDFs in data/raw/[/yellow]")
        console.print("  [dim]   Download from gallup.com/cliftonstrengths[/dim]")

    # Summary
    console.print("\n[bold]━━━ Gather Summary ━━━[/bold]")
    success_count = sum(1 for ok, _ in results.values() if ok)
    total_count = len(results)
    console.print(f"  Gathered: {success_count}/{total_count} sources")

    # Index everything
    if not skip_index and success_count > 0:
        console.print("\n[bold cyan]━━━ Indexing Knowledge Base ━━━[/bold cyan]")
        try:
            knowledge_service = KnowledgeService()
            index_results = knowledge_service.index_all(verbose=True)
            total_chunks = sum(index_results.values())
            indexed_sources = sum(1 for c in index_results.values() if c > 0)
            console.print(
                f"\n  [green]✓ Indexed {total_chunks} chunks from {indexed_sources} sources[/green]"
            )
        except Exception as e:
            console.print(f"  [red]✗ Indexing failed: {e}[/red]")

    # Final summary
    console.print("\n[bold green]━━━ Done! ━━━[/bold green]")
    console.print(f"  Output: {settings.processed_dir}")
    if not skip_index:
        console.print("  Knowledge base: Ready for search")
    console.print("\n  [dim]Run 'futureproof chat' to start talking to your career data[/dim]")


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

    _validate_input(GatherLinkedInInput, zip_path=zip_path)

    _print_panel("Gathering LinkedIn data...")
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

    if username:
        _validate_input(GatherGitHubInput, username=username)

    _print_panel("Gathering GitHub data...")
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

    if username:
        _validate_input(GatherGitLabInput, username=username)

    _print_panel("Gathering GitLab data...")
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

    if url:
        _validate_input(GatherPortfolioInput, url=url)

    _print_panel("Gathering portfolio data...")
    service = CareerService()
    service.gather_portfolio(url)
    console.print("[green]Portfolio data gathered successfully![/green]")


@gather_app.command("assessment")
def gather_assessment(
    input_dir: Annotated[
        Path | None,
        typer.Option("--input", "-i", help="Directory containing Gallup PDF files"),
    ] = None,
) -> None:
    """Gather CliftonStrengths assessment data from Gallup PDFs.

    Parses CliftonStrengths PDF reports and extracts:
    - Top 5/10/34 strength rankings
    - Detailed strength insights
    - Action items and blind spots
    - Domain distribution analysis

    By default, looks for PDFs in data/raw directory.
    """
    from .services import CareerService

    _print_panel("Gathering CliftonStrengths data...")
    try:
        service = CareerService()
        output_path = service.gather_assessment(input_dir)
        console.print("[green]CliftonStrengths data gathered successfully![/green]")
        console.print(f"Output: {output_path}")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Failed to gather assessment data: {e}[/red]")
        raise typer.Exit(code=1)


# ============================================================================
# INDEX / KNOWLEDGE BASE COMMANDS
# ============================================================================


@app.command("index")
def index_command(
    source: Annotated[
        str | None,
        typer.Argument(help="Source to index (github, gitlab, linkedin, portfolio, assessment)"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed indexing progress"),
    ] = False,
) -> None:
    """Index career data into the knowledge base for semantic search.

    This creates embeddings of your career data so the agent can search
    it semantically instead of loading everything into context.

    Examples:
        futureproof index           # Index all sources
        futureproof index github    # Index only GitHub data
        futureproof index --verbose # Show detailed progress
    """
    from .memory.knowledge import KnowledgeSource
    from .services.knowledge_service import KnowledgeService

    _print_panel("Indexing career data...")

    service = KnowledgeService()

    if source:
        # Index specific source
        try:
            src = KnowledgeSource(source.lower())
        except ValueError:
            console.print(f"[red]Unknown source: {source}[/red]")
            valid = [s.value for s in KnowledgeSource]
            console.print(f"Valid sources: {', '.join(valid)}")
            raise typer.Exit(code=1)

        console.print(f"Indexing {source}...")
        count = service.index_source(src, verbose=verbose)
        console.print(f"[green]Indexed {count} chunks from {source}[/green]")
    else:
        # Index all sources
        console.print("Indexing all sources...")
        results = service.index_all(verbose=verbose)

        console.print("\n[bold]Results:[/bold]")
        total = 0
        for src, count in results.items():
            if count > 0:
                console.print(f"  [green]✓[/green] {src}: {count} chunks")
                total += count
            else:
                console.print(f"  [dim]○[/dim] {src}: no data")

        console.print(f"\n[green]Total: {total} chunks indexed[/green]")


@knowledge_app.command("stats")
def knowledge_stats() -> None:
    """Show knowledge base statistics.

    Displays how much career data is indexed and available for semantic search.
    """
    from .services.knowledge_service import KnowledgeService

    service = KnowledgeService()
    stats = service.get_stats()

    total = stats.get("total_chunks", 0)
    console.print("[bold cyan]Knowledge Base Statistics[/bold cyan]\n")

    if total == 0:
        console.print("[yellow]Knowledge base is empty.[/yellow]")
        console.print("Run 'futureproof index' to index your career data.")
        return

    console.print(f"Total chunks: [bold]{total}[/bold]\n")
    console.print("By source:")
    for source, count in stats.get("by_source", {}).items():
        if count > 0:
            console.print(f"  • {source}: {count} chunks")
        else:
            console.print(f"  • [dim]{source}: not indexed[/dim]")

    console.print(f"\nStorage: {stats.get('persist_dir', 'unknown')}")


@knowledge_app.command("search")
def knowledge_search(
    query: Annotated[
        str,
        typer.Argument(help="Search query"),
    ],
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum results"),
    ] = 5,
    source: Annotated[
        str | None,
        typer.Option("--source", "-s", help="Filter by source"),
    ] = None,
) -> None:
    """Search the knowledge base for relevant career information.

    Examples:
        futureproof knowledge search "Python projects"
        futureproof knowledge search "leadership" --source linkedin
    """
    from .services.knowledge_service import KnowledgeService

    service = KnowledgeService()
    sources = [source] if source else None
    results = service.search(query, limit=limit, sources=sources)

    if not results:
        console.print(f"[yellow]No results found for '{query}'[/yellow]")
        return

    console.print(f"[bold]Found {len(results)} results for '{query}':[/bold]\n")

    for i, result in enumerate(results, 1):
        src = result.get("source", "unknown")
        section = result.get("section", "")
        content = result.get("content", "")[:300]

        console.print(f"[bold cyan]{i}. [{src}] {section}[/bold cyan]")
        console.print(f"   {content}...")
        console.print()


@knowledge_app.command("clear")
def knowledge_clear(
    source: Annotated[
        str | None,
        typer.Argument(help="Source to clear (or all if not specified)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation"),
    ] = False,
) -> None:
    """Clear indexed data from the knowledge base.

    Examples:
        futureproof knowledge clear           # Clear all
        futureproof knowledge clear github    # Clear only GitHub data
    """
    from .memory.knowledge import KnowledgeSource, get_knowledge_store

    store = get_knowledge_store()

    if source:
        try:
            src = KnowledgeSource(source.lower())
        except ValueError:
            console.print(f"[red]Unknown source: {source}[/red]")
            raise typer.Exit(code=1)

        if not force:
            confirm = typer.confirm(f"Clear all {source} data from knowledge base?")
            if not confirm:
                raise typer.Abort()

        count = store.clear_source(src)
        console.print(f"[green]Cleared {count} chunks from {source}[/green]")
    else:
        if not force:
            confirm = typer.confirm("Clear ALL data from knowledge base?")
            if not confirm:
                raise typer.Abort()

        total = 0
        for src in KnowledgeSource:
            count = store.clear_source(src)
            total += count

        console.print(f"[green]Cleared {total} chunks from knowledge base[/green]")


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

    if not all_variants:
        _validate_input(GenerateCVInput, language=lang, format=format)

    _print_panel("Generating CV...")

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

    _print_panel(panel_msg)

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

        _validate_input(AdviseInput, target=target)

        _print_panel(f"Getting advice for target: {target}")

        service = CareerService()
        try:
            advice = service.get_advice(target)
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

    _print_panel("Fetching tech trends...")

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

    _print_panel(f"Searching jobs: {role} in {location}...")

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


def _run_market_analysis(
    analysis_type: str,
    panel_message: str,
    refresh: bool = False,
) -> None:
    """Generic market analysis runner.

    DRY helper to consolidate market_fit() and market_skills() which
    shared ~60 lines of duplicate code.

    Args:
        analysis_type: Analysis action ("analyze_market" or "analyze_skills")
        panel_message: Message to display in header panel
        refresh: Whether to bypass cache for market data
    """
    import asyncio
    from typing import cast

    from .gatherers.market import TechTrendsGatherer
    from .services import CareerService, NoDataError
    from .services.career_service import AnalysisAction

    _print_panel(panel_message)

    # Gather market trends
    console.print("[yellow]Gathering market trends...[/yellow]")
    trends_gatherer = TechTrendsGatherer()
    try:
        market_data = asyncio.run(trends_gatherer.gather_with_cache(refresh=refresh))
    except Exception as e:
        console.print(f"[red]Error fetching market data: {e}[/red]")
        return

    # Run analysis
    service = CareerService()
    try:
        result = service.analyze(cast(AnalysisAction, analysis_type), market_data=market_data)
        if result.success:
            console.print(result.content)
        else:
            console.print(f"[red]Error: {result.error}[/red]")
    except NoDataError as e:
        console.print(f"[yellow]{e}[/yellow]")
        console.print("Run 'futureproof gather all' first to collect your career data.")


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
    _run_market_analysis("analyze_market", "Analyzing market fit...", refresh)


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
    _run_market_analysis("analyze_skills", "Analyzing skill gaps...", refresh)


@market_app.command("gather")
def market_gather(
    source: Annotated[
        str,
        typer.Option("--source", "-s", help="Source to gather from (all, trends, jobs, content)"),
    ] = "all",
    refresh: Annotated[
        bool,
        typer.Option("--refresh", "-r", help="Bypass cache and fetch fresh data"),
    ] = False,
) -> None:
    """Gather market intelligence data from all sources.

    Collects tech trends, job listings, content trends, and hiring patterns.
    Data is cached based on source-specific TTLs.

    Sources:
    - trends: Hacker News tech discussions
    - jobs: JobSpy, RemoteOK, Himalayas, Jobicy, WeWorkRemotely, Remotive (180+ job listings)
    - content: Dev.to articles, Stack Overflow tag popularity
    """
    import asyncio

    from .gatherers.market import ContentTrendsGatherer, JobMarketGatherer, TechTrendsGatherer

    _print_panel("Gathering market intelligence...")

    async def gather_all() -> None:
        from .mcp import MCPClientFactory

        if source in ("all", "trends"):
            console.print("\n[bold cyan]━━━ Tech Trends (Hacker News) ━━━[/bold cyan]")
            try:
                trends = TechTrendsGatherer()
                console.print("  [dim]Connecting to HN Algolia API...[/dim]")
                data = await trends.gather_with_cache(refresh=refresh)
                stories = data.get("trending_stories", [])
                hiring = data.get("hiring_trends", {})
                errors = data.get("errors", [])

                console.print(f"  [green]✓[/green] Fetched {len(stories)} front page stories")
                if hiring:
                    total_jobs = hiring.get("total_job_postings", 0)
                    threads = hiring.get("threads_analyzed", 0)
                    msg = f"Analyzed {threads} 'Who is Hiring?' threads ({total_jobs} posts)"
                    console.print(f"  [green]✓[/green] {msg}")

                # HN structured job postings
                hn_jobs = data.get("hn_job_postings", [])
                if hn_jobs:
                    with_salary = sum(1 for j in hn_jobs if j.get("salary_min"))
                    remote = sum(1 for j in hn_jobs if j.get("remote"))
                    msg = f"Extracted {len(hn_jobs)} job postings"
                    msg += f" ({with_salary} with salary, {remote} remote)"
                    console.print(f"  [green]✓[/green] {msg}")

                if errors:
                    for err in errors:
                        console.print(f"  [yellow]⚠[/yellow] {err}")
            except Exception as e:
                console.print(f"  [red]✗ Failed: {e}[/red]")

        if source in ("all", "jobs"):
            console.print("\n[bold cyan]━━━ Job Market Intelligence ━━━[/bold cyan]")
            try:
                jobs = JobMarketGatherer()
                data = await jobs.gather_with_cache(refresh=refresh, role="Software Developer")
                listings = data.get("job_listings", [])
                sources = data.get("summary", {}).get("sources", [])
                remote_count = data.get("summary", {}).get("remote_positions", 0)
                errors = data.get("errors", [])

                # Count jobs per source
                source_counts: dict[str, int] = {}
                for job in listings:
                    src = job.get("site", "unknown")
                    source_counts[src] = source_counts.get(src, 0) + 1

                for src, count in source_counts.items():
                    console.print(f"  [green]✓[/green] {src.capitalize()}: {count} listings")

                # Summary stats
                total_msg = f"{len(listings)} job listings from {len(sources)} sources"
                console.print(f"  [bold]Total:[/bold] {total_msg}")
                console.print(f"  [bold]Remote:[/bold] {remote_count} remote-friendly positions")

                # Salary coverage stats
                with_salary = sum(
                    1
                    for j in listings
                    if (j.get("salary_min") and j.get("salary_min") not in [0, "nan"])
                    or (j.get("salary_max") and j.get("salary_max") not in [0, "nan"])
                    or j.get("salary")
                )
                if listings:
                    pct = with_salary * 100 // len(listings)
                    console.print(
                        f"  [bold]Salary data:[/bold] {with_salary}/{len(listings)} ({pct}%)"
                    )

                # Salary info from Tavily
                if data.get("salary_data"):
                    console.print("  [green]✓[/green] Salary benchmarks from Tavily search")
                if data.get("salary_summary"):
                    console.print(f"  [dim]Summary: {data['salary_summary'][:100]}...[/dim]")

                # Show any errors
                if errors:
                    for err in errors:
                        console.print(f"  [yellow]⚠[/yellow] {err}")
            except Exception as e:
                console.print(f"  [red]✗ Failed: {e}[/red]")

        if source in ("all", "content"):
            console.print(
                "\n[bold cyan]━━━ Content Trends (Dev.to + Stack Overflow) ━━━[/bold cyan]"
            )
            try:
                content = ContentTrendsGatherer()
                data = await content.gather_with_cache(refresh=refresh, focus="all")
                articles = data.get("devto_articles", [])
                so_trends = data.get("stackoverflow_trends", {})
                topic_pop = so_trends.get("topic_popularity", [])
                errors = data.get("errors", [])

                # Dev.to stats
                total_reactions = sum(a.get("reactions_count", 0) for a in articles)
                total_comments = sum(a.get("comments_count", 0) for a in articles)
                console.print(f"  [green]✓[/green] Dev.to: {len(articles)} trending articles")
                console.print(
                    f"      [dim]{total_reactions} reactions, {total_comments} comments[/dim]"
                )

                # Stack Overflow stats
                if topic_pop:
                    console.print(
                        f"  [green]✓[/green] Stack Overflow: {len(topic_pop)} tags tracked"
                    )
                    top_tags = topic_pop[:3]
                    for tag in top_tags:
                        tag_name = tag.get("tag")
                        q_count = tag.get("question_count", 0)
                        console.print(f"      [dim]{tag_name}: {q_count:,} questions[/dim]")

                # Errors
                if errors:
                    for err in errors:
                        console.print(f"  [yellow]⚠[/yellow] {err}")
            except Exception as e:
                console.print(f"  [red]✗ Failed: {e}[/red]")

        # Show available sources summary
        available = MCPClientFactory.get_available_market_sources()
        console.print(f"\n[bold]Active sources ({len(available)}):[/bold] {', '.join(available)}")

    asyncio.run(gather_all())

    console.print("\n[green]Market data gathering complete![/green]")
    console.print(f"Cache location: {settings.market_cache_dir}")


# ============================================================================
# CHAT COMMANDS - Conversational interface
# ============================================================================


@app.command("chat")
def chat_command(
    thread: Annotated[
        str,
        typer.Option("--thread", "-t", help="Conversation thread ID for persistence"),
    ] = "main",
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show tool usage and agent reasoning"),
    ] = False,
) -> None:
    """Start an interactive chat session with the career intelligence agent.

    This is the primary way to interact with FutureProof. The agent can:
    - Analyze your skills and identify gaps
    - Search for relevant job opportunities
    - Generate tailored CVs and cover letters
    - Provide strategic career advice
    - Remember your goals and preferences

    Your conversation is automatically saved and persists across sessions.

    Use --verbose to see which tools the agent is using.
    """
    from .chat.client import run_chat

    try:
        run_chat(thread_id=thread, verbose=verbose)
    except KeyboardInterrupt:
        console.print("\n[dim]Chat ended.[/dim]")
    except Exception as e:
        console.print(f"[red]Chat error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("ask")
def ask_command(
    question: Annotated[
        str,
        typer.Argument(help="Question to ask the career agent"),
    ],
    thread: Annotated[
        str,
        typer.Option("--thread", "-t", help="Conversation thread ID"),
    ] = "main",
) -> None:
    """Ask a single question to the career agent.

    This is for quick one-off queries without entering the full chat interface.
    The response still maintains context from previous conversations in the thread.

    Examples:
        futureproof ask "What are my top skills?"
        futureproof ask "Analyze my gaps for ML Engineer role"
    """
    from .chat.client import ask

    try:
        ask(question, thread_id=thread)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("memory")
def memory_command(
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Clear all conversation history"),
    ] = False,
    threads: Annotated[
        bool,
        typer.Option("--threads", help="List all conversation threads"),
    ] = False,
) -> None:
    """Manage conversation memory and history.

    View memory stats, list conversation threads, or clear history.
    """
    from .memory.checkpointer import clear_thread_history, get_data_dir, list_threads
    from .memory.profile import load_profile

    if clear:
        for thread_id in list_threads():
            clear_thread_history(thread_id)
        console.print("[green]All conversation history cleared.[/green]")
        return

    if threads:
        thread_list = list_threads()
        if thread_list:
            console.print("[bold]Conversation threads:[/bold]")
            for t in thread_list:
                console.print(f"  • {t}")
        else:
            console.print("[dim]No conversation threads found.[/dim]")
        return

    # Show memory stats
    data_dir = get_data_dir()
    profile = load_profile()
    thread_list = list_threads()

    console.print("[bold cyan]Memory Status[/bold cyan]\n")
    console.print(f"Data directory: {data_dir}")
    console.print(f"Conversation threads: {len(thread_list)}")
    console.print(f"Profile configured: {'Yes' if profile.name else 'No'}")
    if profile.goals:
        console.print(f"Career goals: {len(profile.goals)}")


# ============================================================================
# DAEMON COMMANDS - Background intelligence gathering
# ============================================================================


@daemon_app.command("start")
def daemon_start(
    foreground: Annotated[
        bool,
        typer.Option("--foreground", "-f", help="Run in foreground (don't daemonize)"),
    ] = False,
) -> None:
    """Start the background daemon for scheduled intelligence gathering.

    The daemon runs continuously and performs:
    - Daily job market scans (6 AM)
    - Weekly tech trends analysis (Monday 7 AM)
    - Periodic career data refresh (every 3 days)

    Discoveries are queued as insights and shown when you start a chat session.
    """
    from .daemon.server import get_daemon_status, run_daemon

    # Check if already running
    status = get_daemon_status()
    if status.status.value == "running":
        console.print(f"[yellow]Daemon already running (PID {status.pid})[/yellow]")
        return

    if foreground:
        console.print("[bold cyan]Starting daemon in foreground...[/bold cyan]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        try:
            run_daemon(foreground=True)
        except KeyboardInterrupt:
            console.print("\n[dim]Daemon stopped.[/dim]")
    else:
        console.print("[bold cyan]Starting daemon...[/bold cyan]")
        run_daemon(foreground=False)
        # Give it a moment to start
        import time

        time.sleep(1)
        status = get_daemon_status()
        if status.status.value == "running":
            console.print(f"[green]Daemon started (PID {status.pid})[/green]")
            console.print(f"Logs: {status.pid}")
        else:
            console.print("[red]Failed to start daemon. Check logs.[/red]")


@daemon_app.command("stop")
def daemon_stop() -> None:
    """Stop the background daemon."""
    from .daemon.server import get_daemon_status, stop_daemon

    status = get_daemon_status()
    if status.status.value != "running":
        console.print("[yellow]Daemon is not running.[/yellow]")
        return

    console.print(f"[bold cyan]Stopping daemon (PID {status.pid})...[/bold cyan]")
    if stop_daemon():
        console.print("[green]Daemon stopped.[/green]")
    else:
        console.print("[red]Failed to stop daemon.[/red]")


@daemon_app.command("status")
def daemon_status() -> None:
    """Show daemon status and pending insights."""
    from .daemon.server import get_daemon_status

    status = get_daemon_status()

    console.print("[bold cyan]Daemon Status[/bold cyan]\n")

    if status.status.value == "running":
        console.print("Status: [green]Running[/green]")
        console.print(f"PID: {status.pid}")
        if status.uptime_seconds:
            hours = int(status.uptime_seconds // 3600)
            mins = int((status.uptime_seconds % 3600) // 60)
            console.print(f"Uptime: {hours}h {mins}m")
    else:
        console.print("Status: [yellow]Stopped[/yellow]")

    console.print(f"\nPending insights: {status.pending_insights}")
    console.print(f"Scheduled jobs: {status.jobs_registered}")

    if status.pending_insights > 0:
        console.print("\n[dim]Start a chat session to view insights.[/dim]")


@daemon_app.command("insights")
def daemon_insights(
    all_insights: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show all insights including read ones"),
    ] = False,
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Mark all insights as read"),
    ] = False,
) -> None:
    """View or manage queued insights from background jobs."""
    from .daemon.insights import InsightsQueue

    queue = InsightsQueue()

    if clear:
        count = queue.mark_all_read()
        console.print(f"[green]Marked {count} insights as read.[/green]")
        return

    insights = queue.get_all(include_read=all_insights)

    if not insights:
        console.print("[dim]No pending insights.[/dim]")
        return

    console.print(f"[bold cyan]Insights ({len(insights)})[/bold cyan]\n")

    for insight in insights:
        # Priority badge
        priority_colors = {"high": "red", "medium": "yellow", "low": "dim"}
        color = priority_colors.get(insight.priority.value, "white")

        # Read indicator
        read_indicator = "[dim](read)[/dim] " if insight.read else ""

        priority_tag = f"[{color}][{insight.priority.value.upper()}][/{color}]"
        title_tag = f"[bold]{insight.title}[/bold]"
        console.print(f"{priority_tag} {read_indicator}{title_tag}")
        console.print(f"  {insight.content}")
        console.print(
            f"  [dim]{insight.category} • {insight.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]"
        )
        console.print()


@daemon_app.command("run")
def daemon_run_job(
    job: Annotated[
        str,
        typer.Argument(help="Job to run: job-scan, trends, or refresh"),
    ],
) -> None:
    """Run a specific job immediately (for testing or manual refresh).

    Available jobs:
    - job-scan: Scan job market for matching positions
    - trends: Analyze tech trends from Hacker News
    - refresh: Refresh career data from all sources
    """
    import asyncio

    from .daemon.scheduler import DaemonScheduler

    job_map = {
        "job-scan": "daily-job-scan",
        "trends": "weekly-trends",
        "refresh": "career-refresh",
    }

    if job not in job_map:
        console.print(f"[red]Unknown job: {job}[/red]")
        console.print(f"Available: {', '.join(job_map.keys())}")
        raise typer.Exit(code=1)

    job_id = job_map[job]
    console.print(f"[bold cyan]Running job: {job_id}...[/bold cyan]")

    scheduler = DaemonScheduler()
    result = asyncio.run(scheduler.run_job_now(job_id))

    if "error" in result:
        console.print(f"[red]Job failed: {result['error']}[/red]")
    else:
        console.print("[green]Job completed successfully.[/green]")

        # Show any new insights
        from .daemon.insights import InsightsQueue

        queue = InsightsQueue()
        new_insights = queue.get_unread(limit=3)
        if new_insights:
            console.print(f"\n[bold]New insights ({len(new_insights)}):[/bold]")
            for insight in new_insights:
                console.print(f"  • {insight.title}")


if __name__ == "__main__":
    app()
