# Insurance Intelligence Platform

A local-first application for understanding, searching, comparing, and analysing insurance policy documents. The complete Python RAG and LangGraph implementation will run locally; a future public demo will be a separate, synthetic-data-only deployment.

## Architecture

- **Frontend:** React, TypeScript, and Vite. It communicates with the backend through a same-origin `/api/v1` development proxy.
- **Backend:** FastAPI with versioned routes and Pydantic request/response contracts.
- **Local services:** PDF/DOCX text extraction, parent/child chunking, SQLite metadata/chunk storage, local semantic/BM25/hybrid retrieval with reranking and context compression, and deterministic analysis routing for policy comparison and claim completeness.
- **Public demo boundary:** Cloudflare Pages may host the frontend. The conventional Python backend, FAISS, and transformer inference are not assumed to run on Workers; any public demo adapter will use synthetic data and be evaluated separately.

Phases 1 and 2 establish the API contracts and validated local document ingestion. Phase 3 adds grounded question answering over the stored child chunks.

## Project structure

```text
backend/
  app/
    api/                 Versioned health and document API routes
    core/                Environment-backed settings
    evaluation/          Synthetic retrieval benchmark and ranking metrics
    ingestion/           PDF/DOCX text extraction and parent/child chunking
    schemas/             Shared request/response contracts
    storage/              SQLite document and chunk repository
    main.py              FastAPI application factory
  tests/                 API and schema tests
frontend/
  src/
    api/                 Typed backend client
    App.tsx               Initial platform shell and API status
    main.tsx              React entry point
```

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer with npm

## Local setup

### Backend

From the project directory, create and activate a virtual environment, then install the backend and test dependencies:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

If PowerShell prevents virtual-environment activation, use `.\.venv\Scripts\python.exe` in place of `python` for the install, run, and test commands.

Start the API:

```powershell
python -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive OpenAPI documentation is at `http://127.0.0.1:8000/docs`. The API includes `GET /api/v1/health` and the document ingestion/management endpoints described in [docs/API_CONTRACT.md](docs/API_CONTRACT.md).

Uploaded documents are limited to 25 MiB by default. Metadata and extracted chunks are stored in `backend/data/local/documents.sqlite3`; the original upload is not retained. The DOCX page count is left unset because pagination depends on the rendering application. Configure `INSURANCE_DATABASE_PATH` or `INSURANCE_MAX_UPLOAD_SIZE_BYTES` in `backend/.env` to override the defaults.

Run backend tests from `backend`:

```powershell
python -m pytest
```

Run the deterministic, synthetic-only retrieval benchmark from `backend`:

```powershell
python -m app.evaluation
```

It reports per-strategy precision@k, recall@k, MRR@k, and nDCG@k together with
the benchmark dataset's SHA-256 so runs can be compared against the same
synthetic corpus. See [docs/DEPLOYMENT_READINESS.md](docs/DEPLOYMENT_READINESS.md)
for the public-demo boundary and deployment limitations.

### Frontend

In another terminal:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`). The frontend checks backend health through the Vite `/api` proxy. Build and type-check it with:

```powershell
npm run build
```

## Configuration

- `backend/.env.example`: backend title, API prefix, and allowed frontend origins. Copy it to `backend/.env`; never commit real credentials.
- `frontend/.env.example`: optional API base path. The default `/api/v1` works with the local Vite proxy.
- No model provider, API key, database service, or cloud account is required in Phase 1.

## API contracts

See [docs/API_CONTRACT.md](docs/API_CONTRACT.md) for implemented and planned endpoints and their request/response shapes. Detailed contracts are available as Pydantic models in `backend/app/schemas/`.

## Roadmap

1. **Project skeleton and contracts** — complete; local apps, configuration, health check, and shared schemas.
2. **Synthetic document ingestion** — complete; validated PDF/DOCX extraction with page/section metadata and persisted parent/child chunks.
3. **Baseline local RAG** — complete; local embeddings, semantic retrieval, grounded answers, and citations.
4. **Advanced retrieval experiments** — complete; BM25/hybrid retrieval, reranking, query expansion, context compression, and strategy measurements.
5. **Agent workflows** — complete; deterministic workflow routing, policy comparison, and claim completeness analysis.
6. **Frontend integration and hardening** — complete; document, question, comparison, and claim-review workflows are connected with upload/selection validation, API errors, and prompt-override rejection.
7. **Evaluation and demo readiness** — local synthetic retrieval metrics and deployment limits documented; a public demo remains deferred pending a synthetic-only adapter and compatible hosted API.

Each phase will be verified before progressing. This scaffold intentionally does not implement document analysis before its ingestion and retrieval foundations exist.
