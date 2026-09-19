from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        # Split on sentence-ending punctuation followed by whitespace
        sentences = re.split(r'(?<=[.!?])[\s]+', text.strip())
        # Remove empty strings
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return [text.strip()]

        chunks: list[str] = []
        for i in range(0, len(sentences), self.max_sentences_per_chunk):
            group = sentences[i : i + self.max_sentences_per_chunk]
            chunk = " ".join(group).strip()
            if chunk:
                chunks.append(chunk)
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        results = self._split(text, self.separators)
        return [c for c in results if c.strip()]

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        # Base case: text fits in chunk_size
        if len(current_text) <= self.chunk_size:
            return [current_text]

        # No separators left: return text as-is (can't split further)
        if not remaining_separators:
            return [current_text]

        separator = remaining_separators[0]
        next_separators = remaining_separators[1:]

        # Empty string separator: split character by character into chunk_size pieces
        if separator == "":
            chunks = []
            for i in range(0, len(current_text), self.chunk_size):
                chunks.append(current_text[i : i + self.chunk_size])
            return chunks

        parts = current_text.split(separator)

        # If separator doesn't split, try next separator
        if len(parts) <= 1:
            return self._split(current_text, next_separators)

        # Recombine small parts and recursively split large ones
        results: list[str] = []
        current_group = parts[0]
        for part in parts[1:]:
            candidate = current_group + separator + part
            if len(candidate) <= self.chunk_size:
                current_group = candidate
            else:
                # Flush current group
                if current_group:
                    results.extend(self._split(current_group, next_separators))
                current_group = part
        if current_group:
            results.extend(self._split(current_group, next_separators))
        return results


class HeadingBasedChunker:
    """Split Markdown by headings, then recursively split oversized sections.

    Every child produced from an oversized section receives the section heading
    again so that it remains understandable when retrieved on its own.
    """

    HEADING_PATTERN = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*$")

    def __init__(self, chunk_size: int = 800) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        matches = list(self.HEADING_PATTERN.finditer(text))
        if not matches:
            return self._split_without_heading(text.strip())

        chunks: list[str] = []
        preamble = text[: matches[0].start()].strip()
        if preamble:
            chunks.extend(self._split_without_heading(preamble))

        for index, match in enumerate(matches):
            section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            heading = match.group(0).strip()
            body = text[match.end() : section_end].strip()
            chunks.extend(self._split_section(heading, body))

        return chunks

    def _split_without_heading(self, text: str) -> list[str]:
        return [
            part.strip()
            for part in RecursiveChunker(chunk_size=self.chunk_size).chunk(text)
            if part.strip()
        ]

    def _split_section(self, heading: str, body: str) -> list[str]:
        section = f"{heading}\n\n{body}" if body else heading
        if len(section) <= self.chunk_size:
            return [section]

        # Keep enough room to prepend the heading to every recursive child.
        body_chunk_size = self.chunk_size - len(heading) - 2
        if body_chunk_size <= 0:
            return self._split_without_heading(section)

        body_parts = RecursiveChunker(chunk_size=body_chunk_size).chunk(body)
        return [f"{heading}\n\n{part.strip()}" for part in body_parts if part.strip()]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    dot_product = _dot(vec_a, vec_b)
    mag_a = math.sqrt(_dot(vec_a, vec_a))
    mag_b = math.sqrt(_dot(vec_b, vec_b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot_product / (mag_a * mag_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=0),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }
        result = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            count = len(chunks)
            avg_length = sum(len(c) for c in chunks) / count if count > 0 else 0
            result[name] = {
                "count": count,
                "avg_length": round(avg_length, 2),
                "chunks": chunks,
            }
        return result
