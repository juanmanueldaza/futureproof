"""Data gathering tools for the career agent."""

import logging

from langchain_core.tools import tool
from langgraph.types import interrupt

logger = logging.getLogger(__name__)


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

    try:
        from pathlib import Path

        from futureproof.services import GathererService

        service = GathererService()
        results = service.gather_all()

        # Auto-detect LinkedIn ZIP in data/raw/
        raw_dir = Path("data/raw")
        if raw_dir.exists():
            linkedin_zips = list(raw_dir.glob("*[Ll]inked[Ii]n*.zip"))
            if linkedin_zips:
                linkedin_zip = max(linkedin_zips, key=lambda p: p.stat().st_mtime)
                try:
                    service.gather_linkedin(linkedin_zip)
                    results["linkedin"] = True
                except Exception:
                    results["linkedin"] = False
            else:
                results["linkedin"] = False

            # Auto-detect CliftonStrengths PDFs
            gallup_indicators = [
                "top_5",
                "top_10",
                "all_34",
                "action_planning",
                "leadership_insight",
                "discovery_development",
                "sf_top",
                "cliftonstrengths",
                "strengthsfinder",
                "gallup",
            ]
            gallup_pdfs = [
                p
                for p in raw_dir.glob("*.pdf")
                if any(ind in p.name.lower() for ind in gallup_indicators)
            ]
            if gallup_pdfs:
                try:
                    service.gather_assessment(raw_dir)
                    results["assessment"] = True
                except Exception:
                    results["assessment"] = False
            else:
                results["assessment"] = False

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
def gather_linkedin_data(zip_path: str) -> str:
    """Process a LinkedIn data export ZIP file.

    Args:
        zip_path: Path to the LinkedIn export ZIP file (e.g., "data/raw/LinkedIn.zip")

    Use this when the user has downloaded their LinkedIn data export and wants
    to import it. LinkedIn exports can be requested from LinkedIn Settings >
    Data Privacy > Get a copy of your data.
    """
    from pathlib import Path

    try:
        from futureproof.services import GathererService

        service = GathererService()
        output_path = service.gather_linkedin(Path(zip_path))
        return f"LinkedIn data processed successfully. Saved to: {output_path}"

    except FileNotFoundError:
        return f"LinkedIn export not found at '{zip_path}'. Please check the path."
    except Exception as e:
        logger.exception("Error processing LinkedIn data")
        return f"Error processing LinkedIn data: {e}"


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

    try:
        from futureproof.services import GathererService

        service = GathererService()
        dir_path = Path(input_dir) if input_dir else None
        output_path = service.gather_assessment(dir_path)
        return f"CliftonStrengths assessment processed successfully. Saved to: {output_path}"

    except FileNotFoundError:
        search_dir = input_dir or "data/raw/"
        return f"No Gallup PDF files found in '{search_dir}'."
    except Exception as e:
        logger.exception("Error processing assessment data")
        return f"Error processing assessment data: {e}"


@tool
def get_stored_career_data() -> str:
    """Get a summary of all stored career data without fetching new data.

    Use this to see what career data is already available locally.
    """
    try:
        from futureproof.utils.data_loader import load_career_data

        data = load_career_data()

        summary_parts = ["Stored career data summary:"]

        github_data = data.get("github_data", "")
        if github_data:
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
