from io import BytesIO
from uuid import uuid4

from docx import Document as WordDocument
from fastapi.testclient import TestClient

from app.api.routes.documents import get_document_repository
from app.core.config import Settings
from app.ingestion.chunking import CHILD_CHUNK_SIZE, PARENT_CHUNK_SIZE, create_chunks
from app.ingestion.extractors import TextBlock
from app.main import app
from app.storage.documents import SQLiteDocumentRepository

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _make_docx() -> bytes:
    document = WordDocument()
    document.add_heading("Coverage", level=1)
    document.add_paragraph("Synthetic coverage terms. " * 60)
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Limit"
    table.cell(0, 1).text = "$10,000"
    content = BytesIO()
    document.save(content)
    return content.getvalue()


def _make_pdf(text: str) -> bytes:
    escaped_text = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\n", r"\n")
    )
    stream = (
        f"BT /F1 12 Tf 20 250 Td ({escaped_text}) Tj ET\n"
    ).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream
        + b"endstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def _client_and_repository(tmp_path):
    database_path = tmp_path / "documents.sqlite3"
    repository = SQLiteDocumentRepository(database_path)
    app.dependency_overrides[get_document_repository] = lambda: repository
    return TestClient(app), repository, database_path


def test_docx_upload_persists_document_and_parent_child_chunks(tmp_path) -> None:
    client, repository, database_path = _client_and_repository(tmp_path)
    try:
        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "synthetic-policy.docx",
                    _make_docx(),
                    DOCX_CONTENT_TYPE,
                )
            },
        )

        assert response.status_code == 201
        uploaded = response.json()["document"]
        assert uploaded["filename"] == "synthetic-policy.docx"
        assert uploaded["status"] == "ready"
        assert uploaded["page_count"] is None

        stored = repository.get_document(uploaded["document_id"])
        assert stored is not None
        chunks = repository.list_child_chunks()
        assert chunks
        assert all(len(chunk.text) <= CHILD_CHUNK_SIZE for chunk in chunks)
        assert any(chunk.section_title == "Coverage" for chunk in chunks)

        restarted_repository = SQLiteDocumentRepository(database_path)
        assert restarted_repository.get_document(uploaded["document_id"]) == stored
        assert restarted_repository.list_child_chunks()

        listed = client.get("/api/v1/documents?limit=1")
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert client.get(f"/api/v1/documents/{uploaded['document_id']}").status_code == 200

        deleted = client.delete(f"/api/v1/documents/{uploaded['document_id']}")
        assert deleted.status_code == 204
        assert repository.get_document(uploaded["document_id"]) is None
        assert repository.list_child_chunks() == []
        assert client.get(f"/api/v1/documents/{uploaded['document_id']}").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_pdf_upload_records_page_metadata(tmp_path) -> None:
    client, repository, _ = _client_and_repository(tmp_path)
    try:
        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "sample.pdf",
                    _make_pdf("COVERAGE\nSynthetic policy terms."),
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 201
        uploaded = response.json()["document"]
        assert uploaded["page_count"] == 1
        chunks = repository.list_child_chunks()
        assert len(chunks) == 1
        assert chunks[0].page_number == 1
        assert chunks[0].section_title == "COVERAGE"
        assert "Synthetic policy terms." in chunks[0].text
    finally:
        app.dependency_overrides.clear()


def test_chunking_respects_parent_child_sizes_and_metadata_boundaries() -> None:
    document_id = uuid4()
    parents = create_chunks(
        document_id,
        [
            TextBlock("coverage " * 700, page_number=1, section_title="Coverage"),
            TextBlock("limits " * 20, page_number=2, section_title="Limits"),
        ],
    )

    assert len(parents) > 2
    for parent in parents:
        assert len(parent.text) <= PARENT_CHUNK_SIZE
        assert parent.children
        assert all(len(child.text) <= CHILD_CHUNK_SIZE for child in parent.children)
        assert all(child.parent_chunk_id == parent.chunk_id for child in parent.children)
        assert all(child.page_number == parent.page_number for child in parent.children)
    assert parents[-1].page_number == 2
    assert parents[-1].section_title == "Limits"


def test_upload_rejects_unsupported_media_type_and_malformed_docx(tmp_path) -> None:
    client, _, _ = _client_and_repository(tmp_path)
    try:
        unsupported = client.post(
            "/api/v1/documents",
            files={"file": ("policy.txt", b"not a policy", "text/plain")},
        )
        malformed = client.post(
            "/api/v1/documents",
            files={"file": ("policy.docx", b"not a docx", DOCX_CONTENT_TYPE)},
        )

        assert unsupported.status_code == 415
        assert unsupported.json()["error"]["code"] == "unsupported_media_type"
        assert malformed.status_code == 422
        assert malformed.json()["error"]["code"] == "invalid_document"
    finally:
        app.dependency_overrides.clear()


def test_upload_rejects_documents_over_configured_size_limit(tmp_path, monkeypatch) -> None:
    client, _, _ = _client_and_repository(tmp_path)
    monkeypatch.setattr(
        "app.api.routes.documents.get_settings",
        lambda: Settings(
            database_path=tmp_path / "documents.sqlite3",
            max_upload_size_bytes=8,
        ),
    )
    try:
        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "synthetic-policy.docx",
                    _make_docx(),
                    DOCX_CONTENT_TYPE,
                )
            },
        )

        assert response.status_code == 413
    finally:
        app.dependency_overrides.clear()
