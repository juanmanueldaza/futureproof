"""Data gathering tools for the career agent."""

import logging

from langchain_core.tools import tool
from langgraph.types import interrupt

logger = logging.getLogger(__name__)


@tool
def gather_portfolio_data(url: str | None = None) -> str:
    """Gather data from the user's portfolio website.

    Args:
        url: Optional portfolio URL. If not provided, uses config setting.

    Use this to collect information from the user's personal website or portfolio.
    Data is indexed directly to the knowledge base for semantic search.
    """
    from fu7ur3pr00f.services import GathererService

    service = GathererService()
    service.gather_portfolio(url)
    return "Portfolio data gathered and indexed to knowledge base."


def _auto_populate_profile() -> str | None:
    """Populate empty profile fields from knowledge base after gathering.

    Searches for name, role, and location from LinkedIn data and updates
    the profile. Returns a summary of what was populated, or None.
    """
    from fu7ur3pr00f.memory.profile import edit_profile, load_profile
    from fu7ur3pr00f.services.knowledge_service import KnowledgeService

    profile = load_profile()
    if profile.name and profile.current_role:
        return None  # Already populated

    service = KnowledgeService()
    updates: list[str] = []

    # Search for profile headline (contains name, role, location)
    results = service.search(
        query="headline name title location",
        limit=3,
        sources=["linkedin"],
        section="Profile",
    )
    if not results:
        # Fallback: broader search
        results = service.search(
            query="name role title company",
            limit=3,
            sources=["linkedin"],
        )

    if not results:
        return None

    # Parse the top result for name, role, location
    content = results[0].get("content", "")
    lines = content.strip().split("\n")

    def _clean(text: str) -> str:
        """Strip markdown bold markers and whitespace."""
        return text.strip().strip("*").strip()

    name = ""
    role = ""
    location = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        # Common LinkedIn profile patterns (may have **bold** markdown)
        if "name:" in lower or "first name:" in lower:
            name = _clean(line.split(":", 1)[1])
        elif "headline:" in lower:
            role = _clean(line.split(":", 1)[1])
        elif "location:" in lower or "geo location:" in lower:
            location = _clean(line.split(":", 1)[1])

    # If structured parsing didn't work, use first non-empty line as name
    if not name and lines:
        first = _clean(lines[0])
        # Heuristic: first line is often the name if it's short and has no colons
        if first and ":" not in first and len(first) < 60:
            name = first

    def _update(p):
        if not p.name and name:
            p.name = name
            updates.append(f"name={name}")
        if not p.current_role and role:
            p.current_role = role
            updates.append(f"role={role}")
        if not p.location and location:
            p.location = location
            updates.append(f"location={location}")

    if name or role or location:
        edit_profile(_update)

    if updates:
        msg = f"Auto-populated profile: {', '.join(updates)}"
        logger.info(msg)
        return msg
    return None


@tool
def gather_all_career_data() -> str:
    """Gather data from all configured sources.

    Gathers from Portfolio (if configured), and also auto-detects
    LinkedIn ZIP exports and CliftonStrengths PDFs in ~/.fu7ur3pr00f/data/raw/.

    Use this to refresh all career data at once. This may take a minute.
    """
    # Human-in-the-loop: confirm before gathering from all sources
    approved = interrupt(
        {
            "question": "Gather data from all configured sources?",
            "details": (
                "This will fetch from Portfolio, "
                "and auto-detect LinkedIn exports and CliftonStrengths PDFs "
                "in ~/.fu7ur3pr00f/data/raw/. May take a minute."
            ),
        }
    )
    if not approved:
        return "Data gathering cancelled."

    from fu7ur3pr00f.services import GathererService

    service = GathererService()
    results = service.gather_all()

    result_parts = ["Career data gathering complete:"]
    for source, success in results.items():
        status = "+" if success else "-"
        result_parts.append(f"  {status} {source}")

    successful = sum(1 for s in results.values() if s)
    total = len(results)
    result_parts.append(f"\n{successful}/{total} sources gathered and indexed.")

    # Auto-populate profile from gathered data
    if successful > 0:
        try:
            populated = _auto_populate_profile()
            if populated:
                result_parts.append(f"\n{populated}")
        except Exception as e:
            logger.warning("Auto-populate profile failed: %s", e)

    return "\n".join(result_parts)


