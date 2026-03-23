"""CV / resume gatherer.

Parses CV and resume files (PDF or Markdown) into labeled sections
for indexing into the career knowledge base.
"""

import hashlib
import logging
import re
import shutil
import subprocess  # nosec B404 — required for pdftotext CLI
from functools import lru_cache
from pathlib import Path

from ..memory.chunker import Section
from ..services.exceptions import NoDataError, ServiceError

logger = logging.getLogger(__name__)

CV_SECTION_KEYWORDS: frozenset[str] = frozenset({
    "profile",
    "summary",
    "objective",
    "experience",
    "work experience",
    "employment",
    "education",
    "skills",
    "technical skills",
    "projects",
    "certifications",
    "languages",
    "awards",
    "achievements",
    "publications",
    "interests",
    "references",
    "volunteer",
    "courses",
})

# Regex for Markdown headings (# / ## / ###)
_MD_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)", re.MULTILINE)

# Regex for all-caps lines that look like PDF section headings
# e.g. "EXPERIENCE", "WORK EXPERIENCE", "OPEN SOURCE / PROJECTS"
_PDF_ALLCAPS_RE = re.compile(r"^[A-Z][A-Z\s/&-]{2,}$")

# Short all-caps words to exclude from section heading detection
_PDF_ALLCAPS_EXCLUDE = frozenset({
    "NO", "YES", "US", "UK", "IT", "AI", "OK", "ID", "CV",
    "CEO", "CTO", "CFO", "COO", "VP", "SR", "JR", "MD", "PHD",
})


def _file_cache_key(path: Path) -> tuple[str, float, int]:
    """Generate cache key from file path, mtime, and size.
    
    Cache is automatically invalidated when file is modified.
    """
    stat = path.stat()
    return (str(path), stat.st_mtime, stat.st_size)


class CVGatherer:
    """Gather and parse a CV or resume file into labeled sections.

    Supports .pdf (via pdftotext) and .md / .txt (stdlib file I/O).
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
            fmt = "pdf"
        else:
            raw_text = self._extract_text_markdown(path)
            fmt = "markdown"

        if not raw_text.strip():
            raise NoDataError(
                f"No text could be extracted from '{path.name}'. "
                "Is it a scanned/image PDF or an empty file?"
            )

        sections = self._parse_sections(raw_text, fmt)
        if not sections:
            logger.debug("No section headers found in '%s', using fallback section.", path.name)
            return [Section("CV Content", raw_text)]

        return sections

    @lru_cache(maxsize=128)
    def _extract_text_pdf_cached(self, cache_key: tuple[str, float, int]) -> str:
        """Cached PDF text extraction.
        
        Cache is invalidated when file is modified (mtime/size change).
        """
        # cache_key contains (path_str, mtime, size) - we only need path for extraction
        path = Path(cache_key[0])
        return self._extract_text_pdf_uncached(path)
    
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
            raise NoDataError(
                f"File '{path.name}' is empty — no content to import."
            )
        return content

    def _parse_sections(self, text: str, fmt: str) -> list[Section]:
        """Detect section boundaries and return a list of Section objects.

        Args:
            text: Raw extracted text.
            fmt: ``'pdf'`` or ``'markdown'``.

        Returns:
            list[Section] — empty list if no section headers are detected.
        """
        if fmt == "markdown":
            return self._parse_sections_markdown(text)
        return self._parse_sections_pdf(text)

    # ------------------------------------------------------------------
    # Markdown parsing
    # ------------------------------------------------------------------

    def _parse_sections_markdown(self, text: str) -> list[Section]:
        """Split Markdown on ATX headings (# / ## / ###)."""
        matches = list(_MD_HEADING_RE.finditer(text))
        if not matches:
            return []

        sections: list[Section] = []
        for i, match in enumerate(matches):
            heading = match.group(1).strip()
            content_start = match.end()
            content_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[content_start:content_end].strip()
            if content:
                sections.append(Section(heading, content))

        return sections

    # ------------------------------------------------------------------
    # PDF / plain-text parsing
    # ------------------------------------------------------------------

    def _parse_sections_pdf(self, text: str) -> list[Section]:
        """Detect ALL-CAPS or canonical-keyword headings in plain PDF text."""
        lines = text.splitlines()
        heading_indices: list[tuple[int, str]] = []

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if self._is_pdf_heading(stripped):
                heading_indices.append((idx, stripped.title()))

        if not heading_indices:
            return []

        sections: list[Section] = []
        for i, (heading_line, heading_name) in enumerate(heading_indices):
            content_start = heading_line + 1
            content_end = heading_indices[i + 1][0] if i + 1 < len(heading_indices) else len(lines)
            content_lines = [ln for ln in lines[content_start:content_end] if ln.strip()]
            # Require at least 2 non-empty content lines to count as a real section
            if len(content_lines) >= 2:
                sections.append(Section(heading_name, "\n".join(content_lines)))

        return sections

    def _is_pdf_heading(self, line: str) -> bool:
        """Return True if this line looks like a PDF section heading."""
        lower = line.lower()
        # Exact canonical keyword match (single or multi-word, case-insensitive)
        if lower in CV_SECTION_KEYWORDS:
            return True
        # All-caps pattern: e.g. "EXPERIENCE", "OPEN SOURCE / PROJECTS"
        if _PDF_ALLCAPS_RE.match(line):
            # Exclude short all-caps words and common acronyms
            if line in _PDF_ALLCAPS_EXCLUDE:
                return False
            # Require at least 3 words or 8 characters for multi-word headings
            if " " in line or "/" in line or "-" in line:
                return len(line) >= 8
            return True
        return False
