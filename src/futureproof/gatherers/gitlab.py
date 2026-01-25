"""GitLab data gatherer with MCP and CLI support."""

from pathlib import Path

from ..config import settings
from ..mcp import MCPClientFactory
from ..mcp.gitlab_client import GitLabMCPClient
from ..utils.console import console
from .base import CLIGatherer, MCPGatherer


class GitLabCLIGatherer(CLIGatherer):
    """Gather data from GitLab using gitlab2md CLI.

    This is the original CLI-based gatherer, now used as fallback
    when MCP is unavailable.
    """

    cli_command = "gitlab2md"
    cli_install_hint = "Install with: pip install gitlab2md"

    def __init__(self) -> None:
        self.output_dir = settings.processed_dir / "gitlab"

    def gather(self, username: str | None = None) -> Path:
        """Gather GitLab data for a user.

        Args:
            username: GitLab username (defaults to config)

        Returns:
            Path to the generated markdown file
        """
        user = username or settings.gitlab_username
        self.output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"  Fetching data for: {user}")

        # Build command args
        args = [user, "-o", str(self.output_dir)]

        # Add groups if configured
        groups = settings.gitlab_groups_list
        if groups:
            args.extend(["--groups", ",".join(groups)])
            console.print(f"  [dim]Including groups: {', '.join(groups)}[/dim]")

        self._run_cli(args)

        # Combine output files
        output_file = self.output_dir / "gitlab_profile.md"
        return self._combine_files(
            [
                "profile.md",
                "projects.md",
                "member_projects.md",
                "contributed_projects.md",
                "merge_requests.md",
                "issues.md",
                "events.md",
                "groups.md",
            ],
            output_file,
        )


class GitLabGatherer(MCPGatherer):
    """Gather data from GitLab with MCP support and CLI fallback.

    Priority:
    1. MCP server (if GITLAB_MCP_URL and GITLAB_MCP_TOKEN configured)
    2. CLI fallback (gitlab2md)
    """

    def __init__(self) -> None:
        self.output_dir = settings.processed_dir / "gitlab"
        self.fallback_gatherer = GitLabCLIGatherer()

    def _can_use_mcp(self) -> bool:
        """Check if GitLab MCP is configured."""
        return MCPClientFactory.is_available("gitlab")

    async def gather_async(self, username: str | None = None) -> Path:
        """Gather GitLab data using MCP server.

        Args:
            username: GitLab username (defaults to config)

        Returns:
            Path to the generated markdown file
        """
        user = username or settings.gitlab_username
        self.output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"  Fetching data for: {user} (via MCP)")

        gitlab_client = GitLabMCPClient()
        async with gitlab_client:
            # Gather merge requests
            mrs_result = await gitlab_client.search_merge_requests(user)

            # Gather issues
            issues_result = await gitlab_client.search_issues(user)

            # Build markdown output
            markdown = self._format_as_markdown(
                mrs_content=mrs_result.content,
                issues_content=issues_result.content,
                username=user,
            )

        # Write output
        output_file = self.output_dir / settings.gitlab_output_filename
        output_file.write_text(markdown)
        console.print(f"  Saved to: {output_file}")

        return output_file

    def _format_as_markdown(
        self,
        mrs_content: str,
        issues_content: str,
        username: str,
    ) -> str:
        """Format MCP responses as markdown (matching gitlab2md output format).

        Args:
            mrs_content: Merge request data from MCP
            issues_content: Issue data from MCP
            username: GitLab username

        Returns:
            Formatted markdown string
        """
        parts = [
            f"# GitLab Profile: {username}\n",
            "\n## Merge Requests\n",
            mrs_content,
            "\n\n## Issues\n",
            issues_content,
        ]
        return "\n".join(parts)
