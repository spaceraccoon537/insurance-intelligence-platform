from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.evaluation.metrics import ranking_metrics
from app.rag.retrieval import retrieve_chunks, transform_query
from app.schemas import (
    RetrievalEvaluationRequest,
    RetrievalEvaluationResponse,
    RetrievalStrategyMetrics,
)
from app.storage.documents import SQLiteDocumentRepository

router = APIRouter()


def get_document_repository() -> SQLiteDocumentRepository:
    return SQLiteDocumentRepository(get_settings().database_path)


@router.post("/evaluate", response_model=RetrievalEvaluationResponse)
def evaluate_retrieval(
    request: Request,
    body: RetrievalEvaluationRequest,
    repository: SQLiteDocumentRepository = Depends(get_document_repository),
) -> RetrievalEvaluationResponse:
    document_ids = body.document_ids or None
    if body.document_ids:
        missing = [
            document_id
            for document_id in body.document_ids
            if repository.get_document(document_id) is None
        ]
        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {missing[0]}",
            )

    chunks = repository.list_child_chunks(document_ids)
    relevant = set(body.relevant_chunk_ids)
    metrics: list[RetrievalStrategyMetrics] = []

    for strategy in dict.fromkeys(body.strategies):
        retrieved = retrieve_chunks(
            body.question,
            chunks,
            strategy,
            body.top_k,
        )
        chunk_ids = [item.chunk.chunk_id for item in retrieved]
        ranking = (
            ranking_metrics(chunk_ids, relevant, body.top_k)
            if relevant
            else None
        )
        mean_score = (
            sum(item.score for item in retrieved) / len(retrieved)
            if retrieved
            else 0.0
        )
        metrics.append(
            RetrievalStrategyMetrics(
                strategy=strategy,
                chunk_ids=chunk_ids,
                precision_at_k=(
                    ranking.precision_at_k if ranking else 0.0
                ),
                recall_at_k=ranking.recall_at_k if ranking else None,
                mrr_at_k=ranking.mrr_at_k if ranking else None,
                ndcg_at_k=ranking.ndcg_at_k if ranking else None,
                mean_result_score=round(mean_score, 6),
            )
        )

    return RetrievalEvaluationResponse(
        request_id=request.state.request_id,
        query_transform=transform_query(body.question),
        strategies=metrics,
    )
