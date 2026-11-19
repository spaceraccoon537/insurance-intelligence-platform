from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceCitation(ContractModel):
    document_id: UUID
    filename: str
    page_number: int | None = Field(default=None, ge=1)
    section_title: str | None = None
    chunk_id: str
    excerpt: str = Field(min_length=1, max_length=2000)


class ErrorDetail(ContractModel):
    code: str
    message: str
    request_id: UUID


class ErrorResponse(ContractModel):
    error: ErrorDetail