@tool
def gather_linkedin_data(zip_path: str) -> str:
    """Process a LinkedIn data export ZIP file.

    Args:
        zip_path: Path to the LinkedIn export ZIP file
            (e.g., "~/.fu7ur3pr00f/data/raw/LinkedIn.zip")

    Use this when the user has downloaded their LinkedIn data export and wants
    to import it. LinkedIn exports can be requested from LinkedIn Settings >
    Data Privacy > Get a copy of your data.
    """
    from pathlib import Path

    from fu7ur3pr00f.services import GathererService

    resolved = Path(zip_path).expanduser().resolve()
    if not resolved.is_relative_to(Path.home()):
        return "Access denied: path must be within your home directory."

    service = GathererService()
    try:
        service.gather_linkedin(resolved)
    except FileNotFoundError:
        return f"LinkedIn export not found at '{zip_path}'. Please check the path."
    return "LinkedIn data processed and indexed to knowledge base."


@tool
def gather_cv_data(file_path: str) -> str:
    """Import a CV or resume file (PDF or Markdown) into the knowledge base.

    Args:
        file_path: Path to the CV file (.pdf, .md, or .txt).
            Example: "~/Documents/resume.pdf"

    Use this when the user wants to import their CV or resume.
    The file is parsed into sections and indexed for semantic search.
    Existing CV data is NOT automatically cleared — use clear_career_knowledge
    with source='cv' first if re-importing an updated CV.
    """
    from pathlib import Path

    from fu7ur3pr00f.services import GathererService
    from fu7ur3pr00f.services.exceptions import NoDataError, ServiceError

    resolved = Path(file_path).expanduser().resolve()
    if not resolved.is_relative_to(Path.home()):
        return "Access denied: path must be within your home directory."
    if not resolved.is_file():
        return f"CV file not found at '{file_path}'. Please check the path."
    suffix = resolved.suffix.lower()
    if suffix not in {".pdf", ".md", ".txt"}:
        return f"Unsupported format '{suffix}'. Only .pdf, .md, and .txt are supported."

    approved = interrupt({
        "question": f"Index CV from '{resolved}'?",
        "details": (
            "This will parse and index the file into the knowledge base "
            "as source 'cv'. If you've imported a CV before, run "
            "clear_career_knowledge(source='cv') first to avoid duplicates."
        ),
    })
    if not approved:
        return "CV import cancelled."

    service = GathererService()
    try:
        sections = service.gather_cv(resolved)
    except FileNotFoundError:
        return f"CV file not found at '{file_path}'. Please check the path."
    except NoDataError as e:
        return str(e)
    except ServiceError as e:
        return str(e)
    return f"CV imported: {len(sections)} sections indexed from {resolved.name}"


@tool
def gather_assessment_data(input_dir: str = "") -> str:
    """Process CliftonStrengths assessment PDFs from Gallup.

    Args:
        input_dir: Directory containing Gallup PDF files. Defaults to ~/.fu7ur3pr00f/data/raw/.

    Use this when the user has Gallup CliftonStrengths PDF reports and wants
    to import their strengths data. Looks for PDF files with names containing
    keywords like "cliftonstrengths", "gallup", "top_5", etc.
    """
    from pathlib import Path

    from fu7ur3pr00f.services import GathererService

    dir_path: Path | None = None
    if input_dir:
        dir_path = Path(input_dir).expanduser().resolve()
        if not dir_path.is_relative_to(Path.home()):
            return "Access denied: path must be within your home directory."

    service = GathererService()
    try:
        service.gather_assessment(dir_path)
    except FileNotFoundError:
        search_dir = input_dir or "~/.fu7ur3pr00f/data/raw/"
        return f"No Gallup PDF files found in '{search_dir}'."
    return "CliftonStrengths assessment processed and indexed to knowledge base."


