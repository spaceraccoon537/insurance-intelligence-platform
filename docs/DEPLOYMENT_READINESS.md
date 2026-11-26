# Deployment readiness

## Status

The application is a local-first prototype. The retrieval benchmark in
`backend/app/evaluation/retrieval_cases.json` is synthetic-only and runs locally.
There is no public demo deployment or production hosting configuration in this
phase.

## Frontend hosting boundary

The React/Vite frontend can be built as static assets with `npm run build` from
`frontend`; Vite writes them to `frontend/dist`. A static host such as Cloudflare
Pages can serve those assets, but the development-only `/api` proxy in
`frontend/vite.config.ts` does not provide an API in production. Without a
separately hosted compatible API, the deployed frontend cannot perform document
ingestion, retrieval, comparison, or claim review.

## Backend runtime boundary

The FastAPI backend uses local Python packages and a SQLite database at
`INSURANCE_DATABASE_PATH` (by default, `backend/data/local/documents.sqlite3`).
The configured database is a local filesystem path; no remote database,
durable object storage, serverless Python adapter, or edge-compatible retrieval
implementation is configured. Cloudflare Pages serves the frontend and is not
the deployment target for this conventional FastAPI service. Do not assume the
backend, local SQLite persistence, or retrieval dependencies can run on a
Workers runtime without a separately designed and tested adapter.

## Data boundary and verification

- Use only fabricated policy and claim text in demos and evaluation fixtures.
- Do not upload real policyholder, policy, or claim documents to a public demo.
- The ingestion API does not retain original files, but extracted text and
  metadata are persisted in local SQLite; this is not a public-demo privacy
  boundary or a substitute for hosted storage controls.
- The current deployment build check is `npm run build` in `frontend`.
- The local backend check is `python -m pytest` in `backend`.
- Run the deterministic retrieval benchmark with
  `python -m app.evaluation` in `backend`. Its JSON report includes the dataset
  SHA-256, retrieval strategies, and precision@k, recall@k, MRR@k, and nDCG@k.

The small hand-labeled benchmark is a regression/smoke baseline, not evidence
of production retrieval quality or insurance-domain accuracy. Treat changes in
its scores as comparisons on this fixed synthetic dataset only.

A public demo remains deferred until a synthetic-only frontend experience and a
compatible API/data adapter have been designed, hosted, and tested separately.
