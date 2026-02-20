"""Markdown chunking for career documents.

Chunks content by size while preserving section metadata.
Section labels are passed in directly — no header regex parsing.
"""

from dataclasses import dataclass, field
from typing import NamedTuple


class Section(NamedTuple):
    """A named section of content (e.g., name="Experience", content="...")."""

    name: str
    content: str


@dataclass
class MarkdownChunk:
    """A chunk of content with section context."""

    content: str
    section_path: list[str] = field(default_factory=list)
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
    """Split content into size-bounded chunks.

    Strategy:
    1. Accept pre-labeled sections (Section NamedTuples)
    2. Split sections that exceed max_tokens by paragraphs
    3. Merge consecutive small sections under min_tokens
    """

    def __init__(self, max_tokens: int = 500, min_tokens: int = 50):
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens

    def chunk_section(self, section: Section) -> list[MarkdownChunk]:
        """Split a single section into size-bounded chunks.

        Section name flows directly into chunk metadata — no header parsing.

        Args:
            section: Named section with content

        Returns:
            List of MarkdownChunk objects with section_path=[section.name]
        """
        content = section.content.strip()
        if not content:
            return []

        chunk = MarkdownChunk(
            content=content,
            section_path=[section.name],
        )

        # Apply size constraints
        chunks = self._merge_small_chunks([chunk])
        return self._split_large_chunks(chunks)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (~1.3 tokens per word for English text)."""
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
                    buffer = MarkdownChunk(
                        content=buffer.content + "\n\n" + chunk.content,
                        section_path=buffer.section_path,
                        header_level=buffer.header_level,
                        start_line=buffer.start_line,
                        end_line=chunk.end_line,
                    )
                else:
                    merged.append(buffer)
                    if chunk_tokens < self.min_tokens:
                        buffer = chunk
                    else:
                        merged.append(chunk)
                        buffer = None

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
                paragraphs = chunk.content.split("\n\n")
                current_content: list[str] = []
                current_tokens = 0

                for para in paragraphs:
                    para_tokens = self._estimate_tokens(para)

                    if current_tokens + para_tokens > self.max_tokens and current_content:
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
