"""Job source registry for OCP-compliant source management.

Adding a new job source requires only adding an entry to JOB_SOURCE_REGISTRY.
No modification to JobMarketGatherer.gather() needed.

This follows the Open/Closed Principle: open for extension (add new sources),
closed for modification (don't change gather() logic).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

# MCP server types for job sources
JobMCPType = Literal[
    "jobspy",
    "remoteok",
    "himalayas",
    "jobicy",
    "weworkremotely",
    "remotive",
    "tavily",
]


@dataclass
class JobSourceConfig:
    """Configuration for a job source.

    Attributes:
        source_name: MCP source identifier (e.g., "jobspy")
        tool_name: Tool to call on the MCP client
        source_label: Human-readable label for logging/display
        build_tool_args: Function to build tool args from (role, location, limit)
        post_process: Optional function to post-process results
        site_name: Site name to tag results with (if source doesn't provide)
        enabled: Whether source is enabled by default
    """

    source_name: JobMCPType
    tool_name: str
    source_label: str
    build_tool_args: Callable[[str, str, int], dict[str, Any]]
    post_process: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None
    site_name: str | None = None
    enabled: bool = True


# Tool args builder functions
def _build_jobspy_args(role: str, location: str, limit: int) -> dict[str, Any]:
    """Build args for JobSpy search."""
    return {"search_term": role, "location": location, "results_wanted": limit}


def _build_remoteok_args(role: str, location: str, limit: int) -> dict[str, Any]:
    """Build args for RemoteOK search."""
    tags = role.lower().split() if role else []
    return {"tags": tags, "limit": limit}


def _build_himalayas_args(role: str, location: str, limit: int) -> dict[str, Any]:
    """Build args for Himalayas search."""
    return {"limit": limit}


def _build_jobicy_args(role: str, location: str, limit: int) -> dict[str, Any]:
    """Build args for Jobicy search."""
    return {"count": limit}


def _build_wwr_args(role: str, location: str, limit: int) -> dict[str, Any]:
    """Build args for WeWorkRemotely search."""
    return {"category": "programming", "limit": limit}


def _build_remotive_args(role: str, location: str, limit: int) -> dict[str, Any]:
    """Build args for Remotive search."""
    return {"category": "software-dev", "limit": limit}


def _build_tavily_salary_args(role: str, location: str, limit: int) -> dict[str, Any]:
    """Build args for Tavily salary search."""
    return {"role": role, "location": location}


# Post-processor factory
def _tag_with_site(site: str) -> Callable[[list[dict[str, Any]]], list[dict[str, Any]]]:
    """Create a post-processor that tags jobs with site name."""

    def _tagger(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for job in jobs:
            job["site"] = site
        return jobs

    return _tagger


# Registry of job sources (OCP: add entries here, no code changes needed)
JOB_SOURCE_REGISTRY: list[JobSourceConfig] = [
    JobSourceConfig(
        source_name="jobspy",
        tool_name="search_jobs",
        source_label="JobSpy",
        build_tool_args=_build_jobspy_args,
    ),
    JobSourceConfig(
        source_name="remoteok",
        tool_name="search_remote_jobs",
        source_label="RemoteOK",
        site_name="remoteok",
        build_tool_args=_build_remoteok_args,
        post_process=_tag_with_site("remoteok"),
    ),
    JobSourceConfig(
        source_name="himalayas",
        tool_name="search_jobs",
        source_label="Himalayas",
        build_tool_args=_build_himalayas_args,
    ),
    JobSourceConfig(
        source_name="jobicy",
        tool_name="search_remote_jobs",
        source_label="Jobicy",
        build_tool_args=_build_jobicy_args,
    ),
    JobSourceConfig(
        source_name="weworkremotely",
        tool_name="search_jobs",
        source_label="WeWorkRemotely",
        build_tool_args=_build_wwr_args,
    ),
    JobSourceConfig(
        source_name="remotive",
        tool_name="search_jobs",
        source_label="Remotive",
        build_tool_args=_build_remotive_args,
    ),
]

# Salary source (handled separately due to different response format)
SALARY_SOURCE = JobSourceConfig(
    source_name="tavily",
    tool_name="search_salary",
    source_label="Tavily",
    build_tool_args=_build_tavily_salary_args,
)
