# Codebase AI

Chat with any codebase: submit a public GitHub repository, ask natural-language
questions, and receive answers grounded in real source files with clickable,
validated line-level citations.

**Status:** Phase 0 — foundation (React ↔ FastAPI health check working).

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite, Tailwind CSS, shadcn-style primitives, Lucide |
| Backend | Python + FastAPI, Pydantic, SQLAlchemy 2.x, Alembic |
| Relational data | PostgreSQL |
| Vector search | ChromaDB |
| Parsing | Tree-sitter (Phase 2) |
| Embeddings | Sentence Transformers, `BAAI/bge-small-en-v1.5` (Phase 3) |
| LLM | Google Gemini via `google-genai` (Phase 4) |

## Repository layout

```text
backend/    FastAPI application, tests, local storage
frontend/   React + Vite application
PRD.md
Design.md
Architecture.md
Database.md
API.md
```

## Quick start

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --only-binary=:all: -r requirements.txt -c constraints.txt
Copy-Item .env.example .env   # fill in DATABASE_URL and GEMINI_API_KEY
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE codebase_ai;"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173. The landing page shows the live backend status from
`GET /api/health`.

## Phase status

- [x] Phase 0 — Foundation: app scaffolding, config, CORS, error envelope,
      request IDs, PostgreSQL/ChromaDB connectivity, Alembic scaffold, health
      endpoint, design tokens and landing page.
- [x] Phase 1 — Repository ingestion: PostgreSQL models and initial Alembic
      migration, GitHub URL validation, asynchronous shallow clone, repository
      and indexing-status APIs, landing URL form and repository dashboard.
- [x] Phase 2 — Parsing and chunking: Tree-sitter Python/JavaScript parsers,
      deterministic file scanning with security exclusions, normalized symbols,
      syntax-aware chunks, fallback chunking, and status/manifest reporting.
- [x] Phase 3 — Embeddings and vector search: Sentence Transformer (BGE)
      embedding service, ChromaDB vector store with repository + index version
      filtering, end-to-end indexing worker (embed → store → verify → activate),
      and repository READY state.
- [x] Phase 4 — RAG and citations: Gemini LLM integration via REST API,
      repository-scoped retrieval with source_id validation, citation integrity
      (no model-generated paths/line numbers), insufficient-evidence handling,
      conversation/message persistence, and chat/conversation APIs.
- [ ] Phase 5 — File and chat UI
- [ ] Phase 3 — Embeddings and vector search
- [ ] Phase 4 — RAG and citations
- [ ] Phase 5 — File and chat experience
- [ ] Phase 6 — Reliability and evaluation
- [ ] Phase 7 — Stretch features (deferred)

## Non-negotiable rules

1. Citations always come from trusted backend retrieval metadata.
2. Retrieval is scoped to one repository and its active index version.
3. Repository code is never executed.
4. Secrets and absolute server paths never reach the browser.
5. A failed new index never replaces a valid active index.
