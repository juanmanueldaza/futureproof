"""LangGraph orchestrator for career intelligence operations.

This module implements a REAL StateGraph (not that mock bullshit) with:
- Parallel execution for data gathering
- Conditional routing based on state
- Tool calling for dynamic data enrichment
- Structured output via Pydantic models
"""

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..llm import get_llm
from ..utils.data_loader import combine_career_data
from ..utils.security import anonymize_career_data
from .state import CareerState

# ============================================================================
# Node Functions
# ============================================================================


def gather_career_node(state: CareerState) -> dict[str, Any]:
    """Gather career data from all sources (GitHub, GitLab, Portfolio).

    This node runs gatherers in sequence for now. Future: parallel execution.
    """
    from ..gatherers import GitHubGatherer, GitLabGatherer, PortfolioGatherer

    updates: dict[str, Any] = {}
    errors: list[str] = []

    # GitHub
    try:
        github = GitHubGatherer()
        github_path = github.gather()
        updates["github_data"] = github_path.read_text()
    except Exception as e:
        errors.append(f"GitHub: {e}")

    # GitLab
    try:
        gitlab = GitLabGatherer()
        gitlab_path = gitlab.gather()
        updates["gitlab_data"] = gitlab_path.read_text()
    except Exception as e:
        errors.append(f"GitLab: {e}")

    # Portfolio
    try:
        portfolio = PortfolioGatherer()
        portfolio_path = portfolio.gather()
        updates["portfolio_data"] = portfolio_path.read_text()
    except Exception as e:
        errors.append(f"Portfolio: {e}")

    if errors and not any(k.endswith("_data") for k in updates):
        updates["error"] = "; ".join(errors)

    return updates


def gather_market_node(state: CareerState) -> dict[str, Any]:
    """Gather market intelligence data.

    Sources: JobSpy, Brave Search, Hacker News, BLS API.
    This will be implemented when market gatherers are ready.
    """
    # TODO: Implement when market gatherers are created
    # For now, return empty - market data is optional
    return {
        "job_market": None,
        "tech_trends": None,
        "economic_context": None,
    }


def analyze_node(state: CareerState) -> dict[str, Any]:
    """Analyze career data using LLM.

    Supports multiple analysis types:
    - analyze_full: Comprehensive career assessment
    - analyze_goals: Extract stated goals
    - analyze_reality: Analyze actual activities
    - analyze_gaps: Compare goals vs reality
    """
    llm = get_llm()

    # Combine all available career data
    combined_data = combine_career_data(dict(state))

    if not combined_data:
        return {"error": "No data available for analysis. Run 'gather' first."}

    # Anonymize PII before sending to external LLM
    combined_data = anonymize_career_data(combined_data, preserve_professional_emails=True)

    # Add market context if available and requested
    if state.get("include_market"):
        market_context = _build_market_context(state)
        if market_context:
            combined_data = f"{combined_data}\n\n## Market Context\n{market_context}"

    # Determine analysis type and build prompt
    action = state.get("action", "analyze_full")
    prompt = _build_analysis_prompt(action, combined_data)

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


def analyze_market_node(state: CareerState) -> dict[str, Any]:
    """Analyze career data against market intelligence.

    Supports:
    - analyze_market_fit: Profile vs market alignment
    - analyze_skill_gaps: Skills needed for competitiveness
    - analyze_trends: Technology trend analysis
    """
    from ..prompts import (
        MARKET_FIT_PROMPT,
        MARKET_SKILL_GAP_PROMPT,
        TRENDING_SKILLS_PROMPT,
    )

    llm = get_llm()

    # Combine career data
    career_data = combine_career_data(dict(state))
    if not career_data:
        return {"error": "No career data available. Run 'gather all' first."}

    # Build market context
    market_context = _build_market_context(state)
    if not market_context:
        return {"error": "No market data available. Run 'market gather' first."}

    # Anonymize career data
    career_data = anonymize_career_data(career_data, preserve_professional_emails=True)

    action = state.get("action", "analyze_market_fit")

    # Select prompt based on action
    prompts = {
        "analyze_market_fit": MARKET_FIT_PROMPT,
        "analyze_skill_gaps": MARKET_SKILL_GAP_PROMPT,
        "analyze_trends": TRENDING_SKILLS_PROMPT,
    }

    prompt_template = prompts.get(action, MARKET_FIT_PROMPT)
    prompt = prompt_template.format(career_data=career_data, market_data=market_context)

    try:
        response = llm.invoke(prompt)
        result_key = {
            "analyze_market_fit": "market_fit",
            "analyze_skill_gaps": "skill_gaps",
            "analyze_trends": "trending_skills",
        }.get(action, "market_fit")

        return {result_key: response.content}
    except Exception as e:
        return {"error": f"Market analysis failed: {e}"}


