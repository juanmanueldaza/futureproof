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


def _make_handler(task_fn):
    """Create a handler that runs a task and merges results into state."""

    def handler(state: dict[str, Any]) -> dict[str, Any]:
        result = task_fn(state).result()
        return {**state, **result}

    return handler


_handle_analyze_market = _make_handler(analyze_market_task)
_handle_analyze = _make_handler(analyze_task)
_handle_advise = _make_handler(advise_task)


# Dispatch table — add new actions here without modifying execute_workflow.
# Only canonical actions used by callers. Unregistered analyze_* variants
# fall through to _handle_analyze via the startswith("analyze") fallback.
_EXACT_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "analyze_market": _handle_analyze_market,
    "analyze_skills": _handle_analyze_market,
    "advise": _handle_advise,
}

# ============================================================================
# Entrypoint (replaces StateGraph + conditional routing)
# ============================================================================


@entrypoint()
def execute_workflow(state: dict[str, Any]) -> dict[str, Any]:
    """Execute a career intelligence workflow based on the action field.

    Routes to the appropriate task via dispatch table:
    - gather: Parallel data gathering from all sources
    - analyze_market / analyze_skills: Market-aware analysis
    - analyze_*: General career analysis (fallback)
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

    # Fallback: any unregistered analyze_* action gets general analysis
    if action.startswith("analyze"):
        return _handle_analyze(state)

    # Unknown action — return state unchanged
    return state


def create_graph():
    """Return the execute_workflow entrypoint (has .invoke()/.stream())."""
    return execute_workflow
