# Insurance Intelligence Platform

A local-first application for understanding, searching, comparing, and analysing insurance policy documents. The complete Python RAG and LangGraph implementation will run locally; a future public demo will be a separate, synthetic-data-only deployment.

## Architecture

- **Frontend:** React, TypeScript, and Vite. It communicates with the backend through a same-origin `/api/v1` development proxy.
- **Backend:** FastAPI with versioned routes and Pydantic request/response contracts.
- **Planned local services:** PDF/DOCX ingestion, Sentence Transformers embeddings, FAISS dense retrieval, BM25 lexical retrieval, SQLite metadata/evaluation storage, and LangGraph workflows.
- **Public demo boundary:** Cloudflare Pages may host the frontend. The conventional Python backend, FAISS, and transformer inference are not assumed to run on Workers; any public demo adapter will use synthetic data and be evaluated separately.

The Phase 1 contract types define stable shapes for documents, questions/citations, comparisons, and claim completeness. Only the health endpoint is implemented in this phase; analysis routes are added alongside their functional implementations.

## Project structure

```text
backend/
  app/
    api/                 Versioned API router and health endpoint
    core/                Environment-backed settings
    schemas/             Shared request/response contracts
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

The API is available at `http://127.0.0.1:8000`; interactive OpenAPI documentation is at `http://127.0.0.1:8000/docs`. The implemented endpoint is `GET /api/v1/health`.

Run backend tests from `backend`:

```powershell
python -m pytest
```

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

1. **Project skeleton and contracts** — current phase; local apps, configuration, health check, and shared schemas.
2. **Synthetic document ingestion** — validated PDF/DOCX extraction with page/section metadata and parent/child chunks.
3. **Baseline local RAG** — embeddings, FAISS retrieval, grounded answers, and citations.
4. **Advanced retrieval experiments** — BM25/hybrid retrieval, reranking, query transformations, compression, and measured comparisons.
5. **Agent workflows** — LangGraph routing, policy comparison, and claim completeness analysis.
6. **Frontend integration and hardening** — complete user flows, validation, error handling, and prompt-injection defenses.
7. **Evaluation and demo readiness** — reproducible metrics, synthetic-only public demo, and deployment-limit verification.

Each phase will be verified before progressing. This scaffold intentionally does not implement document analysis before its ingestion and retrieval foundations exist.
