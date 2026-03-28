"""Benchmarks for the orchestrator routing."""

import time

import pytest

from fu7ur3pr00f.agents.specialists.orchestrator import OrchestratorAgent

TEST_QUERIES = [
    "How can I get promoted?",
    "Learn Python",
    "Find remote jobs",
    "Improve GitHub repos",
    "Start a company",
]


@pytest.fixture
def orchestrator() -> OrchestratorAgent:
    """Return orchestrator with default specialists (no modification needed)."""
    return OrchestratorAgent()


VALID_SPECIALISTS = {"coach", "learning", "jobs", "code", "founder"}


def test_routing_latency(orchestrator: OrchestratorAgent) -> None:
    """Routing with LLM should complete in reasonable time."""
    start = time.perf_counter()
    for query in TEST_QUERIES:
        route = orchestrator.route(query)
        assert isinstance(route, list)
        assert all(name in VALID_SPECIALISTS for name in route)
    elapsed = time.perf_counter() - start
    # LLM routing takes ~1-3s per query; allow 30s for all 5 queries
    assert elapsed < 30, f"Routing took {elapsed:.2f}s"


def test_routing_accuracy(orchestrator: OrchestratorAgent) -> None:
    """Routing should correctly classify common intents."""
    cases = [
        ("Get promoted to Staff Engineer", "coach"),
        ("Learn Python for machine learning", "learning"),
        ("Find a remote senior developer job", "jobs"),
        ("Improve my GitHub profile and repos", "code"),
        ("Launch my SaaS startup", "founder"),
    ]
    correct = sum(
        1 for query, expected in cases if expected in orchestrator.route(query)
    )
    accuracy = correct / len(cases)
    assert accuracy >= 0.8, f"Routing accuracy {accuracy * 100:.0f}% < 80%"


def test_list_agents(orchestrator: OrchestratorAgent) -> None:
    """All five specialists should be listed."""
    agents = orchestrator.list_agents()
    assert len(agents) == 5
    names = {a["name"] for a in agents}
    assert names == {"coach", "learning", "jobs", "code", "founder"}
