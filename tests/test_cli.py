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


class TestChatCommands:
    """Test chat-related commands."""

    def test_chat_help(self) -> None:
        """Test chat shows help."""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "interactive chat session" in result.output

    def test_ask_help(self) -> None:
        """Test ask shows help."""
        result = runner.invoke(app, ["ask", "--help"])
        assert result.exit_code == 0
        assert "single question" in result.output

    def test_memory_help(self) -> None:
        """Test memory shows help."""
        result = runner.invoke(app, ["memory", "--help"])
        assert result.exit_code == 0
        assert "memory" in result.output
