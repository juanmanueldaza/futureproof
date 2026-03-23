"""Tests for CVGatherer — PDF and Markdown CV parsing."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fu7ur3pr00f.gatherers.cv import CVGatherer
from fu7ur3pr00f.memory.chunker import Section
from fu7ur3pr00f.services.exceptions import NoDataError, ServiceError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

STRUCTURED_PDF_TEXT = """
EXPERIENCE
Software Engineer at Acme Corp (2020-2023)
Led backend services for the payments platform.
Reduced latency by 40% through cache redesign.

EDUCATION
MSc Computer Science, MIT (2018-2020)
Thesis on distributed consensus algorithms.
GPA 4.0 — Dean's List.
"""

STRUCTURED_MD_TEXT = """
## Experience
Software Engineer at Acme Corp (2020-2023)
Led backend services for the payments platform.

## Education
MSc Computer Science, MIT (2018-2020)
Thesis on distributed consensus algorithms.
"""

UNSTRUCTURED_TEXT = "John Doe, software engineer with 5 years experience in Python and Go."


# ---------------------------------------------------------------------------
# _extract_text_pdf
# ---------------------------------------------------------------------------


class TestExtractTextPdf:
    def test_success_returns_stdout(self, tmp_path):
        gatherer = CVGatherer()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = STRUCTURED_PDF_TEXT

        # Create a real temp file for stat() to work with caching
        pdf_file = tmp_path / "resume.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake pdf content")

        with (
            patch("shutil.which", return_value="/usr/bin/pdftotext"),
            patch("subprocess.run", return_value=mock_result),
        ):
            text = gatherer._extract_text_pdf(pdf_file)

        assert text == STRUCTURED_PDF_TEXT

    def test_non_zero_returncode_returns_empty(self, tmp_path):
        gatherer = CVGatherer()
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "some error"
        mock_result.stdout = ""

        pdf_file = tmp_path / "resume.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        with (
            patch("shutil.which", return_value="/usr/bin/pdftotext"),
            patch("subprocess.run", return_value=mock_result),
        ):
            text = gatherer._extract_text_pdf(pdf_file)

        assert text == ""

    def test_pdftotext_missing_raises_service_error(self, tmp_path):
        pdf_file = tmp_path / "resume.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        gatherer = CVGatherer()
        with patch("shutil.which", return_value=None):
            with pytest.raises(ServiceError, match="pdftotext"):
                gatherer._extract_text_pdf(pdf_file)


# ---------------------------------------------------------------------------
# _extract_text_markdown
# ---------------------------------------------------------------------------


class TestExtractTextMarkdown:
    def test_valid_file_returns_content(self, tmp_path):
        md_file = tmp_path / "cv.md"
        md_file.write_text(STRUCTURED_MD_TEXT, encoding="utf-8")
        gatherer = CVGatherer()
        text = gatherer._extract_text_markdown(md_file)
        assert "Experience" in text
        assert "Education" in text

    def test_empty_file_raises_no_data_error(self, tmp_path):
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("   \n\n  ", encoding="utf-8")
        gatherer = CVGatherer()
        with pytest.raises(NoDataError):
            gatherer._extract_text_markdown(empty_file)


# ---------------------------------------------------------------------------
# _parse_sections — PDF mode
# ---------------------------------------------------------------------------


class TestParseSectionsPdf:
    def test_structured_text_returns_sections(self):
        gatherer = CVGatherer()
        sections = gatherer._parse_sections(STRUCTURED_PDF_TEXT, "pdf")
        names = [s.name for s in sections]
        assert any("Experience" in n for n in names)
        assert any("Education" in n for n in names)

    def test_unstructured_text_returns_empty(self):
        gatherer = CVGatherer()
        sections = gatherer._parse_sections(UNSTRUCTURED_TEXT, "pdf")
        assert sections == []


# ---------------------------------------------------------------------------
# _parse_sections — Markdown mode
# ---------------------------------------------------------------------------


class TestParseSectionsMarkdown:
    def test_structured_md_returns_two_sections(self):
        gatherer = CVGatherer()
        sections = gatherer._parse_sections(STRUCTURED_MD_TEXT, "markdown")
        assert len(sections) == 2
        names = [s.name for s in sections]
        assert "Experience" in names
        assert "Education" in names

    def test_partial_sections_returns_only_present(self):
        partial_md = "## Experience\nSoftware Engineer\n\n## Skills\nPython, Go\n"
        gatherer = CVGatherer()
        sections = gatherer._parse_sections(partial_md, "markdown")
        assert len(sections) == 2
        names = [s.name for s in sections]
        assert "Experience" in names
        assert "Skills" in names


# ---------------------------------------------------------------------------
# gather() — happy paths
# ---------------------------------------------------------------------------


class TestGatherHappyPath:
    def test_happy_path_pdf(self, tmp_path):
        pdf_file = tmp_path / "resume.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        gatherer = CVGatherer()
        with patch.object(gatherer, "_extract_text_pdf", return_value=STRUCTURED_PDF_TEXT):
            sections = gatherer.gather(pdf_file)

        assert isinstance(sections, list)
        assert len(sections) > 0
        assert all(isinstance(s, Section) for s in sections)

    def test_happy_path_markdown(self, tmp_path):
        md_file = tmp_path / "cv.md"
        md_file.write_text(STRUCTURED_MD_TEXT, encoding="utf-8")

        gatherer = CVGatherer()
        sections = gatherer.gather(md_file)

        assert isinstance(sections, list)
        assert len(sections) > 0
        names = [s.name for s in sections]
        assert "Experience" in names
        assert "Education" in names


# ---------------------------------------------------------------------------
# gather() — error paths
# ---------------------------------------------------------------------------


class TestGatherErrors:
    def test_missing_file_raises_file_not_found(self, tmp_path):
        gatherer = CVGatherer()
        with pytest.raises(FileNotFoundError):
            gatherer.gather(tmp_path / "nonexistent.pdf")

    def test_scanned_pdf_raises_no_data_error(self, tmp_path):
        pdf_file = tmp_path / "scanned.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        gatherer = CVGatherer()
        with patch.object(gatherer, "_extract_text_pdf", return_value=""):
            with pytest.raises(NoDataError):
                gatherer.gather(pdf_file)

    def test_pdftotext_not_found_raises_service_error(self, tmp_path):
        pdf_file = tmp_path / "resume.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        gatherer = CVGatherer()
        with patch("shutil.which", return_value=None):
            with pytest.raises(ServiceError, match="pdftotext"):
                gatherer.gather(pdf_file)


# ---------------------------------------------------------------------------
# .txt file support
# ---------------------------------------------------------------------------


class TestTxtFileSupport:
    def test_txt_file_parsed_as_markdown(self, tmp_path):
        txt_file = tmp_path / "resume.txt"
        txt_file.write_text(STRUCTURED_MD_TEXT, encoding="utf-8")

        gatherer = CVGatherer()
        sections = gatherer.gather(txt_file)

        assert len(sections) > 0
        assert all(isinstance(s, Section) for s in sections)

    def test_empty_txt_raises_nodataerror(self, tmp_path):
        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("", encoding="utf-8")

        gatherer = CVGatherer()
        with pytest.raises(NoDataError):
            gatherer.gather(txt_file)

    def test_txt_with_headings_parses_sections(self, tmp_path):
        txt_file = tmp_path / "cv.txt"
        txt_file.write_text("""
