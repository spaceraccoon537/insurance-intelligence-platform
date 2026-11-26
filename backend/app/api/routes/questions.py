from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.rag.retrieval import compress_chunk_text, retrieve_chunks
from app.schemas import QuestionRequest, QuestionResponse, SourceCitation
from app.storage.documents import SQLiteDocumentRepository
from app.workflows.prompt_safety import validate_user_query

router = APIRouter()


def get_document_repository() -> SQLiteDocumentRepository:
    return SQLiteDocumentRepository(get_settings().database_path)


@router.post("", response_model=QuestionResponse)
def answer_question(
    request: Request,
    body: QuestionRequest,
    repository: SQLiteDocumentRepository = Depends(get_document_repository),
) -> QuestionResponse:
    body.question = validate_user_query(body.question)
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
    retrieved = retrieve_chunks(
        body.question,
        chunks,
        body.retrieval_strategy,
        get_settings().rag_top_k,
        query_transform=body.query_transform,
        rerank=body.rerank,
    )

    citations = [
        SourceCitation(
            document_id=item.chunk.document_id,
            filename=item.chunk.filename,
            page_number=item.chunk.page_number,
            section_title=item.chunk.section_title,
            chunk_id=item.chunk.chunk_id,
            excerpt=compress_chunk_text(
                body.question,
                item.chunk.text,
            ) if body.compress_context else item.chunk.text[:2000],
        )
        for item in retrieved
    ]

    if citations:
        answer = (
            "Based on the available document excerpts, "
            + " ".join(
                item.chunk.text.strip()
                for item in retrieved[:3]
            )
        )
        if len(answer) > 4000:
            answer = answer[:3997].rstrip() + "..."
    else:
        answer = (
            "No relevant source text was found in the available documents. "
            "Upload a relevant insurance document or broaden the document selection."
        )

    return QuestionResponse(
        request_id=request.state.request_id,
        answer=answer,
        citations=citations,
        retrieval_strategy=body.retrieval_strategy,
    )
