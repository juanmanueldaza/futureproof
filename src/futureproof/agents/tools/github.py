"""GitHub tools for live queries via MCP server."""

from langchain_core.tools import tool

from ._async import run_async


async def _github_call(tool_name: str, args: dict) -> str:
    """Connect to GitHub MCP, call a tool, return content."""
    from futureproof.mcp.base import MCPClientError
    from futureproof.mcp.github_client import GitHubMCPClient

    client = GitHubMCPClient()
    try:
        await client.connect()
        result = await client.call_tool(tool_name, args)
        if result.is_error:
            return f"GitHub API error: {result.error_message or result.content}"
        return result.content
    except MCPClientError as e:
        return f"GitHub connection error: {e}"
    except Exception as e:
        return f"GitHub error: {e}"
    finally:
        await client.disconnect()


@tool
def search_github_repos(query: str, per_page: int = 10) -> str:
    """Search GitHub repositories by name, description, or topic.

    Args:
        query: Search query (e.g., "futureproof", "user:daniaza language:python",
               "topic:machine-learning stars:>100")
        per_page: Number of results (default 10, max 100)

    Use this to find repositories on GitHub — the user's own repos or any public repo.
    Supports GitHub search syntax: user:, org:, language:, topic:, stars:>, etc.
    """
    return run_async(
        _github_call(
            "search_repositories",
            {"query": query, "perPage": per_page},
        )
    )


@tool
def get_github_repo(owner: str, repo: str, path: str = "") -> str:
    """Get contents of a GitHub repository or a specific file/directory.

    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        path: Path to file or directory (default: root). Use "README.md"
              to read the project README.

    Use this to browse repo contents or read specific files like README.md,
    package.json, pyproject.toml, etc.
    """
    args: dict = {"owner": owner, "repo": repo}
    if path:
        args["path"] = path
    return run_async(_github_call("get_file_contents", args))


@tool
def get_github_profile(include_repos: bool = False) -> str:
    """Get the authenticated GitHub user's profile.

    Returns the current user's GitHub profile information including
    username, name, bio, public repos, followers, etc.

    Args:
        include_repos: If True, also fetches the user's recent repos
            (sorted by last updated). Use this for career analysis so
            the agent can see what the user is actually building.

    Use this when the user asks about their GitHub profile or to identify
    their GitHub username.
    """
    return run_async(_get_github_profile(include_repos))


async def _get_github_profile(include_repos: bool) -> str:
    """Fetch profile and optionally recent repos in one connection."""
    from futureproof.mcp.base import MCPClientError
    from futureproof.mcp.github_client import GitHubMCPClient

    client = GitHubMCPClient()
    try:
        await client.connect()
        profile_result = await client.call_tool("get_me", {})
        if profile_result.is_error:
            return f"GitHub API error: {profile_result.error_message or profile_result.content}"

        if not include_repos:
            return profile_result.content

        # Extract username from profile JSON
        import json
        try:
            profile_data = json.loads(profile_result.content)
            username = profile_data.get("login", "")
        except (json.JSONDecodeError, TypeError):
            return profile_result.content

        if not username:
            return profile_result.content

        # Fetch user's repos sorted by recently updated
        repos_result = await client.call_tool(
            "search_repositories",
            {"query": f"user:{username} sort:updated", "perPage": 10},
        )
        repos_content = ""
        if not repos_result.is_error:
            repos_content = f"\n\n## Recent Repositories\n{repos_result.content}"

        return profile_result.content + repos_content
    except MCPClientError as e:
        return f"GitHub connection error: {e}"
    except Exception as e:
        return f"GitHub error: {e}"
    finally:
        await client.disconnect()
