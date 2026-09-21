# Fin (SurakshaCFO)

A personal-finance and insurance-gap demo: a family enters its finances, gets a protection
score and a mutual-fund allocation estimate, browses insurance plan cards, and asks an
advisor questions that are answered from its profile and admin-indexed policy documents.
Behaviour is specified in [docs/SURAKSHACFO_SPEC.md](docs/SURAKSHACFO_SPEC.md).

> Educational estimates only; not financial, tax, medical or insurance advice.

**FastAPI + MongoDB** backend behind a **Vite + React 19 + TypeScript** frontend, joined by a
small typed fetch layer over `/api`.

## Layout

```
backend/   FastAPI + Motor (async MongoDB) + Pydantic v2
  server.py    app, CORS, single APIRouter(prefix="/api")
  routers/     auth, profile, chat, plans, admin
  lib/         db, auth (JWT cookies + bcrypt), rag (local hashed vectors), llm (Gemini seam),
               chat_context (open-mode prompt helpers), plan_extract (document -> plan card), dates
  models/      Pydantic request/response models
  tests/       pytest, run against a live server
frontend/  Vite + React 19 + Tailwind v4 + shadcn/ui, i18n (en / hi / te / ta)
  src/pages/   Login, ResetPassword, Home, Dashboard, Insurance, Account, AdminDocuments
  vercel.json  build settings and the /api rewrite to the Render backend
tests/     Playwright e2e workspace
docs/      spec and demo credentials
render.yaml  Render Blueprint for the backend
```

## Features

- **Dashboard**: protection score, insurance gap and a mutual-fund allocation estimate from the
  family profile.
- **Insurance advisor**: streamed chat in English, Hindi, Telugu or Tamil, with cited sources.
  Chat history is per session: it is deleted on login and logout.
- **Plan cards**: uploading a policy document as admin indexes it for chat and drafts a plan
  card from it (`lib/plan_extract.py`). The admin reviews and edits the draft in the
  documents page, then publishes it. `GET /api/plans` and the Insurance page show only
  published cards. Fields the document does not state are shown as "Not stated in the
  document" rather than guessed.
- **Admin**: `/admin/documents` manages documents (upload, enable/disable, delete, plan-card
  review); the admin API also serves an overview, users and the questions asked.

## Running

Needs Python 3.12, Node 22, and a MongoDB on `localhost:27017`. Copy `.env.example` to
`backend/.env` and fill it in (see [Configuration](#configuration)).

```bash
# backend  ->  http://localhost:8001
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # Windows; .venv/bin/python elsewhere
.venv/Scripts/python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# frontend  ->  http://localhost:3000
cd frontend
npm install --legacy-peer-deps      # plain `npm install` crashes npm 10's peer resolver on vitest
npm run dev
```

Frontend checks: `npm run typecheck` (this is `tsc -b --noEmit`; plain `tsc --noEmit` checks
zero files), `npm run lint`, `npm run build`.

## The `/api` proxy convention

Every backend route lives under `/api`, and the Vite dev server proxies `/api/*` to
`http://localhost:8001`. Frontend code always calls a **relative** path such as `/api/profile`,
never an absolute backend URL. Never hang a route directly off `app` in `server.py`; it would
land outside `/api` and the proxy would not reach it.

## Backend conventions

- **MongoDB**: import the shared handle with `from lib.db import db`. Never build another
  `AsyncIOMotorClient`. Indexes are declared in `lib/db.py` (`INDEXES`) and applied at startup.
- **Ids**: documents use string `uuid4` ids (`_id` / `id`), never `ObjectId`, which is not
  JSON-serialisable.
- **LLM**: `lib/llm.py` is the only module that talks to Gemini. With no `GEMINI_API_KEY` the
  chat degrades to a deterministic, localised fallback answer, so the app runs without a key.
- **Chat has two modes.** With `GEMINI_API_KEY` set and no plan named in the question, chat runs
  in *open mode*: Gemini gets the profile, recent history and the best chunks across all
  enabled documents, and decides what is relevant. Otherwise retrieval is title-gated:
  documents are only retrieved when the question names an indexed plan/provider or asks for a
  comparison, and general questions are answered from the profile alone. Answers stay within
  personal finance and insurance (`SCOPE_RULES` in `lib/chat_context.py`).
- **Plan cards are drafts until published.** `plan_extract.py` treats the LLM's JSON as
  untrusted, cleans every field, and never blocks or fails an upload.
- **Admin** is seeded only when both `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set.

## Testing

**Backend (pytest)** hits a live uvicorn at `BACKEND_URL` (default `http://localhost:8001`), so
start the backend first:

```bash
cd backend && .venv/Scripts/python -m pytest
```

`backend/pytest.ini` runs with `-n 2 --dist loadscope` (pytest-xdist) and
`asyncio_mode = auto`; pass `-n 0` for serial runs. `tests/conftest.py` seeds the shared
`retest.*` account and two plan documents that several tests assume. A few tests
(`test_llm_adapter`, `test_chat_context`, `test_plan_extract`) exercise pure helpers and do not
need the server. The demo admin login the
tests use is in [docs/test_credentials.md](docs/test_credentials.md) and needs the matching
`ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env`.

**Frontend (Playwright)**: specs go in `tests/e2e/`; `playwright.config.ts` and
`fixtures/helpers.ts` are the shared setup.

## Configuration

`backend/.env` (git-ignored; template in [.env.example](.env.example)):

| Variable | Purpose |
|---|---|
| `MONGO_URL`, `DB_NAME` | MongoDB connection and database name |
| `CORS_ORIGINS`, `APP_URL`, `FRONTEND_URL` | Allowed origins and app URLs. Keep `FRONTEND_URL` on `http://` locally, or auth cookies are marked `Secure` and plain-HTTP clients will not send them |
| `JWT_SECRET` | Signs session tokens |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Seeded admin account; skipped if either is unset |
| `GEMINI_API_KEY` | Optional; empty means deterministic fallback answers |
| `GEMINI_MODEL` | Optional; defaults to `gemini-3-flash-preview` |
| `EXPOSE_RESET_TOKEN` | Set to `true` only for local demos/tests. It makes `/auth/forgot-password` return the reset token; never set it in production |

## Deploying the backend (Render)

`render.yaml` defines the FastAPI service (root `backend`, `uvicorn server:app --host 0.0.0.0 --port $PORT`,
health check `/api/`). In Render choose **New → Blueprint**, pick this repo, and fill in the prompted
secrets: `MONGO_URL` (an Atlas user with `readWrite` on `fin`, not an admin user), `ADMIN_EMAIL`,
`ADMIN_PASSWORD` (not the public demo password), and the `https://` URLs for `FRONTEND_URL`, `APP_URL`
and `CORS_ORIGINS`. `JWT_SECRET` is generated. In Atlas, allow Render's outbound IPs under
**Network Access**. The frontend is deployed separately and proxies `/api/*` to the Render URL, so the
browser sees a single origin and cookies work without CORS changes.

## Deploying the frontend (Vercel)

Point a Vercel project at `frontend/`. `frontend/vercel.json` sets `npm install --legacy-peer-deps`,
`npm run build`, the `dist` output, the `/api/*` rewrite to the Render URL, and an SPA fallback to
`index.html`. If the Render service URL changes, update the rewrite destination there.
