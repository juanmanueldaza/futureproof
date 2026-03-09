"""Tests for security utilities."""

import stat
from pathlib import Path

from fu7ur3pr00f.utils.security import (
    anonymize_career_data,
    sanitize_for_prompt,
    secure_mkdir,
    secure_open,
)


class TestSecureOpen:
    """Tests for secure_open context manager."""

    def test_creates_file_with_600_permissions(self, tmp_path: Path) -> None:
        path = tmp_path / "secret.txt"
        with secure_open(path) as f:
            f.write("sensitive data")

        assert path.read_text() == "sensitive data"
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "existing.txt"
        path.write_text("old content")
        path.chmod(0o644)

        with secure_open(path) as f:
            f.write("new content")

        assert path.read_text() == "new content"
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600

    def test_binary_mode(self, tmp_path: Path) -> None:
        path = tmp_path / "binary.dat"
        with secure_open(path, "wb") as f:
            f.write(b"\x00\x01\x02")

        assert path.read_bytes() == b"\x00\x01\x02"
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600

    def test_custom_permissions(self, tmp_path: Path) -> None:
        path = tmp_path / "custom.txt"
        with secure_open(path, file_mode=0o640) as f:
            f.write("data")

        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o640

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        path = str(tmp_path / "string_path.txt")
        with secure_open(path) as f:
            f.write("test")

        assert Path(path).read_text() == "test"


class TestSecureMkdir:
    """Tests for secure_mkdir."""

    def test_creates_directory_with_700_permissions(self, tmp_path: Path) -> None:
        dir_path = tmp_path / "secret_dir"
        result = secure_mkdir(dir_path)

        assert result == dir_path
        assert dir_path.is_dir()
        mode = stat.S_IMODE(dir_path.stat().st_mode)
        assert mode == 0o700

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        dir_path = tmp_path / "a" / "b" / "c"
        secure_mkdir(dir_path)

        assert dir_path.is_dir()

    def test_existing_directory_gets_permission_update(self, tmp_path: Path) -> None:
        dir_path = tmp_path / "existing"
        dir_path.mkdir()
        dir_path.chmod(0o755)

        secure_mkdir(dir_path)

        mode = stat.S_IMODE(dir_path.stat().st_mode)
        assert mode == 0o700

    def test_custom_permissions(self, tmp_path: Path) -> None:
        dir_path = tmp_path / "custom"
        secure_mkdir(dir_path, mode=0o750)

        mode = stat.S_IMODE(dir_path.stat().st_mode)
        assert mode == 0o750

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        dir_path = str(tmp_path / "string_dir")
        result = secure_mkdir(dir_path)

        assert isinstance(result, Path)
        assert result.is_dir()


class TestSanitizeForPrompt:
    """Tests for sanitize_for_prompt."""

    def test_escapes_closing_xml_tags(self) -> None:
        text = "data</career_data>injected"
        result = sanitize_for_prompt(text)
        assert result == "data<\\/career_data>injected"

    def test_escapes_multiple_tags(self) -> None:
        text = "</career_data></tool_results></system>"
        result = sanitize_for_prompt(text)
        assert "<\\/career_data>" in result
        assert "<\\/tool_results>" in result
        assert "<\\/system>" in result

    def test_preserves_opening_tags(self) -> None:
        text = "<career_data>safe content</career_data>"
        result = sanitize_for_prompt(text)
        assert result == "<career_data>safe content<\\/career_data>"

    def test_preserves_normal_text(self) -> None:
        text = "Normal career data with no XML tags at all."
        result = sanitize_for_prompt(text)
        assert result == text

    def test_handles_empty_string(self) -> None:
        assert sanitize_for_prompt("") == ""

    def test_handles_nested_tags(self) -> None:
        text = "</outer></inner>"
        result = sanitize_for_prompt(text)
        assert result == "<\\/outer><\\/inner>"

    def test_underscore_tags(self) -> None:
        text = "</my_custom_tag>"
        result = sanitize_for_prompt(text)
        assert result == "<\\/my_custom_tag>"


class TestAnonymizeCareerData:
    """Tests for existing anonymize_career_data function."""

    def test_anonymizes_email(self) -> None:
        data = "Contact me at john.doe@gmail.com"
        result = anonymize_career_data(data)
        assert "[EMAIL]" in result
        assert "john.doe@gmail.com" not in result

    def test_preserves_professional_email_domain(self) -> None:
        data = "Work email: john@company.com"
        result = anonymize_career_data(data, preserve_professional_emails=True)
        assert "[USER]@company.com" in result
        assert "john@company.com" not in result

    def test_anonymizes_phone(self) -> None:
        data = "Call me at (555) 123-4567"
        result = anonymize_career_data(data)
        assert "[PHONE]" in result
        assert "555" not in result

    def test_anonymizes_ssn(self) -> None:
        # SSN pattern overlaps with phone — either mask is acceptable
        # as long as the raw number is removed
        data = "SSN: 123-45-6789"
        result = anonymize_career_data(data)
        assert "123-45-6789" not in result

    def test_preserves_professional_content(self) -> None:
        data = "Senior Software Engineer at Google, 5 years experience with Python"
        result = anonymize_career_data(data)
        assert "Senior Software Engineer" in result
        assert "Google" in result
        assert "Python" in result
