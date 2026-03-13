"""GitHub tools for live queries via MCP server."""

import base64
import contextlib
import json
import logging

from langchain_core.tools import tool

from fu7ur3pr00f.config import settings
from fu7ur3pr00f.mcp.pool import call_mcp

logger = logging.getLogger(__name__)
_GITHUB_API_BASE = "https://api.github.com"


def _github_http_headers() -> tuple[dict[str, str] | None, str]:
    token = settings.github_mcp_token_resolved
    if not token:
        return None, (
            "GitHub token not configured. Set GITHUB_PERSONAL_ACCESS_TOKEN "
            "or GITHUB_MCP_TOKEN, or run /setup."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }, ""


def _github_http(tool_name: str, args: dict) -> str:
    """Fallback to GitHub REST API when MCP is unavailable."""
    import httpx

    headers, error = _github_http_headers()
    if error:
        return error

    try:
        with httpx.Client(timeout=20) as client:
            if tool_name == "search_repositories":
                params = {
                    "q": args.get("query", ""),
                    "per_page": args.get("perPage", 10),
                }
                response = client.get(
                    f"{_GITHUB_API_BASE}/search/repositories",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                return response.text

            if tool_name == "get_file_contents":
                owner = args.get("owner", "")
                repo = args.get("repo", "")
                path = (args.get("path") or "").lstrip("/")
                if not owner or not repo:
                    return "GitHub API error: owner and repo are required."
                url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/contents"
                if path:
                    url = f"{url}/{path}"
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict) and data.get("type") == "file":
                    content = data.get("content", "")
                    encoding = data.get("encoding")
                    if encoding == "base64" and content:
                        try:
                            decoded = base64.b64decode(content).decode(
                                "utf-8",
                                errors="replace",
                            )
                            return decoded
                        except Exception:
                            return response.text
                return response.text

            if tool_name == "get_me":
                response = client.get(f"{_GITHUB_API_BASE}/user", headers=headers)
                response.raise_for_status()
                return response.text

            return f"GitHub API error: unsupported tool '{tool_name}'."
    except httpx.HTTPStatusError as exc:
        return f"GitHub API error: {exc.response.status_code} {exc.response.text}"
    except Exception as exc:
        return f"GitHub API error: {exc}"


def _save_github_username(username: str) -> None:
    """Save GitHub username to profile if not already set."""
    from fu7ur3pr00f.memory.profile import edit_profile

    def _set(profile):  # type: ignore[no-untyped-def]
        if not profile.github_username:
            profile.github_username = username

    with contextlib.suppress(Exception):
        edit_profile(_set)


def _github(tool_name: str, args: dict) -> str:
    """Call GitHub MCP via pool, return content or error."""
    result = call_mcp("github", tool_name, args)
    if isinstance(result, str):
        normalized = result.lstrip()
        if normalized.startswith("Github connection error") or "GitHub MCP server" in result:
            logger.info("GitHub MCP unavailable, falling back to REST API: %s", result)
            return _github_http(tool_name, args)
        if "docker: permission denied" in result:
            logger.info("GitHub MCP requires Docker; falling back to REST API")
            return _github_http(tool_name, args)
    return result if isinstance(result, str) else str(result)


@tool
def search_github_repos(
    query: str, per_page: int = 10,
) -> str:
    """Search GitHub repositories by name, description, or topic.

    Args:
        query: Search query (e.g., "fu7ur3pr00f",
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
