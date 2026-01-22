"""Simple action orchestrator for career intelligence operations."""

from typing import Any

from ..llm import get_llm
from ..utils.data_loader import combine_career_data
from ..utils.security import anonymize_career_data
from .state import CareerState


def gather_node(state: CareerState) -> dict[str, Any]:
    """Gather data from all sources."""
    from ..gatherers import GitHubGatherer, GitLabGatherer, PortfolioGatherer

    updates: dict[str, Any] = {}

    try:
        # GitHub
        github = GitHubGatherer()
        github_path = github.gather()
        updates["github_data"] = github_path.read_text()

        # GitLab
        gitlab = GitLabGatherer()
        gitlab_path = gitlab.gather()
        updates["gitlab_data"] = gitlab_path.read_text()

        # Portfolio
        portfolio = PortfolioGatherer()
        portfolio_path = portfolio.gather()
        updates["portfolio_data"] = portfolio_path.read_text()

    except Exception as e:
        updates["error"] = str(e)

    return updates


def analyze_node(state: CareerState) -> dict[str, Any]:
    """Analyze career data using LLM."""
    from ..prompts import ANALYZE_CAREER_PROMPT

    llm = get_llm()

    # Combine all available data
    combined_data = combine_career_data(dict(state))

    if not combined_data:
        return {"error": "No data available for analysis. Run 'gather' first."}

    # Anonymize PII before sending to external LLM
    combined_data = anonymize_career_data(combined_data, preserve_professional_emails=True)

    # Determine analysis type
    action = state.get("action", "analyze_full")

    if action == "analyze_goals":
        prompt = f"""Based on the following career data, extract and list all STATED career goals,
aspirations, and targets mentioned. Look for:
- Headlines and taglines that indicate desired roles
- About sections mentioning goals
- Any explicit career objectives

{combined_data}

Provide a clear, bulleted list of stated career goals."""

    elif action == "analyze_reality":
        prompt = f"""Based on the following career data, analyze what this person is ACTUALLY doing.
Look at:
- Technologies and languages used in repositories
- Types of projects built
- Activity patterns
- Skills demonstrated vs claimed

{combined_data}

Provide an honest assessment of actual activities and demonstrated skills."""

    elif action == "analyze_gaps":
        prompt = f"""Based on the following career data, identify GAPS between:
1. What this person SAYS they want (stated goals, headline, aspirations)
2. What they're ACTUALLY doing (projects, languages, activity)

{combined_data}

Provide:
1. A list of stated goals
2. A summary of actual activities
3. Specific gaps identified
4. An alignment score (0-100)
5. Actionable recommendations to close the gaps"""

    else:  # analyze_full
        prompt = f"""{ANALYZE_CAREER_PROMPT}

{combined_data}"""

    try:
        response = llm.invoke(prompt)
        result_key = {
            "analyze_goals": "goals",
            "analyze_reality": "reality",
            "analyze_gaps": "gaps",
        }.get(action, "analysis")

        return {result_key: response.content}
    except Exception as e:
        return {"error": f"Analysis failed: {e}"}


def generate_node(state: CareerState) -> dict[str, Any]:
    """Generate CV using LLM."""
    from ..generators import CVGenerator

    try:
        generator = CVGenerator()

        # Generate both language versions
        cv_en = generator.generate(language="en", format="ats", state=dict(state))
        cv_es = generator.generate(language="es", format="ats", state=dict(state))

        return {"cv_en": str(cv_en), "cv_es": str(cv_es)}
    except Exception as e:
        return {"error": f"Generation failed: {e}"}


def advise_node(state: CareerState) -> dict[str, Any]:
    """Provide strategic career advice."""
    from ..prompts import STRATEGIC_ADVICE_PROMPT

    llm = get_llm()

    target = state.get("target") or "career growth"

    # Combine all available data
    combined_data = combine_career_data(dict(state), include_analysis=True)
    if not combined_data:
        combined_data = "No data available."

    # Anonymize PII before sending to external LLM
    combined_data = anonymize_career_data(combined_data, preserve_professional_emails=True)

    prompt = f"""{STRATEGIC_ADVICE_PROMPT}

TARGET GOAL: {target}

CAREER DATA:
{combined_data}

Provide strategic, actionable advice for achieving the target goal."""

    try:
        response = llm.invoke(prompt)
        return {"advice": response.content}
    except Exception as e:
        return {"error": f"Advice generation failed: {e}"}


def _execute_action(state: CareerState) -> dict[str, Any]:
    """Execute action based on state."""
    action = state.get("action", "")

    # Map actions to handlers
    handlers = {
        "gather": gather_node,
        "generate": generate_node,
        "advise": advise_node,
    }

    # Check for analyze actions (they all use analyze_node)
    if action.startswith("analyze"):
        return analyze_node(state)

    handler = handlers.get(action)
    if handler:
        return handler(state)

    return {"error": f"Unknown action: {action}"}


class _SimpleGraph:
    """Simple graph executor that mimics LangGraph interface."""

    def invoke(self, state: CareerState) -> dict[str, Any]:
        """Execute the action and return updated state."""
        result = dict(state)
        result.update(_execute_action(state))
        return result


def create_graph() -> _SimpleGraph:
    """Create a simple action executor.

    Returns an object with an `invoke(state)` method for backwards compatibility
    with the existing CLI interface.
    """
    return _SimpleGraph()
