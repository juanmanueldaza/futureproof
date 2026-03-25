"""Shared test fixtures for FutureProof."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_asyncio import fixture as async_fixture

from fu7ur3pr00f.agents.specialists.orchestrator import OrchestratorAgent


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project structure with data directories."""
    data_dir = tmp_path / "data"
    (data_dir / "raw").mkdir(parents=True)
    (data_dir / "processed" / "linkedin").mkdir(parents=True)
    (data_dir / "processed" / "portfolio").mkdir(parents=True)
    (data_dir / "output").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_career_data() -> dict[str, str]:
    """Sample career data for testing."""
    return {
        "linkedin_data": (
            "# LinkedIn Profile\n\n" "Software Engineer with 5 years experience."
        ),
        "portfolio_data": (
            "# Portfolio\n\n## About\n" "Full-stack developer passionate about AI."
        ),
    }


@pytest.fixture
def mock_llm() -> MagicMock:
    """Mock LLM for testing without API calls."""
    mock = MagicMock()
    mock.invoke.return_value.content = "Mocked LLM response for testing"
    return mock


@pytest.fixture
def mock_llm_with_structured_format() -> MagicMock:
    """Mock LLM returning structured content format (list of dicts)."""
    mock = MagicMock()
    mock.invoke.return_value.content = [
        {"type": "text", "text": "Mocked structured response"}
    ]
    return mock


@async_fixture
async def orchestrator():
    """Orchestrator for tests."""
    yield OrchestratorAgent()
