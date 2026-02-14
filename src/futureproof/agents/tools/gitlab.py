"""GitLab tools for live queries via MCP server."""

from langchain_core.tools import tool

from ._async import run_async


async def _gitlab_call(tool_name: str, args: dict) -> str:
    """Connect to GitLab MCP, call a tool, return content."""
    from futureproof.mcp.base import MCPClientError
    from futureproof.mcp.gitlab_client import GitLabMCPClient

    client = GitLabMCPClient()
    try:
        await client.connect()
        result = await client.call_tool(tool_name, args)
        if result.is_error:
            return f"GitLab API error: {result.error_message or result.content}"
        return result.content
    except MCPClientError as e:
        return f"GitLab connection error: {e}"
    except Exception as e:
        return f"GitLab error: {e}"
    finally:
        await client.disconnect()


@tool
def search_gitlab_projects(query: str) -> str:
    """Search for projects on GitLab.

    Args:
        query: Search query (e.g., "colmena", project name, or keyword)

    Use this to find projects/repositories on GitLab by name or description.
    """
    return run_async(
        _gitlab_call(
            "search",
            {"search_type": "projects", "query": query},
        )
    )


@tool
def get_gitlab_project(project_path: str) -> str:
    """Get details about a specific GitLab project.

    Args:
        project_path: Full project path (e.g., "username/project-name"
                      or "group/subgroup/project-name")

    Use this to get detailed information about a specific GitLab project
    including description, visibility, stars, and recent activity.
    """
    return run_async(
        _gitlab_call(
            "get_project",
            {"project_id": project_path},
        )
    )


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
    return run_async(
        _gitlab_call(
            "get_file_contents",
            {"project_id": project_path, "file_path": file_path, "ref": ref},
        )
    )
