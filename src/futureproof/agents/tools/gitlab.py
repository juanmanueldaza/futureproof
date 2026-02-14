"""GitLab tools for live queries via glab CLI."""

import subprocess

from langchain_core.tools import tool


def _glab(args: list[str], timeout: int = 30) -> str:
    """Run a glab CLI command and return output."""
    try:
        result = subprocess.run(
            ["glab", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            error = result.stderr.strip() or result.stdout.strip()
            return f"GitLab CLI error: {error}"
        return result.stdout.strip()
    except FileNotFoundError:
        return (
            "GitLab CLI (glab) is not installed. Install it from https://gitlab.com/gitlab-org/cli"
        )
    except subprocess.TimeoutExpired:
        return "GitLab CLI timed out."


@tool
def search_gitlab_projects(query: str) -> str:
    """Search for projects on GitLab.

    Args:
        query: Search query (e.g., "colmena", project name, or keyword)

    Use this to find projects/repositories on GitLab by name or description.
    """
    return _glab(["repo", "search", "--search", query])


@tool
def get_gitlab_project(project_path: str) -> str:
    """Get details about a specific GitLab project.

    Args:
        project_path: Full project path (e.g., "username/project-name"
                      or "group/subgroup/project-name")

    Use this to get detailed information about a specific GitLab project
    including description, README content, and recent activity.
    """
    return _glab(["repo", "view", project_path, "--output", "json"])


@tool
def get_gitlab_file(project_path: str, file_path: str, ref: str = "main") -> str:
    """Read a file from a GitLab repository.

    Args:
        project_path: Full project path (e.g., "username/project-name")
        file_path: Path to the file (e.g., "README.md")
        ref: Branch or tag name (default: "main")

    Use this to read specific files from a GitLab repo like README.md,
    package.json, etc.
    """
    # URL-encode the file path for the API endpoint
    encoded_path = file_path.replace("/", "%2F")
    endpoint = f"projects/{project_path.replace('/', '%2F')}/repository/files/{encoded_path}/raw"
    return _glab(["api", endpoint, "--method", "GET", "-f", f"ref={ref}"])
