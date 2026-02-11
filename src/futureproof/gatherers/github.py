"""GitHub data gatherer with MCP and CLI support."""

import json
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

            # Gather repositories (get more to match CLI)
            repos_result = await github_client.list_user_repos(user, per_page=100)

            # Gather contributions data
            prs_result = await github_client.search_user_pull_requests(user, per_page=100)
            issues_result = await github_client.search_user_issues(user, per_page=100)
            reviews_result = await github_client.search_user_reviews(user, per_page=100)

            # Build markdown output
            markdown = self._format_as_markdown(
                profile_json=profile_result.content,
                repos_json=repos_result.content,
                prs_json=prs_result.content,
                issues_json=issues_result.content,
                reviews_json=reviews_result.content,
                username=user,
            )

        # Write output
        output_file = self.output_dir / settings.github_output_filename
        output_file.write_text(markdown)
        console.print(f"  Saved to: {output_file}")

        return output_file

    def _format_as_markdown(
        self,
        profile_json: str,
        repos_json: str,
        prs_json: str,
        issues_json: str,
        reviews_json: str,
        username: str,
    ) -> str:
        """Format MCP responses as markdown (matching github2md output format).

        Args:
            profile_json: Profile data JSON from MCP
            repos_json: Repository data JSON from MCP
            prs_json: Pull requests data JSON from MCP
            issues_json: Issues data JSON from MCP
            reviews_json: Code reviews data JSON from MCP
            username: GitHub username

        Returns:
            Formatted markdown string matching github2md output
        """
        parts = []

        # Parse profile
        try:
            profile = json.loads(profile_json)
            details = profile.get("details", {})

            parts.append(f"# GitHub Profile: {username}\n")
            if details.get("name"):
                parts.append(f"**{details['name']}**\n")
            if details.get("bio"):
                parts.append(f"> {details['bio']}\n")

            parts.append("\n## Info\n")
            if details.get("company"):
                parts.append(f"- **Company:** {details['company']}")
            if details.get("location"):
                parts.append(f"- **Location:** {details['location']}")
            if details.get("created_at"):
                member_since = details["created_at"][:10]  # YYYY-MM-DD
                parts.append(f"- **Member since:** {member_since}")

            parts.append("\n## Stats\n")
            parts.append(f"- **Public Repos:** {details.get('public_repos', 0)}")
            parts.append(f"- **Followers:** {details.get('followers', 0)}")
            parts.append(f"- **Following:** {details.get('following', 0)}")

            profile_url = profile.get("profile_url", f"https://github.com/{username}")
            parts.append(f"\n**Profile:** {profile_url}\n")

        except (json.JSONDecodeError, KeyError):
            parts.append(f"# GitHub Profile: {username}\n")
            parts.append(profile_json)

        # Parse repositories
        parts.append("\n---\n")
        parts.append("# Repositories\n")
        try:
            repos_data = json.loads(repos_json)
            items = repos_data.get("items", [])
            total_count = repos_data.get("total_count", len(items))

            # Calculate totals
            total_stars = sum(r.get("stargazers_count", 0) for r in items)
            total_forks = sum(r.get("forks_count", 0) for r in items)

            parts.append(f"**Total Repositories:** {total_count}")
            parts.append(f"**Total Stars:** {total_stars} | **Total Forks:** {total_forks}\n")

            # List repositories with details
            for repo in items:
                name = repo.get("name", "Unknown")
                desc = repo.get("description", "")
                lang = repo.get("language", "")
                stars = repo.get("stargazers_count", 0)
                forks = repo.get("forks_count", 0)
                url = repo.get("html_url", "")
                archived = repo.get("archived", False)
                topics = repo.get("topics", [])

                status = " (archived)" if archived else ""
                parts.append(f"\n### [{name}]({url}){status}\n")
                if desc:
                    parts.append(f"{desc}\n")
                meta = []
                if lang:
                    meta.append(f"**Language:** {lang}")
                if stars:
                    meta.append(f"**Stars:** {stars}")
                if forks:
                    meta.append(f"**Forks:** {forks}")
                if meta:
                    parts.append(" | ".join(meta))
                if topics:
                    parts.append(f"\n**Topics:** {', '.join(topics)}")

        except (json.JSONDecodeError, KeyError):
            parts.append(repos_json)

        # Parse contributions
        parts.append("\n\n---\n")
        parts.append("# Contributions\n")

        try:
            prs_data = json.loads(prs_json)
            pr_count = prs_data.get("total_count", 0)
        except (json.JSONDecodeError, KeyError):
            pr_count = 0

        try:
            issues_data = json.loads(issues_json)
            issue_count = issues_data.get("total_count", 0)
        except (json.JSONDecodeError, KeyError):
            issue_count = 0

        try:
            reviews_data = json.loads(reviews_json)
            review_count = reviews_data.get("total_count", 0)
        except (json.JSONDecodeError, KeyError):
            review_count = 0

        parts.append("## Breakdown\n")
        parts.append(f"- **Pull Requests:** {pr_count}")
        parts.append(f"- **Issues:** {issue_count}")
        parts.append(f"- **Code Reviews:** {review_count}")

        # Note: GitHub MCP doesn't provide commit count across all repos easily
        # The CLI tool calculates this from the contribution graph which isn't exposed via API
        parts.append(
            "\n*Note: Commit count requires contribution graph access (not available via API)*"
        )

        return "\n".join(parts)
