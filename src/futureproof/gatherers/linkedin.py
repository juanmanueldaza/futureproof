"""LinkedIn data gatherer using linkedin2md."""

from pathlib import Path

from ..config import settings
from ..utils.console import console
from .base import CLIGatherer


class LinkedInGatherer(CLIGatherer):
    """Gather data from LinkedIn export using linkedin2md."""

    cli_command = "linkedin2md"
    cli_install_hint = "Install with: pip install linkedin2md"

    def __init__(self) -> None:
        self.output_dir = settings.processed_dir / "linkedin"

    def gather(self, zip_path: Path, output_dir: Path | None = None) -> Path:
        """Process LinkedIn data export ZIP file.

        Args:
            zip_path: Path to the LinkedIn data export ZIP file
            output_dir: Optional custom output directory

        Returns:
            Path to the main profile markdown file
        """
        if not zip_path.exists():
            raise FileNotFoundError(f"LinkedIn export not found: {zip_path}")

        target_dir = output_dir or self.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"  Processing: {zip_path}")
        console.print(f"  Output: {target_dir}")

        result = self._run_cli(
            [
                str(zip_path),
                "-o",
                str(target_dir),
                "--lang",
                settings.default_language,
            ]
        )

        console.print("  [green]Processed successfully[/green]")
        if result.stdout:
            console.print(f"  {result.stdout.strip()}")

        # Return path to the main profile file (consistent with other gatherers)
        profile_file = target_dir / "profile.md"
        if profile_file.exists():
            return profile_file

        # Fallback: return first .md file found or the directory
        md_files = list(target_dir.glob("*.md"))
        return md_files[0] if md_files else target_dir
