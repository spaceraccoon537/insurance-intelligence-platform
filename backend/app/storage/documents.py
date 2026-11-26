from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence
from uuid import UUID

from app.ingestion.chunking import ParentChunk
from app.schemas import DocumentListResponse, DocumentResponse, DocumentStatus


@dataclass(frozen=True)
class StoredChildChunk:
    chunk_id: str
    document_id: UUID
    parent_chunk_id: str
    text: str
    page_number: int | None
    section_title: str | None
    filename: str = ""


class SQLiteDocumentRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    page_count INTEGER CHECK (page_count IS NULL OR page_count > 0)
                );

                CREATE TABLE IF NOT EXISTS document_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                    parent_chunk_id TEXT REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
                    kind TEXT NOT NULL CHECK (kind IN ('parent', 'child')),
                    ordinal INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    page_number INTEGER,
                    section_title TEXT,
                    UNIQUE (document_id, kind, ordinal)
                );

                CREATE INDEX IF NOT EXISTS idx_document_chunks_document
                    ON document_chunks(document_id, kind, ordinal);
                """
            )

    @staticmethod
    def _to_response(row: sqlite3.Row) -> DocumentResponse:
        return DocumentResponse(
            document_id=UUID(row["document_id"]),
            filename=row["filename"],
            content_type=row["content_type"],
            size_bytes=row["size_bytes"],
            status=DocumentStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            page_count=row["page_count"],
        )

    def save_document(
        self,
        document: DocumentResponse,
        parent_chunks: Sequence[ParentChunk],
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO documents (
                    document_id, filename, content_type, size_bytes, status, created_at, page_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(document.document_id),
                    document.filename,
                    document.content_type,
                    document.size_bytes,
                    document.status.value,
                    document.created_at.isoformat(),
                    document.page_count,
                ),
            )
            for parent in parent_chunks:
                connection.execute(
                    """
                    INSERT INTO document_chunks (
                        chunk_id, document_id, parent_chunk_id, kind, ordinal, text,
                        page_number, section_title
                    ) VALUES (?, ?, NULL, 'parent', ?, ?, ?, ?)
                    """,
                    (
                        parent.chunk_id,
                        str(document.document_id),
                        parent.ordinal,
                        parent.text,
                        parent.page_number,
                        parent.section_title,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO document_chunks (
                        chunk_id, document_id, parent_chunk_id, kind, ordinal, text,
                        page_number, section_title
                    ) VALUES (?, ?, ?, 'child', ?, ?, ?, ?)
                    """,
                    [
                        (
                            child.chunk_id,
                            str(document.document_id),
                            parent.chunk_id,
                            child.ordinal,
                            child.text,
                            child.page_number,
                            child.section_title,
                        )
                        for child in parent.children
                    ],
                )

    def list_documents(self, offset: int = 0, limit: int = 20) -> DocumentListResponse:
        with self._connection() as connection:
            total = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            rows = connection.execute(
                """
                SELECT * FROM documents
                ORDER BY created_at DESC, document_id
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return DocumentListResponse(
            documents=[self._to_response(row) for row in rows],
            total=total,
            offset=offset,
            limit=limit,
        )

    def get_document(self, document_id: UUID) -> DocumentResponse | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE document_id = ?",
                (str(document_id),),
            ).fetchone()
        return self._to_response(row) if row else None

    def delete_document(self, document_id: UUID) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM documents WHERE document_id = ?",
                (str(document_id),),
            )
        return cursor.rowcount > 0

    def list_child_chunks(
        self,
        document_ids: Sequence[UUID] | None = None,
    ) -> list[StoredChildChunk]:
        if document_ids == []:
            return []

        query = """
            SELECT
                document_chunks.chunk_id,
                document_chunks.document_id,
                document_chunks.parent_chunk_id,
                document_chunks.text,
                document_chunks.page_number,
                document_chunks.section_title,
                documents.filename
            FROM document_chunks
            JOIN documents ON documents.document_id = document_chunks.document_id
            WHERE document_chunks.kind = 'child'
        """
        parameters: tuple[str, ...] = ()
        if document_ids is not None:
            placeholders = ",".join("?" for _ in document_ids)
            query += f" AND document_chunks.document_id IN ({placeholders})"
            parameters = tuple(str(document_id) for document_id in document_ids)
        query += " ORDER BY document_chunks.document_id, document_chunks.ordinal"

        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [
            StoredChildChunk(
                chunk_id=row["chunk_id"],
                document_id=UUID(row["document_id"]),
                parent_chunk_id=row["parent_chunk_id"],
                text=row["text"],
                page_number=row["page_number"],
                section_title=row["section_title"],
                filename=row["filename"],
            )
            for row in rows
        ]