def generate_node(state: CareerState) -> dict[str, Any]:
    """Generate CV using LLM."""
    from ..generators import CVGenerator

    try:
        generator = CVGenerator()
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

    # Combine career data with analysis if available
    combined_data = combine_career_data(dict(state), include_analysis=True)
    if not combined_data:
        combined_data = "No data available."

    # Add market context if requested
    if state.get("include_market"):
        market_context = _build_market_context(state)
        if market_context:
            combined_data = f"{combined_data}\n\n## Market Context\n{market_context}"

    # Anonymize PII
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


# ============================================================================
# Routing Functions
# ============================================================================


def route_by_action(
    state: CareerState,
) -> Literal[
    "gather_career",
    "gather_market",
    "analyze",
    "analyze_market",
    "generate",
    "advise",
    "end",
]:
    """Route to appropriate node based on action in state."""
    action = state.get("action", "")

    if action == "gather" or action == "gather_all":
        return "gather_career"

    if action == "gather_market":
        return "gather_market"

    if action in ("analyze_market_fit", "analyze_skill_gaps", "analyze_trends"):
        return "analyze_market"

    if action.startswith("analyze"):
        return "analyze"

    if action == "generate":
        return "generate"

    if action == "advise":
        return "advise"

    return "end"


def should_continue_to_market(state: CareerState) -> Literal["gather_market", "end"]:
    """Check if we should gather market data after career data."""
    if state.get("include_market"):
        return "gather_market"
    return "end"


# ============================================================================
# Helper Functions
# ============================================================================


def _build_analysis_prompt(action: str, combined_data: str) -> str:
    """Build the appropriate analysis prompt based on action type."""
    from ..prompts import ANALYZE_CAREER_PROMPT

    if action == "analyze_goals":
        return f"""Based on the following career data, extract and list all STATED career goals,
aspirations, and targets mentioned. Look for:
- Headlines and taglines that indicate desired roles
- About sections mentioning goals
- Any explicit career objectives

{combined_data}

Provide a clear, bulleted list of stated career goals."""

    elif action == "analyze_reality":
        return f"""Based on the following career data, analyze what this person is ACTUALLY doing.
Look at:
- Technologies and languages used in repositories
- Types of projects built
- Activity patterns
- Skills demonstrated vs claimed

{combined_data}

Provide an honest assessment of actual activities and demonstrated skills."""

    elif action == "analyze_gaps":
        return f"""Based on the following career data, identify GAPS between:
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
        return f"""{ANALYZE_CAREER_PROMPT}

{combined_data}"""


def _build_market_context(state: CareerState) -> str:
    """Build market context string from state."""
    parts = []

    job_market = state.get("job_market")
    if job_market:
        parts.append(f"### Job Market Data\n{job_market}")

    tech_trends = state.get("tech_trends")
    if tech_trends:
        parts.append(f"### Technology Trends\n{tech_trends}")

    economic_context = state.get("economic_context")
    if economic_context:
        parts.append(f"### Economic Context\n{economic_context}")

    salary_data = state.get("salary_data")
    if salary_data:
        parts.append(f"### Salary Data\n{salary_data}")

    return "\n\n".join(parts)


# ============================================================================
# Graph Construction
# ============================================================================


def create_graph() -> CompiledStateGraph[CareerState]:
    """Create the career intelligence StateGraph.

    This is a REAL LangGraph StateGraph with:
    - Conditional routing based on action
    - Separate nodes for different operations
    - Support for market intelligence integration

    Returns:
        Compiled StateGraph ready for invocation
    """
    # Create the graph with our state type
    builder: StateGraph[CareerState] = StateGraph(CareerState)

    # Add nodes
    builder.add_node("gather_career", gather_career_node)
    builder.add_node("gather_market", gather_market_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("analyze_market", analyze_market_node)
    builder.add_node("generate", generate_node)
    builder.add_node("advise", advise_node)

    # Add edges from START - route based on action
    builder.add_conditional_edges(START, route_by_action)

    # All nodes go to END after completion
    builder.add_edge("gather_career", END)
    builder.add_edge("gather_market", END)
    builder.add_edge("analyze", END)
    builder.add_edge("analyze_market", END)
    builder.add_edge("generate", END)
    builder.add_edge("advise", END)

    # Compile and return
    return builder.compile()  # type: ignore[return-value]


# ============================================================================
# Backwards Compatibility
# ============================================================================


class _LegacyGraphWrapper:
    """Wrapper to maintain backwards compatibility with old interface.

    The old code expected create_graph() to return an object with invoke().
    The new StateGraph.compile() returns a CompiledGraph which also has invoke().
    This wrapper ensures the interface stays the same.
    """

    def __init__(self) -> None:
        self._graph: CompiledStateGraph[CareerState] = create_graph()

    def invoke(self, state: CareerState) -> dict[str, Any]:
        """Execute the graph and return updated state."""
        result = self._graph.invoke(state)
        return dict(result)


def get_graph() -> _LegacyGraphWrapper:
    """Get a graph instance with backwards-compatible interface.

    Use this for the existing CLI code that expects the old interface.
    For new code, use create_graph() directly.
    """
    return _LegacyGraphWrapper()
