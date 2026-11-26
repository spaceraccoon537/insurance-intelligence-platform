from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.rag.retrieval import compress_chunk_text, retrieve_chunks
from app.schemas import (
    ClaimAnalysisRequest,
    ClaimAnalysisResponse,
    ComparisonDimension,
    ComparisonRequest,
    ComparisonResponse,
    ComparisonValue,
    Finding,
    FindingSeverity,
    RetrievalStrategy,
    SourceCitation,
)
from app.storage.documents import SQLiteDocumentRepository, StoredChildChunk
from app.workflows.prompt_safety import validate_user_query

router = APIRouter()


def get_document_repository() -> SQLiteDocumentRepository:
    return SQLiteDocumentRepository(get_settings().database_path)


def _require_documents(
    repository: SQLiteDocumentRepository,
    document_ids: list[UUID],
) -> None:
    for document_id in document_ids:
        if repository.get_document(document_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {document_id}",
            )


def _citations(
    question: str,
    chunks: list[StoredChildChunk],
    limit: int = 3,
) -> list[SourceCitation]:
    retrieved = retrieve_chunks(
        question,
        chunks,
        RetrievalStrategy.HYBRID,
        limit,
        query_transform=True,
        rerank=True,
    )
    return [
        SourceCitation(
            document_id=item.chunk.document_id,
            filename=item.chunk.filename,
            page_number=item.chunk.page_number,
            section_title=item.chunk.section_title,
            chunk_id=item.chunk.chunk_id,
            excerpt=compress_chunk_text(question, item.chunk.text),
        )
        for item in retrieved
    ]


def _value_from_citations(citations: list[SourceCitation]) -> str:
    if not citations:
        return "No source text was found for this dimension."
    excerpts = [citation.excerpt.strip() for citation in citations if citation.excerpt]
    value = " ".join(excerpts)
    return value[:2000].rstrip() if value else "No source text was found for this dimension."


@router.post("/comparisons", response_model=ComparisonResponse)
def compare_policies(
    request: Request,
    body: ComparisonRequest,
    repository: SQLiteDocumentRepository = Depends(get_document_repository),
) -> ComparisonResponse:
    for index, focus_area in enumerate(body.focus_areas):
        if focus_area.strip():
            body.focus_areas[index] = validate_user_query(focus_area)
    _require_documents(repository, body.document_ids)
    focus_names = [
        area.strip()
        for area in body.focus_areas
        if area.strip()
    ]
    dimension_names = focus_names or [
        "coverage",
        "deductible",
        "exclusions",
        "limits",
        "claims",
    ]

    dimensions: list[ComparisonDimension] = []
    for dimension_name in dict.fromkeys(dimension_names):
        values: list[ComparisonValue] = []
        for document_id in dict.fromkeys(body.document_ids):
            chunks = repository.list_child_chunks([document_id])
            citations = _citations(dimension_name, chunks)
            values.append(
                ComparisonValue(
                    document_id=document_id,
                    value=_value_from_citations(citations),
                    citations=citations,
                )
            )
        dimensions.append(
            ComparisonDimension(
                name=dimension_name,
                values=values,
            )
        )

    summary = (
        f"Compared {len(body.document_ids)} policy documents across "
        f"{len(dimensions)} dimension(s). "
        "The findings summarize retrieved policy text and may require review."
    )
    return ComparisonResponse(
        request_id=request.state.request_id,
        dimensions=dimensions,
        summary=summary,
    )


@router.post("/claims/analyze", response_model=ClaimAnalysisResponse)
def analyze_claim(
    request: Request,
    body: ClaimAnalysisRequest,
    repository: SQLiteDocumentRepository = Depends(get_document_repository),
) -> ClaimAnalysisResponse:
    _require_documents(repository, [body.policy_document_id, *body.claim_document_ids])

    policy_chunks = repository.list_child_chunks([body.policy_document_id])
    claim_chunks = repository.list_child_chunks(body.claim_document_ids)
    claim_text = "\n".join(chunk.text.lower() for chunk in claim_chunks)

    findings: list[Finding] = []
    completeness_fields = (
        ("date of loss", "Date of loss"),
        ("claim number", "Claim number"),
        ("loss description", "Loss description"),
        ("policyholder", "Policyholder name"),
        ("amount", "Claim amount"),
        ("evidence", "Supporting evidence"),
    )
    for marker, title in completeness_fields:
        if marker not in claim_text:
            findings.append(
                Finding(
                    severity=FindingSeverity.MISSING_INFORMATION,
                    title=f"Missing {title.lower()}",
                    explanation=(
                        f"The submitted claim text does not contain clearly identifiable "
                        f"{title.lower()} information."
                    ),
                    citations=_citations(marker, claim_chunks, limit=1),
                )
            )

    potentially_missing_documents = (
        ("police report", ("police", "theft")),
        ("damage estimate", ("estimate", "repair", "contractor")),
        ("photographs", ("photo", "photograph", "picture")),
        ("receipts", ("receipt", "proof of purchase")),
        ("proof of ownership", ("ownership", "receipt", "invoice")),
    )
    missing_document_types = [
        label
        for label, markers in potentially_missing_documents
        if not any(marker in claim_text for marker in markers)
    ]

    exclusion_terms = (
        ("flood", "flood damage"),
        ("earthquake", "earthquake damage"),
        ("wear and tear", "wear and tear"),
        ("intentional", "intentional damage"),
    )
    for marker, label in exclusion_terms:
        if marker in claim_text:
            policy_citations = _citations(label, policy_chunks)
            if policy_citations:
                findings.append(
                    Finding(
                        severity=FindingSeverity.POTENTIAL_ISSUE,
                        title=f"Possible {label} exclusion",
                        explanation=(
                            f"The claim text mentions {label}. Review the policy "
                            "exclusions and applicable conditions before drawing a coverage conclusion."
                        ),
                        citations=policy_citations,
                    )
                )

    disclaimer = (
        "This is an automated document analysis aid, not a coverage determination "
        "or claim decision. Review the source documents and consult a qualified professional."
    )
    return ClaimAnalysisResponse(
        request_id=request.state.request_id,
        findings=findings,
        potentially_missing_document_types=missing_document_types,
        disclaimer=disclaimer,
    )
