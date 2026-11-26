from dataclasses import dataclass
from uuid import UUID

from app.ingestion.extractors import TextBlock

PARENT_CHUNK_SIZE = 2000
CHILD_CHUNK_SIZE = 500


@dataclass(frozen=True)
class ChildChunk:
    chunk_id: str
    parent_chunk_id: str
    text: str
    ordinal: int
    page_number: int | None
    section_title: str | None


@dataclass(frozen=True)
class ParentChunk:
    chunk_id: str
    text: str
    ordinal: int
    page_number: int | None
    section_title: str | None
    children: tuple[ChildChunk, ...]


def _split_text(text: str, max_chars: int) -> list[str]:
    remaining = text.strip()
    pieces: list[str] = []
    while len(remaining) > max_chars:
        split_at = remaining.rfind(" ", 0, max_chars + 1)
        if split_at <= 0:
            split_at = max_chars
        pieces.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def create_chunks(document_id: UUID, blocks: list[TextBlock]) -> tuple[ParentChunk, ...]:
    parents: list[ParentChunk] = []
    buffer: list[str] = []
    buffer_size = 0
    page_number: int | None = None
    section_title: str | None = None
    child_ordinal = 0

    def flush_parent() -> None:
        nonlocal buffer, buffer_size, child_ordinal
        if not buffer:
            return

        text = "\n".join(buffer)
        parent_ordinal = len(parents) + 1
        parent_id = f"{document_id}:p{parent_ordinal:04d}"
        children: list[ChildChunk] = []
        for child_text in _split_text(text, CHILD_CHUNK_SIZE):
            child_ordinal += 1
            children.append(
                ChildChunk(
                    chunk_id=f"{document_id}:c{child_ordinal:04d}",
                    parent_chunk_id=parent_id,
                    text=child_text,
                    ordinal=child_ordinal,
                    page_number=page_number,
                    section_title=section_title,
                )
            )
        parents.append(
            ParentChunk(
                chunk_id=parent_id,
                text=text,
                ordinal=parent_ordinal,
                page_number=page_number,
                section_title=section_title,
                children=tuple(children),
            )
        )
        buffer = []
        buffer_size = 0

    for block in blocks:
        if not block.text.strip():
            continue
        pieces = _split_text(block.text, PARENT_CHUNK_SIZE)
        for piece in pieces:
            metadata_changed = bool(
                buffer
                and (page_number != block.page_number or section_title != block.section_title)
            )
            added_size = len(piece) + (1 if buffer else 0)
            if metadata_changed or buffer_size + added_size > PARENT_CHUNK_SIZE:
                flush_parent()

            if not buffer:
                page_number = block.page_number
                section_title = block.section_title
            buffer.append(piece)
            buffer_size += len(piece) + (1 if len(buffer) > 1 else 0)

    flush_parent()
    return tuple(parents)
