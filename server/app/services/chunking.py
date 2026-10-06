"""
Split extracted PDF text into overlapping chunks, keeping track of page numbers
so retrieved passages can be cited back to the page they came from.
"""
from bisect import bisect_right
from dataclasses import dataclass

# Chunks are sized so a handful of them fit comfortably in any model's context
TARGET_CHUNK_CHARS = 1_000
CHUNK_OVERLAP_CHARS = 200
MIN_CHUNK_CHARS = 50

# Prefer to break on these, in order, near the end of a chunk
BREAK_CANDIDATES = ("\n\n", "\n", ". ", "? ", "! ", " ")


@dataclass
class Chunk:
    index: int
    content: str
    page_start: int
    page_end: int


def _join_pages(pages: list[str]) -> tuple[str, list[int], list[int]]:
    """
    Join page texts into one string.
    Returns (full_text, page_start_offsets, page_numbers) for offset -> page lookup.
    """
    parts: list[str] = []
    starts: list[int] = []
    numbers: list[int] = []
    offset = 0
    for page_number, text in enumerate(pages, start=1):
        text = (text or "").strip()
        if not text:
            continue
        starts.append(offset)
        numbers.append(page_number)
        parts.append(text)
        offset += len(text) + 1  # +1 for the "\n" added by the join below
    return "\n".join(parts), starts, numbers


def _page_at(offset: int, starts: list[int], numbers: list[int]) -> int:
    """Page number containing the given character offset."""
    if not starts:
        return 1
    position = bisect_right(starts, offset) - 1
    return numbers[max(position, 0)]


def _find_break(text: str, window_start: int, hard_end: int) -> int:
    """
    Find a natural break point in text[window_start:hard_end].
    Returns the index just after the separator, or hard_end if none found.
    """
    for separator in BREAK_CANDIDATES:
        position = text.rfind(separator, window_start, hard_end)
        if position != -1:
            return position + len(separator)
    return hard_end


def chunk_pages(
    pages: list[str],
    target_chars: int = TARGET_CHUNK_CHARS,
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
) -> list[Chunk]:
    """Turn per-page text into overlapping chunks annotated with page ranges."""
    text, starts, numbers = _join_pages(pages)
    text = text.strip()
    if not text:
        return []

    chunks: list[Chunk] = []
    position = 0
    length = len(text)

    while position < length:
        hard_end = min(position + target_chars, length)
        if hard_end < length:
            # Look for a break in the last 40% of the chunk so sizes stay even
            end = _find_break(text, position + int(target_chars * 0.6), hard_end)
        else:
            end = hard_end

        content = text[position:end].strip()
        if len(content) >= MIN_CHUNK_CHARS or (not chunks and content):
            chunks.append(
                Chunk(
                    index=len(chunks),
                    content=content,
                    page_start=_page_at(position, starts, numbers),
                    page_end=_page_at(max(end - 1, position), starts, numbers),
                )
            )

        if end >= length:
            break
        # Step forward, keeping an overlap so sentences spanning a boundary survive
        position = max(end - overlap_chars, position + 1)

    return chunks


def group_chunks_into_sections(
    chunks: list[Chunk] | list, target_chars: int
) -> list[list]:
    """
    Group consecutive chunks into sections of roughly `target_chars`, for
    section-by-section summarization of long documents.
    """
    sections: list[list] = []
    current: list = []
    current_chars = 0

    for chunk in chunks:
        chunk_chars = len(chunk.content)
        if current and current_chars + chunk_chars > target_chars:
            sections.append(current)
            current = []
            current_chars = 0
        current.append(chunk)
        current_chars += chunk_chars

    if current:
        sections.append(current)
    return sections
