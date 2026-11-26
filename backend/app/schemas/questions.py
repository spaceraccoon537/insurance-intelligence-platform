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
    query_transform: bool = True
    rerank: bool = True
    compress_context: bool = True


class QuestionResponse(ContractModel):
    request_id: UUID
    answer: str
    citations: list[SourceCitation]
    retrieval_strategy: RetrievalStrategy


class RetrievalEvaluationRequest(ContractModel):
    question: QuestionText
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)
    relevant_chunk_ids: list[str] = Field(default_factory=list, max_length=100)
    strategies: list[RetrievalStrategy] = Field(
        default_factory=lambda: list(RetrievalStrategy),
        max_length=3,
    )
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievalStrategyMetrics(ContractModel):
    strategy: RetrievalStrategy
    chunk_ids: list[str]
    precision_at_k: float
    recall_at_k: float | None
    mrr_at_k: float | None
    ndcg_at_k: float | None
    mean_result_score: float


class RetrievalEvaluationResponse(ContractModel):
    request_id: UUID
    query_transform: str
    strategies: list[RetrievalStrategyMetrics]
