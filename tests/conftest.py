"""Shared test fixtures for FutureProof."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


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
        "linkedin_data": "# LinkedIn Profile\n\nSoftware Engineer with 5 years experience.",
        "portfolio_data": "# Portfolio\n\n## About\nFull-stack developer passionate about AI.",
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
    mock.invoke.return_value.content = [{"type": "text", "text": "Mocked structured response"}]
    return mock