# John Doe
## Experience
Software Engineer at Acme
## Education
BS Computer Science
""", encoding="utf-8")

        gatherer = CVGatherer()
        sections = gatherer.gather(txt_file)

        assert len(sections) >= 2
        section_names = [s.name.lower() for s in sections]
        assert "experience" in section_names
        assert "education" in section_names


# ---------------------------------------------------------------------------
# gather_cv_data() tool tests
# ---------------------------------------------------------------------------


class TestGatherCvDataTool:
    """Tests for the gather_cv_data tool.
    
    Note: Full integration testing with interrupt() requires LangGraph
    runtime. These tests verify basic validation and error handling.
    """
    
    def test_gather_cv_data_tool_exists(self):
        """Verify the tool is properly registered."""
        from langchain_core.tools import StructuredTool
        from fu7ur3pr00f.agents.tools.gathering import gather_cv_data
        
        assert isinstance(gather_cv_data, StructuredTool)
        assert gather_cv_data.name == "gather_cv_data"
        assert "file_path" in gather_cv_data.args

    def test_gather_cv_data_file_not_found(self, tmp_path):
        from fu7ur3pr00f.agents.tools.gathering import gather_cv_data
        from pathlib import Path

        # Create a file in tmp_path that looks like a PDF but doesn't exist
        # We test the actual error message for non-existent files
        fake_path = str(tmp_path / "subfolder" / "nonexistent.pdf")
        result = gather_cv_data.invoke({"file_path": fake_path})
        # The tool checks is_file() which fails for non-existent paths
        assert "not found" in result.lower() or "access denied" in result.lower()

    def test_gather_cv_data_unsupported_format(self, tmp_path):
        from fu7ur3pr00f.agents.tools.gathering import gather_cv_data
        from pathlib import Path

        # Create a test file in home directory to pass the path check
        import os
        test_file = Path.home() / ".fu7ur3pr00f" / "test_cv.docx"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"fake docx")
        
        try:
            result = gather_cv_data.invoke({"file_path": str(test_file)})
            assert "unsupported format" in result.lower()
        finally:
            test_file.unlink(missing_ok=True)

    def test_gather_cv_data_path_outside_home(self):
        from fu7ur3pr00f.agents.tools.gathering import gather_cv_data

        result = gather_cv_data.invoke({"file_path": "/etc/passwd"})
        assert "access denied" in result.lower()


# ---------------------------------------------------------------------------
# gather() — fallback
# ---------------------------------------------------------------------------


class TestGatherFallback:
    def test_unstructured_content_returns_fallback_section(self, tmp_path):
        md_file = tmp_path / "unstructured.md"
        md_file.write_text(UNSTRUCTURED_TEXT, encoding="utf-8")

        gatherer = CVGatherer()
        sections = gatherer.gather(md_file)

        assert len(sections) == 1
        assert sections[0].name == "CV Content"
        assert sections[0].content == UNSTRUCTURED_TEXT


# ---------------------------------------------------------------------------
# Integration smoke test
# ---------------------------------------------------------------------------


class TestCVGathererIntegration:
    def test_gather_returns_sections_with_name_and_content(self, tmp_path):
        md_file = tmp_path / "cv.md"
        md_file.write_text(STRUCTURED_MD_TEXT, encoding="utf-8")

        sections = CVGatherer().gather(md_file)

        assert isinstance(sections, list)
        assert len(sections) > 0
        for s in sections:
            assert isinstance(s, Section)
            assert s.name
            assert s.content
