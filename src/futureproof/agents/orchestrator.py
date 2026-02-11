"""LangGraph orchestrator for career intelligence operations.

This module uses LangGraph's Functional API (@entrypoint/@task) to implement:
- Parallel execution for data gathering
- Action-based routing via a Python dispatcher
- Tool calling for dynamic data enrichment
- Structured output via Pydantic models

SRP-compliant: Task functions use extracted helpers for:
- Data preparation (helpers/data_pipeline.py)
- LLM invocation (helpers/llm_invoker.py)
- Result key mapping (helpers/result_mapper.py)
"""

from typing import Any

from langgraph.func import entrypoint, task

from ..prompts import get_prompt_builder
from .helpers import advice_pipeline, default_invoker, default_pipeline, get_result_key

# ============================================================================
# Task Functions
# ============================================================================


@task
def gather_github_task() -> dict[str, Any]:
    """Gather GitHub data."""
    from ..gatherers import GitHubGatherer

    try:
        github = GitHubGatherer()
        path = github.gather()
        return {"github_data": path.read_text()}
    except Exception as e:
        return {"error": f"GitHub: {e}"}


@task
def gather_gitlab_task() -> dict[str, Any]:
    """Gather GitLab data."""
    from ..gatherers import GitLabGatherer

    try:
        gitlab = GitLabGatherer()
        path = gitlab.gather()
        return {"gitlab_data": path.read_text()}
    except Exception as e:
        return {"error": f"GitLab: {e}"}


@task
def gather_portfolio_task() -> dict[str, Any]:
    """Gather Portfolio data."""
    from ..gatherers import PortfolioGatherer

    try:
        portfolio = PortfolioGatherer()
        path = portfolio.gather()
        return {"portfolio_data": path.read_text()}
    except Exception as e:
        return {"error": f"Portfolio: {e}"}


@task
def gather_market_task() -> dict[str, Any]:
    """Gather market intelligence data."""
    return {
        "job_market": None,
        "tech_trends": None,
        "economic_context": None,
    }


@task
def analyze_task(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze career data using LLM."""
    prompt_builder = get_prompt_builder()

    career_data = default_pipeline.prepare(state)
    if not career_data:
        return {"error": "No data available for analysis. Run 'gather' first."}

    if state.get("include_market"):
        career_data = prompt_builder.enrich_with_market_context(career_data, state)

    action = state.get("action", "analyze_full")
    prompt = prompt_builder.build_analysis_prompt(action, career_data)

    return default_invoker.invoke(prompt, get_result_key(action), "Analysis")


@task
def analyze_market_task(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze career data against market intelligence."""
    prompt_builder = get_prompt_builder()

    career_data = default_pipeline.prepare(state)
    if not career_data:
        return {"error": "No career data available. Run 'gather all' first."}

    market_context = prompt_builder.build_market_context(state)
    if not market_context:
        return {"error": "No market data available. Run 'market gather' first."}

    action = state.get("action", "analyze_market_fit")
    prompt = prompt_builder.build_market_analysis_prompt(action, career_data, market_context)

    return default_invoker.invoke(prompt, get_result_key(action, "market_fit"), "Market analysis")


@task
def generate_task(state: dict[str, Any]) -> dict[str, Any]:
    """Generate CV using LLM."""
    from ..generators import CVGenerator

    try:
        generator = CVGenerator()
        cv_en = generator.generate(language="en", format="ats", state=state)
        cv_es = generator.generate(language="es", format="ats", state=state)
        return {"cv_en": str(cv_en), "cv_es": str(cv_es)}
    except Exception as e:
        return {"error": f"Generation failed: {e}"}


@task
def advise_task(state: dict[str, Any]) -> dict[str, Any]:
    """Provide strategic career advice."""
    prompt_builder = get_prompt_builder()
    target = state.get("target") or "career growth"

    career_data = advice_pipeline.prepare(state)
    if not career_data:
        career_data = "No data available."

    market_context = None
    if state.get("include_market"):
        market_context = prompt_builder.build_market_context(state)

    prompt = prompt_builder.build_advice_prompt(target, career_data, market_context)

    return default_invoker.invoke(prompt, "advice", "Advice generation")


# ============================================================================
# Entrypoint (replaces StateGraph + conditional routing)
# ============================================================================


@entrypoint()
def execute_workflow(state: dict[str, Any]) -> dict[str, Any]:
    """Execute a career intelligence workflow based on the action field.

    Routes to the appropriate task based on state["action"]:
    - gather / gather_all: Parallel data gathering from all sources
    - gather_market: Market intelligence gathering
    - analyze_*: Career or market analysis
    - generate: CV generation
    - advise: Career advice

    Args:
        state: CareerState dict with an "action" field

    Returns:
        Updated state dict with results
    """
    action = state.get("action", "")

    if action in ("gather", "gather_all"):
        # Parallel execution of all gatherers
        github_future = gather_github_task()
        gitlab_future = gather_gitlab_task()
        portfolio_future = gather_portfolio_task()

        github_result = github_future.result()
        gitlab_result = gitlab_future.result()
        portfolio_result = portfolio_future.result()

        # Merge results
        updates: dict[str, Any] = {}
        errors: list[str] = []
        for result in [github_result, gitlab_result, portfolio_result]:
            if "error" in result and result["error"]:
                errors.append(result["error"])
            else:
                updates.update(result)

        if errors and not any(k.endswith("_data") for k in updates):
            updates["error"] = "; ".join(errors)

        return {**state, **updates}

    if action == "gather_market":
        result = gather_market_task().result()
        return {**state, **result}

    if action in (
        "analyze_market",
        "analyze_market_fit",
        "analyze_skill_gaps",
        "analyze_skills",
        "analyze_trends",
    ):
        result = analyze_market_task(state).result()
        return {**state, **result}

    if action.startswith("analyze"):
        result = analyze_task(state).result()
        return {**state, **result}

    if action == "generate":
        result = generate_task(state).result()
        return {**state, **result}

    if action == "advise":
        result = advise_task(state).result()
        return {**state, **result}

    # Unknown action — return state unchanged
    return state


def create_graph():
    """Create the career intelligence workflow.

    Returns the Functional API entrypoint, which has .invoke() and .stream()
    methods compatible with the previous StateGraph interface.

    Returns:
        The execute_workflow entrypoint
    """
    return execute_workflow
