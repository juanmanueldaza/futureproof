"""GitLab data gatherer using gitlab2md package."""

from pathlib import Path

from ..config import settings
from ..utils.console import console
from .base import CLIGatherer


class GitLabGatherer(CLIGatherer):
    """Gather data from GitLab using gitlab2md CLI."""

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
