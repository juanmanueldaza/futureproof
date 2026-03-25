"""Tests for CV generator."""


class TestCVGenerator:
    def test_import(self):
        from fu7ur3pr00f.generators.cv_generator import create_cv

        assert create_cv is not None

    def test_clean_llm_output(self):
        from fu7ur3pr00f.generators.cv_generator import _clean_llm_output

        # Should strip markdown code fences
        raw = "```markdown\n# John Doe\n## Summary\n```"
        cleaned = _clean_llm_output(raw)
        assert "```" not in cleaned
        assert "# John Doe" in cleaned

    def test_clean_llm_output_passthrough(self):
        from fu7ur3pr00f.generators.cv_generator import _clean_llm_output

        raw = "# John Doe\n\n## Summary\nExperienced dev."
        cleaned = _clean_llm_output(raw)
        assert cleaned == raw


class TestCVGeneratorPDFRenderer:
    def test_render_pdf_import(self):
        from fu7ur3pr00f.generators.cv_generator import _render_pdf

        assert _render_pdf is not None
