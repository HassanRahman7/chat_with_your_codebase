# Codebase AI - Backend

FastAPI backend for repository ingestion, indexing, retrieval and grounded
answers with validated citations.

## Requirements

- Python 3.11+
- PostgreSQL 15+ (local service is fine)
- Git on `PATH` (used from Phase 1 onward)

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --only-binary=:all: -r requirements.txt -c constraints.txt
```

`constraints.txt` pins the versions verified to work with Windows Smart App
Control enabled. Do not upgrade these packages unpinned: newly published native
wheels can be blocked by SAC until their cloud reputation propagates. If a new
version is blocked, pin the previous known-good version instead of disabling
SAC.

### 1. Environment

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set:

- `DATABASE_URL` - your local PostgreSQL password
- `GEMINI_API_KEY` - your Google Gemini API key

### 2. Create the database

Using the PostgreSQL `psql` binary (adjust the path if needed):

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE codebase_ai;"
```

### 3. Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

`GET /api/health` performs real PostgreSQL and ChromaDB connectivity checks and
returns `503` with `status: degraded` when a dependency is unavailable.

## Migrations

Alembic is the only schema-change mechanism. Do **not** use
`Base.metadata.create_all()`.

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

The initial migration is created in Phase 1 together with the first models, so
there are no throwaway migrations.

## Tests

```powershell
pytest
```

## Structure

```text
app/
  api/
    error_handlers.py   # standard {"error": {...}} envelope
    middleware.py       # request IDs
    routers/            # thin HTTP routers
  database/             # SQLAlchemy base/session + ChromaDB adapter
  schemas/              # Pydantic API contracts
  services/             # application/domain logic
  utils/                # logging and shared helpers
  config.py             # centralized typed settings
  main.py               # app factory
storage/                # controlled local storage (git-ignored contents)
tests/                  # unit and integration tests
```
