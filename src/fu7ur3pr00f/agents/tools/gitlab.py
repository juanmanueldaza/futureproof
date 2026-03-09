"""GitLab tools for live queries via glab CLI."""

import re
import shutil
import subprocess  # nosec B404 — required for glab CLI interaction

from langchain_core.tools import tool

# Validation patterns for GitLab CLI inputs
_RE_GIT_REF = re.compile(r"^[a-zA-Z0-9._/-]+$")
_RE_PROJECT_PATH = re.compile(r"^[a-zA-Z0-9._/-]+$")
_RE_FILE_PATH = re.compile(r"^[a-zA-Z0-9._/ -]+$")


def _validate_gitlab_input(
    value: str, name: str, pattern: re.Pattern[str], max_len: int,
) -> str | None:
    """Validate a GitLab CLI input. Returns error message or None if valid."""
    if not value or len(value) > max_len:
        return f"Invalid {name}: must be 1-{max_len} characters."
    if value.startswith("-"):
        return f"Invalid {name}: must not start with '-'."
    if not pattern.match(value):
        return f"Invalid {name}: contains disallowed characters."
    return None


def _glab(args: list[str], timeout: int = 30) -> str:
    """Run a glab CLI command and return output."""
    glab_path = shutil.which("glab")
    if not glab_path:
        return (
            "GitLab CLI (glab) is not installed. Install it from https://gitlab.com/gitlab-org/cli"
        )
    try:
        result = subprocess.run(  # nosec B603 — args are validated, glab resolved via which()
            [glab_path, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            error = result.stderr.strip() or result.stdout.strip()
            return f"GitLab CLI error: {error}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "GitLab CLI timed out."


@tool
def search_gitlab_projects(query: str) -> str:
    """Search for projects on GitLab.

    Args:
        query: Search query (e.g., "colmena", project name, or keyword)

    Use this to find projects/repositories on GitLab by name or description.
    """
    if not query or len(query) > 256:
        return "Invalid query: must be 1-256 characters."
    if query.startswith("-"):
        return "Invalid query: must not start with '-'."
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
    err = _validate_gitlab_input(project_path, "project path", _RE_PROJECT_PATH, 256)
    if err:
        return err
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
    err = _validate_gitlab_input(project_path, "project path", _RE_PROJECT_PATH, 256)
    if err:
        return err
    err = _validate_gitlab_input(file_path, "file path", _RE_FILE_PATH, 512)
    if err:
        return err
    err = _validate_gitlab_input(ref, "ref", _RE_GIT_REF, 256)
    if err:
        return err

    # URL-encode the file path for the API endpoint
    encoded_path = file_path.replace("/", "%2F")
    endpoint = (
        f"projects/{project_path.replace('/', '%2F')}"
        f"/repository/files/{encoded_path}/raw"
    )
    return _glab(["api", endpoint, "--method", "GET", "-f", f"ref={ref}"])
