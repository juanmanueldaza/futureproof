"""Data gathering tools for the career agent."""

from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def gather_github_data(username: str | None = None) -> str:
    """Gather the user's GitHub profile data including repositories and contributions.

    Args:
        username: Optional GitHub username. If not provided, uses config setting.

    Use this when you need current information about the user's GitHub activity,
    projects, or technical contributions. This fetches fresh data from GitHub.
    """
    from futureproof.services import GathererService

    service = GathererService()
    output_path = service.gather_github(username)
    return f"GitHub data gathered successfully. Saved to: {output_path}"


@tool
def gather_gitlab_data(username: str | None = None) -> str:
    """Gather the user's GitLab profile data including projects and merge requests.

    Args:
        username: Optional GitLab username. If not provided, uses config setting.

    Use this when you need information about the user's GitLab activity and projects.
    """
    from futureproof.services import GathererService

    service = GathererService()
    output_path = service.gather_gitlab(username)
    return f"GitLab data gathered successfully. Saved to: {output_path}"


@tool
def gather_portfolio_data(url: str | None = None) -> str:
    """Gather data from the user's portfolio website.

    Args:
        url: Optional portfolio URL. If not provided, uses config setting.

    Use this to collect information from the user's personal website or portfolio.
    """
    from futureproof.services import GathererService

    service = GathererService()
    output_path = service.gather_portfolio(url)
    return f"Portfolio data gathered successfully. Saved to: {output_path}"


@tool
def gather_all_career_data() -> str:
    """Gather data from all configured sources.

    Gathers from GitHub, GitLab, and Portfolio (if configured), and also
    auto-detects LinkedIn ZIP exports and CliftonStrengths PDFs in data/raw/.

    Use this to refresh all career data at once. This may take a minute.
    """
    # Human-in-the-loop: confirm before gathering from all sources
    approved = interrupt(
        {
            "question": "Gather data from all configured sources?",
            "details": (
                "This will fetch from GitHub, GitLab, Portfolio, "
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
        status = "✓" if success else "✗"
        result_parts.append(f"  {status} {source}")

    successful = sum(1 for s in results.values() if s)
    total = len(results)
    result_parts.append(f"\n{successful}/{total} sources gathered successfully.")

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
        output_path = service.gather_linkedin(Path(zip_path))
    except FileNotFoundError:
        return f"LinkedIn export not found at '{zip_path}'. Please check the path."
    return f"LinkedIn data processed successfully. Saved to: {output_path}"


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
        output_path = service.gather_assessment(dir_path)
    except FileNotFoundError:
        search_dir = input_dir or "data/raw/"
        return f"No Gallup PDF files found in '{search_dir}'."
    return f"CliftonStrengths assessment processed successfully. Saved to: {output_path}"


# Data source keys and their display labels
_DATA_SOURCES = [
    ("github_data", "GitHub"),
    ("gitlab_data", "GitLab"),
    ("portfolio_data", "Portfolio"),
    ("linkedin_data", "LinkedIn"),
    ("assessment_data", "CliftonStrengths"),
]


@tool
def get_stored_career_data() -> str:
    """Get a summary of all stored career data without fetching new data.

    Use this to see what career data is already available locally.
    """
    from futureproof.utils.data_loader import load_career_data

    data = load_career_data()

    result_parts = ["Stored career data summary:"]
    for key, label in _DATA_SOURCES:
        content = data.get(key, "")
        if content:
            lines = content.count("\n")
            result_parts.append(f"\n**{label}:** Data available ({lines} lines)")

    if len(result_parts) == 1:
        return "No career data stored yet. Use gather_all_career_data() to collect data."

    return "\n".join(result_parts)
