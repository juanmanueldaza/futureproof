"""GitHub data gatherer using github2md package."""

from pathlib import Path

from ..config import settings
from ..utils.console import console
from .base import CLIGatherer


class GitHubGatherer(CLIGatherer):
    """Gather data from GitHub using github2md CLI."""

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
