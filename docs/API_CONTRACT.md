# API contract

All API routes use the `/api/v1` prefix. JSON uses `snake_case` keys. UUIDs are serialized as strings and timestamps as ISO 8601 UTC values.

## Implemented in Phase 1

| Method | Path | Purpose | Response |
|---|---|---|---|
| `GET` | `/api/v1/health` | Liveness and API version check | `HealthResponse` |

## Planned contracts

These shapes are defined now to guide later implementation. The routes are **not yet available**; they will be added with the relevant ingestion/RAG/workflow phases.

| Method | Path | Request | Response |
|---|---|---|---|
| `POST` | `/api/v1/documents` | Multipart PDF or DOCX upload | `DocumentUploadResponse` |
| `GET` | `/api/v1/documents` | Optional pagination/filter query | `DocumentListResponse` |
| `GET` | `/api/v1/documents/{document_id}` | — | `DocumentResponse` |
| `DELETE` | `/api/v1/documents/{document_id}` | — | `204 No Content` |
| `POST` | `/api/v1/questions` | `QuestionRequest` | `QuestionResponse` |
| `POST` | `/api/v1/comparisons` | `ComparisonRequest` | `ComparisonResponse` |
| `POST` | `/api/v1/claims/analyze` | `ClaimAnalysisRequest` | `ClaimAnalysisResponse` |

## Data contracts

Pydantic definitions in `backend/app/schemas/` are the source of truth:

- **Documents:** lifecycle status, filename, media type, byte size, upload time, and page count when available.
- **Questions:** non-empty question, optional document IDs, and a requested retrieval strategy. Empty document IDs mean the caller's available document collection once document ownership is introduced.
- **Citations:** document ID and filename plus optional page/section, chunk reference, and source excerpt.
- **Comparisons:** 2–10 policy document IDs and optional focus areas; findings are grouped by comparison dimension and cite supporting sources.
- **Claim analysis:** a policy document and one or more claim-document IDs; findings distinguish missing information from potential issues and include evidence. This is an analysis aid, not a coverage or claim decision.
- **Errors:** application errors use a stable code, human-readable message, and request ID. FastAPI's standard `422` validation response remains in effect for invalid request bodies in this phase.

## Compatibility principles

- Additive optional fields are preferred over renaming/removing existing fields.
- Stable IDs and source metadata must survive ingestion, retrieval, and citation rendering.
- API keys and provider credentials are server-side configuration and must never be returned by an endpoint.
- Upload limits and supported media types will be enforced when the upload route is implemented.
