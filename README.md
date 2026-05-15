# Text-to-SQL Web Chatbot Skeleton

Project scaffold for a multi-agent Text-to-SQL chatbot:

- `frontend`: web chat UI (React + Vite)
- `backend`: API service (FastAPI)
- `ai`: agent pipeline stubs (rewriter, retrieval, routing, SQL, execution, answer)

## Quick Start

### 1) Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend defaults to `http://localhost:5173` and calls backend at `http://localhost:8000`.

## Docker Setup

From `text_to_sql` root:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Postgres: `localhost:5432` (`text2sql` / `text2sql`)

## Frontend localhost

Run only frontend on localhost (without Docker):

```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173`.

Notes:

- Frontend uses Vite proxy `/api` -> `http://localhost:8000`.
- Ensure backend is running on port `8000`.

## Phase 2 - Query Rewriter Test

1. Set OpenRouter key:

```bash
copy .env.example .env
```

Then edit `.env` and set `OPENROUTER_API_KEY`.

2. Install/update backend dependencies:

```bash
cd backend
.venv\Scripts\python -m pip install -r requirements.txt
```

3. Run Query Rewriter test:

```bash
cd ..
backend\.venv\Scripts\python ai\tests\test_query_rewriter.py
```

Expected format:

- Input: `Top 3 sinh vien GPA cao nhat CNTT`
- Output: rewritten query clear enough for SQL generation.

### OpenRouter TLS / SSL errors on Windows

If you see `CERTIFICATE_VERIFY_FAILED`:

1. **Corporate proxy / custom CA** — set `SSL_CERT_FILE` (or `REQUESTS_CA_BUNDLE`) in `.env` to a PEM file that includes your organisation’s root certificate.
2. **Local debugging only** — set `OPENROUTER_SSL_VERIFY=false` in `.env` to skip certificate verification (insecure; do not ship to production).

By default the client uses the `certifi` CA bundle.
