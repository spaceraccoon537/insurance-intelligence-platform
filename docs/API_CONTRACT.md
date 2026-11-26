# API contract

All API routes use the `/api/v1` prefix. JSON uses `snake_case` keys. UUIDs are serialized as strings and timestamps as ISO 8601 UTC values.

## Implemented

| Method | Path | Purpose | Response |
|---|---|---|---|
| `GET` | `/api/v1/health` | Liveness and API version check | `HealthResponse` |
| `POST` | `/api/v1/documents` | Multipart PDF or DOCX upload (`file`) | `DocumentUploadResponse` (`201`) |
| `GET` | `/api/v1/documents` | `offset` and `limit` query parameters | `DocumentListResponse` |
| `GET` | `/api/v1/documents/{document_id}` | Retrieve document metadata | `DocumentResponse` |
| `DELETE` | `/api/v1/documents/{document_id}` | Delete document metadata and its chunks | `204 No Content` |
| `POST` | `/api/v1/questions` | Local grounded question answering | `QuestionResponse` |
| `POST` | `/api/v1/retrieval/evaluate` | Compare retrieval strategies against optional relevant chunk IDs | `RetrievalEvaluationResponse` |
| `POST` | `/api/v1/comparisons` | Compare 2–10 policy documents by dimension | `ComparisonResponse` |
| `POST` | `/api/v1/claims/analyze` | Analyze claim completeness against a policy | `ClaimAnalysisResponse` |

Uploads are limited to 25 MiB by default. The filename extension, declared media type, and file structure are validated; encrypted PDFs and files with no extractable text are rejected. The original upload is not retained. Extracted parent/child chunks and metadata are stored in local SQLite. PDFs include page metadata; DOCX page numbers are unavailable and remain unset. Invalid media types return `415`, malformed or empty documents return `422`, and oversize uploads return `413`.

The document list supports `offset` (default `0`) and `limit` (default `20`, maximum `100`). Missing document IDs return `404`.

Application HTTP errors use the `ErrorResponse` envelope and include an `X-Request-ID` response header. FastAPI request-validation errors retain FastAPI's standard `422` response.

Question and analysis text is sanitized for control characters. Explicit prompt-override attempts are rejected; retrieved document text is treated as untrusted source evidence, never as executable instructions.

## Data contracts

Pydantic definitions in `backend/app/schemas/` are the source of truth:

- **Documents:** lifecycle status, filename, media type, byte size, upload time, and page count when available. Phase 2 completes ingestion synchronously and returns `ready`.
- **Questions:** non-empty question, optional document IDs, and a requested retrieval strategy. Empty document IDs mean the caller's available document collection once document ownership is introduced.
- **Advanced retrieval:** questions support deterministic query expansion, reranking, and context compression. The retrieval evaluation endpoint compares configured strategies and, when relevant chunk IDs are supplied, reports precision@K, recall@K, MRR@K, and nDCG@K using binary relevance. Precision@K uses K as its denominator even when fewer than K chunks are returned. Without relevance labels, ranking metrics other than precision (reported as `0`) are `null`.
- **Citations:** document ID and filename plus optional page/section, chunk reference, and source excerpt.
- **Comparisons:** 2–10 policy document IDs and optional focus areas; findings are grouped by comparison dimension and cite supporting sources.
- **Claim analysis:** a policy document and one or more claim-document IDs; findings distinguish missing information from potential issues and include evidence. This is an analysis aid, not a coverage or claim decision.
- **Errors:** application errors use a stable code, human-readable message, and request ID. FastAPI's standard `422` validation response remains in effect for invalid request bodies in this phase.

## Compatibility principles

- Additive optional fields are preferred over renaming/removing existing fields.
- Stable IDs and source metadata must survive ingestion, retrieval, and citation rendering.
- API keys and provider credentials are server-side configuration and must never be returned by an endpoint.
- Upload limits and supported media types will be enforced when the upload route is implemented.
