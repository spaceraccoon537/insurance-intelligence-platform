from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.schemas.common import ContractModel


class DocumentStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentResponse(ContractModel):
    document_id: UUID
    filename: str
    content_type: str
    size_bytes: int = Field(ge=1)
    status: DocumentStatus
    created_at: datetime
    page_count: int | None = Field(default=None, ge=1)


class DocumentUploadResponse(ContractModel):
    document: DocumentResponse


class DocumentListResponse(ContractModel):
    documents: list[DocumentResponse]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
