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

from collections.abc import Callable
from typing import Any

from langgraph.func import entrypoint, task

from ..prompts import get_prompt_builder
from .helpers import advice_pipeline, default_pipeline, get_result_key, invoke_llm

# ============================================================================
# Task Functions
# ============================================================================


def _make_gather_task(gatherer_module_attr: str, data_key: str, label: str):
    """Create a gather task for a specific data source."""

    @task
    def _gather() -> dict[str, Any]:
        from .. import gatherers

        try:
            cls = getattr(gatherers, gatherer_module_attr)
            path = cls().gather()
            return {data_key: path.read_text()}
        except Exception as e:
            return {"error": f"{label}: {e}"}

    return _gather


gather_github_task = _make_gather_task("GitHubGatherer", "github_data", "GitHub")
gather_gitlab_task = _make_gather_task("GitLabGatherer", "gitlab_data", "GitLab")
gather_portfolio_task = _make_gather_task("PortfolioGatherer", "portfolio_data", "Portfolio")


@task
def analyze_task(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze career data using LLM."""
    prompt_builder = get_prompt_builder()

    career_data = default_pipeline(state)
    if not career_data:
        return {"error": "No data available for analysis. Run 'gather' first."}

    if state.get("include_market"):
        career_data = prompt_builder.enrich_with_market_context(career_data, state)

    action = state.get("action", "analyze_full")
    prompt = prompt_builder.build_analysis_prompt(action, career_data)

    return invoke_llm(prompt, get_result_key(action), "Analysis")


@task
def analyze_market_task(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze career data against market intelligence."""
    prompt_builder = get_prompt_builder()

    career_data = default_pipeline(state)
    if not career_data:
        return {"error": "No career data available. Run 'gather all' first."}

    market_context = prompt_builder.build_market_context(state)
    if not market_context:
        return {"error": "No market data available. Run 'market gather' first."}

    action = state.get("action", "analyze_market_fit")
    prompt = prompt_builder.build_market_analysis_prompt(action, career_data, market_context)

    return invoke_llm(prompt, get_result_key(action, "market_fit"), "Market analysis")


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

    career_data = advice_pipeline(state)
    if not career_data:
        career_data = "No data available."

    market_context = None
    if state.get("include_market"):
        market_context = prompt_builder.build_market_context(state)

    prompt = prompt_builder.build_advice_prompt(target, career_data, market_context)

    return invoke_llm(prompt, "advice", "Advice generation")


# ============================================================================
# Action Handlers (extracted from execute_workflow for OCP)
# ============================================================================


def _handle_gather(state: dict[str, Any]) -> dict[str, Any]:
    """Parallel execution of all career data gatherers."""
    github_future = gather_github_task()
    gitlab_future = gather_gitlab_task()
    portfolio_future = gather_portfolio_task()

    github_result = github_future.result()
    gitlab_result = gitlab_future.result()
    portfolio_result = portfolio_future.result()

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


def _make_handler(task_fn):
    """Create a handler that runs a task and merges results into state."""

    def handler(state: dict[str, Any]) -> dict[str, Any]:
        result = task_fn(state).result()
        return {**state, **result}

    return handler


_handle_analyze_market = _make_handler(analyze_market_task)
_handle_analyze = _make_handler(analyze_task)
_handle_generate = _make_handler(generate_task)
_handle_advise = _make_handler(advise_task)


# Dispatch tables — add new actions here without modifying execute_workflow.
# Exact matches are checked first, then prefix matches as fallback.
_EXACT_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "gather": _handle_gather,
    "gather_all": _handle_gather,
    "analyze_market": _handle_analyze_market,
    "analyze_market_fit": _handle_analyze_market,
    "analyze_skill_gaps": _handle_analyze_market,
    "analyze_skills": _handle_analyze_market,
    "analyze_trends": _handle_analyze_market,
    "generate": _handle_generate,
    "advise": _handle_advise,
}

_PREFIX_HANDLERS: list[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = [
    ("analyze", _handle_analyze),
]


# ============================================================================
# Entrypoint (replaces StateGraph + conditional routing)
# ============================================================================


@entrypoint()
def execute_workflow(state: dict[str, Any]) -> dict[str, Any]:
    """Execute a career intelligence workflow based on the action field.

    Routes to the appropriate task via dispatch tables:
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

    handler = _EXACT_HANDLERS.get(action)
    if handler:
        return handler(state)

    for prefix, prefix_handler in _PREFIX_HANDLERS:
        if action.startswith(prefix):
            return prefix_handler(state)

    # Unknown action — return state unchanged
    return state


def create_graph():
    """Return the execute_workflow entrypoint (has .invoke()/.stream())."""
    return execute_workflow
