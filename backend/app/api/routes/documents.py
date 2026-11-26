from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from app.core.config import get_settings
from app.ingestion.chunking import create_chunks
from app.ingestion.extractors import (
    InvalidDocumentError,
    UnsupportedDocumentError,
    extract_document,
)
from app.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatus,
    DocumentUploadResponse,
)
from app.storage.documents import SQLiteDocumentRepository

router = APIRouter()


def get_document_repository() -> SQLiteDocumentRepository:
    return SQLiteDocumentRepository(get_settings().database_path)


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    repository: SQLiteDocumentRepository = Depends(get_document_repository),
) -> DocumentUploadResponse:
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not filename or len(filename) > 255 or any(ord(character) < 32 for character in filename):
        raise HTTPException(status_code=422, detail="A valid filename is required.")

    max_size = get_settings().max_upload_size_bytes
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="The uploaded document exceeds the size limit.")
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded document is empty.")

    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    try:
        extracted = extract_document(filename, content_type, content)
    except UnsupportedDocumentError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except InvalidDocumentError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    document_id = uuid4()
    document = DocumentResponse(
        document_id=document_id,
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        status=DocumentStatus.READY,
        created_at=datetime.now(timezone.utc),
        page_count=extracted.page_count,
    )
    chunks = create_chunks(document_id, extracted.blocks)
    repository.save_document(document, chunks)
    return DocumentUploadResponse(document=document)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    repository: SQLiteDocumentRepository = Depends(get_document_repository),
) -> DocumentListResponse:
    return repository.list_documents(offset=offset, limit=limit)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    repository: SQLiteDocumentRepository = Depends(get_document_repository),
) -> DocumentResponse:
    document = repository.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    repository: SQLiteDocumentRepository = Depends(get_document_repository),
) -> Response:
    if not repository.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
