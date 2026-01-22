"""CLI smoke tests for FutureProof."""

from typer.testing import CliRunner

from futureproof.cli import app

runner = CliRunner()


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_app_shows_help(self) -> None:
        """Test app shows help when no args provided."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Career Intelligence System" in result.output

    def test_version_flag(self) -> None:
        """Test --version flag shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "FutureProof" in result.output

    def test_gather_help(self) -> None:
        """Test gather subcommand shows help."""
        result = runner.invoke(app, ["gather", "--help"])
        assert result.exit_code == 0
        assert "Gather professional data" in result.output

    def test_generate_help(self) -> None:
        """Test generate subcommand shows help."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "Generate CVs and reports" in result.output

    def test_analyze_help(self) -> None:
        """Test analyze subcommand shows help."""
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "Analyze career data" in result.output

    def test_advise_help(self) -> None:
        """Test advise subcommand shows help."""
        result = runner.invoke(app, ["advise", "--help"])
        assert result.exit_code == 0
        assert "strategic career advice" in result.output


class TestGatherCommands:
    """Test gather subcommands."""

    def test_gather_all_help(self) -> None:
        """Test gather all shows help."""
        result = runner.invoke(app, ["gather", "all", "--help"])
        assert result.exit_code == 0
        assert "all configured sources" in result.output

    def test_gather_github_help(self) -> None:
        """Test gather github shows help."""
        result = runner.invoke(app, ["gather", "github", "--help"])
        assert result.exit_code == 0
        assert "GitHub" in result.output

    def test_gather_gitlab_help(self) -> None:
        """Test gather gitlab shows help."""
        result = runner.invoke(app, ["gather", "gitlab", "--help"])
        assert result.exit_code == 0
        assert "GitLab" in result.output

    def test_gather_linkedin_help(self) -> None:
        """Test gather linkedin shows help."""
        result = runner.invoke(app, ["gather", "linkedin", "--help"])
        assert result.exit_code == 0
        assert "LinkedIn" in result.output

    def test_gather_portfolio_help(self) -> None:
        """Test gather portfolio shows help."""
        result = runner.invoke(app, ["gather", "portfolio", "--help"])
        assert result.exit_code == 0
        assert "portfolio" in result.output


class TestGenerateCommands:
    """Test generate subcommands."""

    def test_generate_cv_help(self) -> None:
        """Test generate cv shows help."""
        result = runner.invoke(app, ["generate", "cv", "--help"])
        assert result.exit_code == 0
        assert "--lang" in result.output
        assert "--format" in result.output


class TestAnalyzeCommands:
    """Test analyze subcommands."""

    def test_analyze_full_help(self) -> None:
        """Test analyze full shows help."""
        result = runner.invoke(app, ["analyze", "full", "--help"])
        assert result.exit_code == 0
        assert "full career analysis" in result.output

    def test_analyze_goals_help(self) -> None:
        """Test analyze goals shows help."""
        result = runner.invoke(app, ["analyze", "goals", "--help"])
        assert result.exit_code == 0
        assert "goals" in result.output

    def test_analyze_reality_help(self) -> None:
        """Test analyze reality shows help."""
        result = runner.invoke(app, ["analyze", "reality", "--help"])
        assert result.exit_code == 0
        assert "actual activities" in result.output

    def test_analyze_gaps_help(self) -> None:
        """Test analyze gaps shows help."""
        result = runner.invoke(app, ["analyze", "gaps", "--help"])
        assert result.exit_code == 0
        assert "gaps" in result.output


class TestAdviseCommand:
    """Test advise command."""

    def test_advise_without_target_shows_usage(self) -> None:
        """Test advise without target shows usage hint."""
        result = runner.invoke(app, ["advise"])
        assert result.exit_code == 0
        assert "--target" in result.output
