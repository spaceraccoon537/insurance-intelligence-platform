from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import Field, StringConstraints

from app.schemas.common import ContractModel, SourceCitation


class RetrievalStrategy(StrEnum):
    SEMANTIC = "semantic"
    BM25 = "bm25"
    HYBRID = "hybrid"


QuestionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class QuestionRequest(ContractModel):
    question: QuestionText
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID


class QuestionResponse(ContractModel):
    request_id: UUID
    answer: str
    citations: list[SourceCitation]
    retrieval_strategy: RetrievalStrategy
