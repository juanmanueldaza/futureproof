"""GitHub data gatherer with MCP and CLI support."""

from pathlib import Path

from ..config import settings
from ..mcp import MCPClientFactory
from ..mcp.github_client import GitHubMCPClient
from ..utils.console import console
from .base import CLIGatherer, MCPGatherer


class GitHubCLIGatherer(CLIGatherer):
    """Gather data from GitHub using github2md CLI.

    This is the original CLI-based gatherer, now used as fallback
    when MCP is unavailable.
    """

    cli_command = "github2md"
    cli_install_hint = "Install with: pip install github2md"

    def __init__(self) -> None:
        self.output_dir = settings.processed_dir / "github"

    def gather(self, username: str | None = None) -> Path:
        """Gather GitHub data for a user.

        Args:
            username: GitHub username (defaults to config)

        Returns:
            Path to the generated markdown file
        """
        user = username or settings.github_username
        self.output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"  Fetching data for: {user}")

        self._run_cli([user, "-o", str(self.output_dir)])

        # Combine output files
        output_file = self.output_dir / "github_profile.md"
        return self._combine_files(
            ["profile.md", "repositories.md", "contributions.md"],
            output_file,
        )


class GitHubGatherer(MCPGatherer):
    """Gather data from GitHub with MCP support and CLI fallback.

    Priority:
    1. MCP server (if GITHUB_PERSONAL_ACCESS_TOKEN or GITHUB_MCP_TOKEN configured)
    2. CLI fallback (github2md)
    """

    def __init__(self) -> None:
        self.output_dir = settings.processed_dir / "github"
        self.fallback_gatherer = GitHubCLIGatherer()

    def _can_use_mcp(self) -> bool:
        """Check if GitHub MCP is configured."""
        return MCPClientFactory.is_available("github")

    async def gather_async(self, username: str | None = None) -> Path:
        """Gather GitHub data using MCP server.

        Args:
            username: GitHub username (defaults to config)

        Returns:
            Path to the generated markdown file
        """
        user = username or settings.github_username
        self.output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"  Fetching data for: {user} (via MCP)")

        github_client = GitHubMCPClient()
        async with github_client:
            # Gather profile
            profile_result = await github_client.get_user_profile()

            # Gather repositories
            repos_result = await github_client.list_user_repos(user)

            # Build markdown output
            markdown = self._format_as_markdown(
                profile_content=profile_result.content,
                repos_content=repos_result.content,
                username=user,
            )

        # Write output
        output_file = self.output_dir / settings.github_output_filename
        output_file.write_text(markdown)
        console.print(f"  Saved to: {output_file}")

        return output_file

    def _format_as_markdown(
        self,
        profile_content: str,
        repos_content: str,
        username: str,
    ) -> str:
        """Format MCP responses as markdown (matching github2md output format).

        Args:
            profile_content: Profile data from MCP
            repos_content: Repository data from MCP
            username: GitHub username

        Returns:
            Formatted markdown string
        """
        parts = [
            f"# GitHub Profile: {username}\n",
            profile_content,
            "\n\n## Repositories\n",
            repos_content,
        ]
        return "\n".join(parts)
