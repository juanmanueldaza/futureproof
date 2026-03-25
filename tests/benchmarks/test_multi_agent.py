"""Benchmarks for the orchestrator routing."""

import time

import pytest

from fu7ur3pr00f.agents.specialists.coach import CoachAgent
from fu7ur3pr00f.agents.specialists.code import CodeAgent
from fu7ur3pr00f.agents.specialists.founder import FounderAgent
from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
from fu7ur3pr00f.agents.specialists.learning import LearningAgent
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
    orch = OrchestratorAgent()
    orch._specialists = {
        "coach": CoachAgent(),
        "learning": LearningAgent(),
        "jobs": JobsAgent(),
        "code": CodeAgent(),
        "founder": FounderAgent(),
    }
    return orch


def test_routing_latency(orchestrator: OrchestratorAgent) -> None:
    """Routing should be sub-millisecond."""
    start = time.perf_counter()
    for query in TEST_QUERIES:
        route = orchestrator.route(query)
        assert route in {"coach", "learning", "jobs", "code", "founder"}
    elapsed = time.perf_counter() - start
    assert elapsed < 0.01, f"Routing took {elapsed * 1000:.2f}ms"


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
        1 for query, expected in cases if orchestrator.route(query) == expected
    )
    accuracy = correct / len(cases)
    assert accuracy >= 0.8, f"Routing accuracy {accuracy * 100:.0f}% < 80%"


def test_list_agents(orchestrator: OrchestratorAgent) -> None:
    """All five specialists should be listed."""
    agents = orchestrator.list_agents()
    assert len(agents) == 5
    names = {a["name"] for a in agents}
    assert names == {"coach", "learning", "jobs", "code", "founder"}
