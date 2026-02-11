"""Intelligent markdown chunking for career documents.

Chunks by markdown headers to preserve semantic boundaries.
Each chunk maintains context about its section hierarchy.
"""

import re
from dataclasses import dataclass, field


@dataclass
class MarkdownChunk:
    """A chunk of markdown with section context."""

    content: str
    section_path: list[str] = field(default_factory=list)  # e.g., ["Repositories", "pokedex"]
    header_level: int = 0
    start_line: int = 0
    end_line: int = 0

    @property
    def section_name(self) -> str:
        """Get the most specific section name."""
        return self.section_path[-1] if self.section_path else ""

    @property
    def parent_section(self) -> str:
        """Get the parent section name."""
        return self.section_path[0] if self.section_path else ""


class MarkdownChunker:
    """Split markdown by headers while preserving context.

    Strategy:
    1. Split on ## headers (level 2) as primary chunks
    2. Include parent # header context in section_path
    3. Keep chunks under max_tokens (configurable)
    4. Merge small sections that are under min_tokens
    """

    # Regex to match markdown headers
    HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __init__(self, max_tokens: int = 500, min_tokens: int = 50):
        """Initialize chunker with token limits.

        Args:
            max_tokens: Maximum tokens per chunk (will split if exceeded)
            min_tokens: Minimum tokens per chunk (will merge if below)
        """
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens

    def chunk(self, content: str) -> list[MarkdownChunk]:
        """Split markdown content into semantic chunks.

        Args:
            content: Raw markdown text

        Returns:
            List of MarkdownChunk objects with section context
        """
        if not content or not content.strip():
            return []

        lines = content.split("\n")
        chunks: list[MarkdownChunk] = []

        # Track current section hierarchy
        current_h1 = ""
        current_chunk_lines: list[str] = []
        current_section_path: list[str] = []
        current_header_level = 0
        chunk_start_line = 0

        for i, line in enumerate(lines):
            header_match = self.HEADER_PATTERN.match(line)

            if header_match:
                level = len(header_match.group(1))
                header_text = header_match.group(2).strip()

                # Save current chunk before starting new section
                if current_chunk_lines:
                    chunk = self._create_chunk(
                        current_chunk_lines,
                        current_section_path.copy(),
                        current_header_level,
                        chunk_start_line,
                        i - 1,
                    )
                    if chunk:
                        chunks.append(chunk)
                    current_chunk_lines = []

                # Update section hierarchy
                if level == 1:
                    current_h1 = header_text
                    current_section_path = [header_text]
                elif level == 2:
                    current_section_path = (
                        [current_h1, header_text] if current_h1 else [header_text]
                    )
                elif level >= 3:
                    # For deeper headers, keep h1 and use this as section
                    if current_h1:
                        current_section_path = [current_h1, header_text]
                    else:
                        current_section_path = [header_text]

                current_header_level = level
                chunk_start_line = i

            current_chunk_lines.append(line)

        # Don't forget the last chunk
        if current_chunk_lines:
            chunk = self._create_chunk(
                current_chunk_lines,
                current_section_path.copy(),
                current_header_level,
                chunk_start_line,
                len(lines) - 1,
            )
            if chunk:
                chunks.append(chunk)

        # Post-process: merge small chunks, split large ones
        chunks = self._merge_small_chunks(chunks)
        chunks = self._split_large_chunks(chunks)

        return chunks

    def _create_chunk(
        self,
        lines: list[str],
        section_path: list[str],
        header_level: int,
        start_line: int,
        end_line: int,
    ) -> MarkdownChunk | None:
        """Create a chunk from lines if it has meaningful content."""
        content = "\n".join(lines).strip()

        # Skip empty or whitespace-only chunks
        if not content:
            return None

        return MarkdownChunk(
            content=content,
            section_path=section_path,
            header_level=header_level,
            start_line=start_line,
            end_line=end_line,
        )

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (simple word-based approximation).

        Uses ~1.3 tokens per word for English text as a rough estimate.
        """
        return int(len(text.split()) * 1.3)

    def _merge_small_chunks(self, chunks: list[MarkdownChunk]) -> list[MarkdownChunk]:
        """Merge consecutive small chunks that share the same parent section."""
        if not chunks:
            return chunks

        merged: list[MarkdownChunk] = []
        buffer: MarkdownChunk | None = None

        for chunk in chunks:
            chunk_tokens = self._estimate_tokens(chunk.content)

            if buffer is None:
                if chunk_tokens < self.min_tokens:
                    buffer = chunk
                else:
                    merged.append(chunk)
            else:
                buffer_tokens = self._estimate_tokens(buffer.content)
                combined_tokens = buffer_tokens + chunk_tokens

                # Merge if same parent section and combined size is reasonable
                same_parent = buffer.parent_section == chunk.parent_section
                fits = combined_tokens <= self.max_tokens

                if same_parent and fits and chunk_tokens < self.min_tokens:
                    # Merge into buffer
                    buffer = MarkdownChunk(
                        content=buffer.content + "\n\n" + chunk.content,
                        section_path=buffer.section_path,
                        header_level=buffer.header_level,
                        start_line=buffer.start_line,
                        end_line=chunk.end_line,
                    )
                else:
                    # Flush buffer and start fresh
                    merged.append(buffer)
                    if chunk_tokens < self.min_tokens:
                        buffer = chunk
                    else:
                        merged.append(chunk)
                        buffer = None

        # Don't forget buffered chunk
        if buffer:
            merged.append(buffer)

        return merged

    def _split_large_chunks(self, chunks: list[MarkdownChunk]) -> list[MarkdownChunk]:
        """Split chunks that exceed max_tokens."""
        result: list[MarkdownChunk] = []

        for chunk in chunks:
            if self._estimate_tokens(chunk.content) <= self.max_tokens:
                result.append(chunk)
            else:
                # Split by paragraphs (double newline)
                paragraphs = chunk.content.split("\n\n")
                current_content: list[str] = []
                current_tokens = 0

                for para in paragraphs:
                    para_tokens = self._estimate_tokens(para)

                    if current_tokens + para_tokens > self.max_tokens and current_content:
                        # Flush current content
                        result.append(
                            MarkdownChunk(
                                content="\n\n".join(current_content),
                                section_path=chunk.section_path,
                                header_level=chunk.header_level,
                                start_line=chunk.start_line,
                                end_line=chunk.end_line,
                            )
                        )
                        current_content = [para]
                        current_tokens = para_tokens
                    else:
                        current_content.append(para)
                        current_tokens += para_tokens

                # Flush remaining
                if current_content:
                    result.append(
                        MarkdownChunk(
                            content="\n\n".join(current_content),
                            section_path=chunk.section_path,
                            header_level=chunk.header_level,
                            start_line=chunk.start_line,
                            end_line=chunk.end_line,
                        )
                    )

        return result
