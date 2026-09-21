# Invariants, Tech Stack & File Map

## Tech Stack
- Frontend: Vite 8 + React 19 + TypeScript + Tailwind v4 + shadcn/ui, react-router-dom, TanStack Query, i18n for en/hi/te/ta (`frontend/src/`). Package manager is **npm** (`npm install --legacy-peer-deps`).
- Backend: Python 3.12 + FastAPI + Motor (async MongoDB) + Pydantic v2 (`backend/`)
- Database: MongoDB (`MONGO_URL`, `DB_NAME`). No migrations; indexes are declared in `backend/lib/db.py` `INDEXES` and applied at startup.
- Auth: JWT access/refresh tokens in HttpOnly cookies (PyJWT + bcrypt), roles `user` / `admin`. A `Bearer` header is also accepted (the tests use it).
- LLM: Gemini through `backend/lib/llm.py` (`google-genai`), optional. RAG uses local 128-dim hashed bag-of-words vectors stored in Mongo, cosine in Python.
- Testing: pytest against a live uvicorn (32 tests), Playwright workspace in `tests/` (no specs yet).
- Behaviour spec: `docs/SURAKSHACFO_SPEC.md`.

## Hard Invariants
1. **MongoDB only**: use `from lib.db import db`; never construct another `AsyncIOMotorClient`. No SQL/ORM/migration tooling (Supabase, SQLAlchemy, Alembic, Prisma) may come back.
2. **Every route is under `/api`**: one `APIRouter(prefix="/api")` in `server.py`. The frontend calls only relative `/api/...` paths through the Vite proxy to `http://localhost:8001`.
3. **String `uuid4` ids** (`_id` / `id`); never `ObjectId` in a response.
4. **`lib/llm.py` is the only module that knows about Gemini.** With no `GEMINI_API_KEY` chat falls back to a deterministic, localized answer; that path must keep working.
5. **Chat retrieval is title-gated**: documents are retrieved only when the question names an indexed plan/provider or asks for a comparison (`_matching_document_ids` in `routers/chat.py`). General questions are answered from the profile alone.
6. **`seed_admin` never invents credentials**: it seeds only when both `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set.
7. **Backend tests hit a live server** at `BACKEND_URL` (default `http://localhost:8001`). `pytest.ini` keeps `-n 2 --dist loadscope` and `asyncio_mode = auto`.
8. **Frontend typecheck is `npx tsc -b --noEmit`** (`npm run typecheck`); plain `tsc --noEmit` checks zero files.
9. **`.env*` stays git-ignored** (only `.env.example` is tracked). Never commit keys.

## File Map
- `backend/server.py` — app, CORS, index/admin startup, `api_router` mounting the four routers
- `backend/routers/auth.py` — register, login/lockout, session/me/refresh, settings, password change/reset
- `backend/routers/profile.py` — profile intake, dashboard analysis (`_analysis`), illustrative plans (`_plans`)
- `backend/routers/chat.py` — streaming insurance chat, title-gated retrieval, comparison tables, fallbacks
- `backend/routers/admin.py` — document upload/index/pause/delete, users, questions, overview
- `backend/lib/db.py` — shared Motor handle and `INDEXES`
- `backend/lib/auth.py` — password hashing, JWT cookies, `get_current_user`, `require_admin`, `seed_admin`
- `backend/lib/rag.py` — text extraction, chunking, hashed embeddings, `retrieve`
- `backend/lib/llm.py` — `llm_configured()`, `stream_answer()` (Gemini seam)
- `backend/models/` — Pydantic request/response models
- `backend/tests/` — pytest specs; `conftest.py` seeds the shared `retest.*` account and two plan documents
- `frontend/src/App.tsx` — routes only; pages in `frontend/src/pages/` (Home, Login, ResetPassword, Dashboard, Insurance, Account, AdminDocuments)
- `frontend/src/lib/` — `api.ts` typed fetch layer, `auth.tsx`, `i18n.ts`, plus `lucide-react.tsx` / `recharts.tsx` wrappers aliased in `vite.config.ts`
- `tests/` — Playwright workspace (`playwright.config.ts`, `fixtures/helpers.ts`, `e2e/`)
- `docs/SURAKSHACFO_SPEC.md`, `docs/test_credentials.md` — spec and demo admin login
