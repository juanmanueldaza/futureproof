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
    (data_dir / "processed" / "github").mkdir(parents=True)
    (data_dir / "processed" / "gitlab").mkdir(parents=True)
    (data_dir / "processed" / "portfolio").mkdir(parents=True)
    (data_dir / "output").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_career_data() -> dict[str, str]:
    """Sample career data for testing."""
    return {
        "linkedin_data": "# LinkedIn Profile\n\nSoftware Engineer with 5 years experience.",
        "github_data": "# GitHub Profile\n\n## Repositories\n- project-a\n- project-b",
        "gitlab_data": "# GitLab Profile\n\n## Projects\n- internal-tool (Go)",
        "portfolio_data": "# Portfolio\n\n## About\nFull-stack developer passionate about AI.",
    }


@pytest.fixture
def sample_linkedin_files() -> dict[str, str]:
    """Sample LinkedIn file contents."""
    return {
        "profile.md": "# John Doe\n\nSoftware Engineer at TechCorp",
        "experience.md": "## Experience\n\n### TechCorp\nSenior Engineer (2020-present)",
        "education.md": "## Education\n\n### MIT\nBS Computer Science (2016)",
        "skills.md": "## Skills\n\n- Python\n- JavaScript\n- Go",
    }


@pytest.fixture
def mock_llm() -> MagicMock:
    """Mock LLM for testing without API calls."""
    mock = MagicMock()
    mock.invoke.return_value.content = "Mocked LLM response for testing"
    return mock


@pytest.fixture
def mock_llm_with_gemini_format() -> MagicMock:
    """Mock LLM returning Gemini 3 format (list of dicts)."""
    mock = MagicMock()
    mock.invoke.return_value.content = [{"type": "text", "text": "Mocked Gemini 3 response"}]
    return mock


@pytest.fixture
def populated_data_dir(tmp_project: Path, sample_linkedin_files: dict[str, str]) -> Path:
    """Create a temporary project with sample data files."""
    processed_dir = tmp_project / "data" / "processed"

    # Write LinkedIn files
    linkedin_dir = processed_dir / "linkedin"
    for filename, content in sample_linkedin_files.items():
        (linkedin_dir / filename).write_text(content)

    # Write GitHub file
    (processed_dir / "github" / "github_profile.md").write_text(
        "# GitHub Profile\n\n## Repositories\n- awesome-project"
    )

    # Write GitLab file
    (processed_dir / "gitlab" / "gitlab_profile.md").write_text(
        "# GitLab Profile\n\n## Projects\n- internal-tool"
    )

    # Write Portfolio file
    (processed_dir / "portfolio" / "portfolio.md").write_text(
        "# Portfolio\n\n## About Me\nPassionate developer"
    )

    return tmp_project
