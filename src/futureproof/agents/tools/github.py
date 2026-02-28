"""GitHub tools for live queries via MCP server."""

import json

from langchain_core.tools import tool

from futureproof.mcp.pool import call_tool


def _save_github_username(username: str) -> None:
    """Save GitHub username to profile if not already set."""
    from futureproof.memory.profile import edit_profile

    def _set(profile):  # type: ignore[no-untyped-def]
        if not profile.github_username:
            profile.github_username = username

    try:
        edit_profile(_set)
    except Exception:
        pass  # Best-effort — don't break tool call


def _github(tool_name: str, args: dict) -> str:
    """Call GitHub MCP via pool, return content or error."""
    from futureproof.mcp.base import MCPClientError

    try:
        result = call_tool("github", tool_name, args)
        if result.is_error:
            return (
                f"GitHub API error: "
                f"{result.error_message or result.content}"
            )
        return result.content
    except MCPClientError as e:
        return f"GitHub connection error: {e}"
    except Exception as e:
        return f"GitHub error: {e}"


@tool
def search_github_repos(
    query: str, per_page: int = 10,
) -> str:
    """Search GitHub repositories by name, description, or topic.

    Args:
        query: Search query (e.g., "futureproof",
               "user:daniaza language:python",
               "topic:machine-learning stars:>100")
        per_page: Number of results (default 10, max 100)

    Use this to find repositories on GitHub — the user's own
    repos or any public repo.
    Supports GitHub search syntax: user:, org:, language:,
    topic:, stars:>, etc.
    """
    return _github(
        "search_repositories",
        {"query": query, "perPage": per_page},
    )


@tool
def get_github_repo(
    owner: str, repo: str, path: str = "",
) -> str:
    """Get contents of a GitHub repository or file/directory.

    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        path: Path to file or directory (default: root).
              Use "README.md" to read the project README.

    Use this to browse repo contents or read specific files
    like README.md, package.json, pyproject.toml, etc.
    """
    args: dict = {"owner": owner, "repo": repo}
    if path:
        args["path"] = path
    return _github("get_file_contents", args)


@tool
def get_github_profile(include_repos: bool = False) -> str:
    """Get the authenticated GitHub user's profile.

    Returns the current user's GitHub profile information
    including username, name, bio, public repos, followers, etc.

    Args:
        include_repos: If True, also fetches the user's recent
            repos (sorted by last updated). Use this for career
            analysis so the agent can see what the user is
            actually building.

    Use this when the user asks about their GitHub profile or
    to identify their GitHub username.
    """
    profile_content = _github("get_me", {})
    if profile_content.startswith("GitHub"):
        return profile_content  # Error case

    # Extract username and save to profile for future calls
    try:
        data = json.loads(profile_content)
        username = data.get("login", "")
    except (json.JSONDecodeError, TypeError):
        username = ""

    if username:
        _save_github_username(username)

    if not include_repos:
        return profile_content

    if not username:
        return profile_content

    # Reuses the same pooled connection
    repos_content = _github(
        "search_repositories",
        {
            "query": f"user:{username} sort:updated",
            "perPage": 10,
        },
    )
    if repos_content.startswith("GitHub"):
        return profile_content  # Repos failed, return profile

    return (
        profile_content
        + f"\n\n## Recent Repositories\n{repos_content}"
    )
