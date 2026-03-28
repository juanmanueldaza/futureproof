"""CV / resume gatherer.

Parses CV and resume files (PDF or Markdown) into labeled sections
for indexing into the career knowledge base.
"""

import json
import logging
import shutil
import subprocess  # nosec B404 — required for pdftotext CLI
from pathlib import Path

from ..memory.chunker import Section
from ..services.exceptions import NoDataError, ServiceError

logger = logging.getLogger(__name__)


_pdf_text_cache: dict[tuple[str, float, int], str] = {}


def _file_cache_key(path: Path) -> tuple[str, float, int]:
    """Generate cache key from file path, mtime, and size.

    Cache is automatically invalidated when file is modified.
    """
    stat = path.stat()
    return (str(path), stat.st_mtime, stat.st_size)


class CVGatherer:
    """Gather and parse a CV or resume file into labeled sections.

    Supports .pdf (via pdftotext) and .md / .txt (stdlib file I/O).
    Uses LLM-based section extraction for all formats.
    """

    def gather(self, file_path: Path | str) -> list[Section]:
        """Parse a CV/resume file into labeled sections.

        Args:
            file_path: Absolute path to a .pdf, .md, or .txt file.

        Returns:
            list[Section] — at least one section is always returned.

        Raises:
            FileNotFoundError: if file_path does not exist or is not a regular file.
            ServiceError: if pdftotext binary is not installed.
            NoDataError: if the file is empty or yields no extractable text.
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"CV file not found: {path}")

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            raw_text = self._extract_text_pdf(path)
        else:
            raw_text = self._extract_text_markdown(path)

        if not raw_text.strip():
            raise NoDataError(
                f"No text could be extracted from {path.name!r}. "
                "Is it a scanned/image PDF or an empty file?"
            )

        sections = self._parse_sections_with_llm(raw_text)
        if not sections:
            logger.debug(
                "LLM returned no sections for '%s', using fallback section.", path.name
            )
            return [Section("CV Content", raw_text)]

        return sections

    def _extract_text_pdf_cached(self, cache_key: tuple[str, float, int]) -> str:
        """Cached PDF text extraction.

        Cache is automatically invalidated when file is modified (mtime/size change).
        """
        if cache_key in _pdf_text_cache:
            return _pdf_text_cache[cache_key]
        path = Path(cache_key[0])
        result = self._extract_text_pdf_uncached(path)
        _pdf_text_cache[cache_key] = result
        return result

    def _extract_text_pdf_uncached(self, path: Path) -> str:
        """Run pdftotext -layout and return stdout (uncached)."""
        pdftotext_path = shutil.which("pdftotext")
        if not pdftotext_path:
            raise ServiceError(
                "pdftotext is not installed. "
                "Install it with: apt install poppler-utils  /  brew install poppler"
            )

        try:
            result = subprocess.run(  # nosec B603 — pdftotext resolved via which()
                [pdftotext_path, "-layout", str(path), "-"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout
            logger.warning("pdftotext failed for %s: %s", path, result.stderr)
            return ""
        except subprocess.TimeoutExpired:
            logger.error("Timeout extracting text from %s", path)
            return ""

    def _extract_text_pdf(self, path: Path) -> str:
        """Run pdftotext with caching.

        Raises:
            ServiceError: if pdftotext is not found on PATH.
        """
        cache_key = _file_cache_key(path)
        return self._extract_text_pdf_cached(cache_key)

    def _extract_text_markdown(self, path: Path) -> str:
        """Read a .md or .txt file as UTF-8.

        Raises:
            NoDataError: if the file is empty after stripping whitespace.
        """
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            raise NoDataError(f"File {path.name!r} is empty — no content to import.")
        return content

    def _parse_sections_with_llm(self, text: str) -> list[Section]:
        """Use LLM to extract labeled sections from CV text.

        Sends the raw text to the LLM and asks for a structured JSON list
        of section title + content pairs. Falls back to empty list on failure
        (caller returns a single fallback section).
        """
        from langchain_core.messages import HumanMessage

        from fu7ur3pr00f.llm.fallback import get_model_with_fallback

        prompt = (
            "Extract all sections from this CV/resume text.\n"
            "Return a JSON array where each element has:\n"
            '  "title": the section heading (e.g. "Experience", "Education", "Skills")\n'
            '  "content": the full text body of that section\n'
            "Only include sections with meaningful content (at least 2 lines).\n\n"
            f"CV text:\n{text[:8000]}\n\n"
            "Respond with valid JSON only — no markdown, no explanation:\n"
            '[{"title": "...", "content": "..."}, ...]'
        )

        try:
            model, _ = get_model_with_fallback(purpose="summary")
            result = model.invoke([HumanMessage(content=prompt)])
            content = result.content.strip()  # type: ignore
            start = content.find("[")
            end = content.rfind("]") + 1
            sections_data = json.loads(content[start:end])
            return [
                Section(s["title"], s["content"])
                for s in sections_data
                if s.get("title") and s.get("content")
            ]
        except Exception:
            logger.warning(
                "LLM section extraction failed, using fallback", exc_info=True
            )
            return []
