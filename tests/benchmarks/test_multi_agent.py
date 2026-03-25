"""Benchmarks for multi-agent system."""

import asyncio
import time

import pytest

from fu7ur3pr00f.agents.multi_agent import MultiAgentSystem

TEST_QUERIES = [
    "How can I get promoted?",
    "Learn Python",
    "Find remote jobs",
    "Improve GitHub",
    "Start a company",
]


@pytest.mark.asyncio
async def test_routing_latency():
    """Test routing latency."""
    system = MultiAgentSystem()
    await system.initialize()

    assert system.orchestrator is not None
    start = time.perf_counter()
    for query in TEST_QUERIES:
        route = system.orchestrator._route(query)
        assert route in ["coach", "learning", "jobs", "code", "founder"]
    elapsed = time.perf_counter() - start
    assert elapsed < 0.01, f"Routing took {elapsed * 1000:.2f}ms"


@pytest.mark.asyncio
async def test_initialization_latency():
    """Test initialization time."""
    start = time.perf_counter()
    system = MultiAgentSystem()
    await system.initialize()
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0
    assert len(system.get_available_agents()) == 5


@pytest.mark.asyncio
async def test_concurrent_routing():
    """Test concurrent routing."""
    system = MultiAgentSystem()
    await system.initialize()

    assert system.orchestrator is not None

    async def route(q: str) -> str:
        return system.orchestrator._route(q)  # type: ignore[union-attr]

    start = time.perf_counter()
    tasks = [route(q) for q in TEST_QUERIES * 10]
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_routing_accuracy():
    """Test routing accuracy."""
    system = MultiAgentSystem()
    await system.initialize()

    cases = [
        ("Get promoted", "coach"),
        ("Learn Python", "learning"),
        ("Find job", "jobs"),
        ("GitHub", "code"),
        ("Startup", "founder"),
    ]

    assert system.orchestrator is not None
    correct = sum(
        1 for query, expected in cases if system.orchestrator._route(query) == expected
    )

    accuracy = correct / len(cases)
    assert accuracy > 0.9, f"Accuracy {accuracy * 100:.1f}%"
