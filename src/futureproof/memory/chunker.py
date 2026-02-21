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


class MarkdownChunker:
    """Split content into size-bounded chunks.

    Strategy:
    1. Accept pre-labeled sections (Section NamedTuples)
    2. Split sections that exceed max_tokens by paragraphs
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

        return self._split_large_chunks([chunk])

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (~1.3 tokens per word for English text)."""
        return int(len(text.split()) * 1.3)

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
                        )
                    )

        return result
