"""GitHub tools for live queries via MCP server."""

from langchain_core.tools import tool

from ._async import run_async


async def _github_call(tool_name: str, args: dict) -> str:
    """Connect to GitHub MCP, call a tool, return content."""
    from futureproof.mcp.github_client import GitHubMCPClient

    client = GitHubMCPClient()
    try:
        await client.connect()
        result = await client.call_tool(tool_name, args)
        if result.is_error:
            return f"GitHub API error: {result.error_message or result.content}"
        return result.content
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
def get_github_profile() -> str:
    """Get the authenticated GitHub user's profile.

    Returns the current user's GitHub profile information including
    username, name, bio, public repos, followers, etc.

    Use this when the user asks about their GitHub profile or to identify
    their GitHub username.
    """
    return run_async(_github_call("get_me", {}))
