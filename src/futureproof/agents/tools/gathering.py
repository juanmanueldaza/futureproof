"""Data gathering tools for the career agent."""

from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def gather_portfolio_data(url: str | None = None) -> str:
    """Gather data from the user's portfolio website.

    Args:
        url: Optional portfolio URL. If not provided, uses config setting.

    Use this to collect information from the user's personal website or portfolio.
    Data is indexed directly to the knowledge base for semantic search.
    """
    from futureproof.services import GathererService

    service = GathererService()
    service.gather_portfolio(url)
    return "Portfolio data gathered and indexed to knowledge base."


@tool
def gather_all_career_data() -> str:
    """Gather data from all configured sources.

    Gathers from Portfolio (if configured), and also auto-detects
    LinkedIn ZIP exports and CliftonStrengths PDFs in data/raw/.

    Use this to refresh all career data at once. This may take a minute.
    """
    # Human-in-the-loop: confirm before gathering from all sources
    approved = interrupt(
        {
            "question": "Gather data from all configured sources?",
            "details": (
                "This will fetch from Portfolio, "
                "and auto-detect LinkedIn exports and CliftonStrengths PDFs "
                "in data/raw/. May take a minute."
            ),
        }
    )
    if not approved:
        return "Data gathering cancelled."

    from futureproof.services import GathererService

    service = GathererService()
    results = service.gather_all()

    result_parts = ["Career data gathering complete:"]
    for source, success in results.items():
        status = "+" if success else "-"
        result_parts.append(f"  {status} {source}")

    successful = sum(1 for s in results.values() if s)
    total = len(results)
    result_parts.append(f"\n{successful}/{total} sources gathered and indexed.")

    return "\n".join(result_parts)


@tool
def gather_linkedin_data(zip_path: str) -> str:
    """Process a LinkedIn data export ZIP file.

    Args:
        zip_path: Path to the LinkedIn export ZIP file (e.g., "data/raw/LinkedIn.zip")

    Use this when the user has downloaded their LinkedIn data export and wants
    to import it. LinkedIn exports can be requested from LinkedIn Settings >
    Data Privacy > Get a copy of your data.
    """
    from pathlib import Path

    from futureproof.services import GathererService

    service = GathererService()
    try:
        service.gather_linkedin(Path(zip_path))
    except FileNotFoundError:
        return f"LinkedIn export not found at '{zip_path}'. Please check the path."
    return "LinkedIn data processed and indexed to knowledge base."


@tool
def gather_assessment_data(input_dir: str = "") -> str:
    """Process CliftonStrengths assessment PDFs from Gallup.

    Args:
        input_dir: Directory containing Gallup PDF files. Defaults to data/raw/.

    Use this when the user has Gallup CliftonStrengths PDF reports and wants
    to import their strengths data. Looks for PDF files with names containing
    keywords like "cliftonstrengths", "gallup", "top_5", etc.
    """
    from pathlib import Path

    from futureproof.services import GathererService

    service = GathererService()
    dir_path = Path(input_dir) if input_dir else None
    try:
        service.gather_assessment(dir_path)
    except FileNotFoundError:
        search_dir = input_dir or "data/raw/"
        return f"No Gallup PDF files found in '{search_dir}'."
    return "CliftonStrengths assessment processed and indexed to knowledge base."


@tool
def get_stored_career_data() -> str:
    """Get a summary of all indexed career data in the knowledge base.

    Use this to see what career data is available for search and analysis.
    """
    from futureproof.services.knowledge_service import KnowledgeService

    service = KnowledgeService()
    stats = service.get_stats()

    total = stats.get("total_chunks", 0)
    if total == 0:
        return "No career data indexed yet. Use gather_all_career_data() to collect data."

    result_parts = ["Indexed career data summary:"]
    for source, count in stats.get("by_source", {}).items():
        if count > 0:
            result_parts.append(f"\n**{source}:** {count} chunks indexed")

    result_parts.append(f"\nTotal: {total} chunks in knowledge base.")
    return "\n".join(result_parts)
