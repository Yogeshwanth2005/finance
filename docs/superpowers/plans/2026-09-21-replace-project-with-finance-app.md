# Replace Fin v2 With the `finance` App (MongoDB) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app in `finance/fintech-main` (SurakshaCFO: FastAPI + Motor/MongoDB backend, Vite/React 19 frontend) the project at the repo root, on MongoDB, and remove the Supabase/Prisma/Next.js remnants.

**Architecture:** Keep the repo root `D:\Fin` and its git history. `backend/` and `frontend/` are overwritten with the `finance` versions, `finance/` is kept read-only as the source until the swap is verified, then deleted. Two Emergent-platform couplings are removed on the way in: the `emergentintegrations` LLM client (not installable from public PyPI) and the `@emergentbase/*` Vite plugins.

**Tech Stack:** Python 3.12, FastAPI, Motor/PyMongo (MongoDB at `mongodb://localhost:27017`), PyJWT + bcrypt, `google-genai` (Gemini), Vite 8 + React 19 + TypeScript + Tailwind v4 + shadcn/ui, npm, pytest (live-server), Playwright.

**Spec:** `finance/fintech-main/memory/SPEC.md` (behavior source of truth after the swap; copied to `docs/SURAKSHACFO_SPEC.md` in Task 5).

## Global Constraints

- Database is **MongoDB** via Motor. No Supabase, SQLAlchemy, Alembic, Prisma or Postgres code or deps may remain.
- Every backend route is under `/api` (one `APIRouter(prefix="/api")` in `server.py`); the frontend only calls relative `/api/...` paths through Vite's proxy to `http://localhost:8001`.
- Documents use string `uuid4` ids (`_id` / `id`), never `ObjectId` in responses.
- Backend tests hit a **live** uvicorn at `BACKEND_URL` (default `http://localhost:8001`); `backend/pytest.ini` keeps `-n 2 --dist loadscope` and `asyncio_mode = auto`.
- Never copy `finance/fintech-main/backend/.env` or `frontend/.env`; `.env*` stays git-ignored. The current `backend/.env` is edited in place.
- Frontend package manager is **npm** (`yarn` on this machine is broken by `C:\hadoop\bin\libexec\yarn-config.sh`).
- `frontend` typecheck command is `npx tsc -b --noEmit` (plain `tsc --noEmit` checks zero files).
- Shell is Git Bash; venv interpreter is `backend/.venv/Scripts/python`. `SRC=finance/fintech-main` below.

## What was found (context for the executor)

| Area | Current repo | `finance/fintech-main` |
|---|---|---|
| Backend entry | none (no `server.py`, no routers) | `server.py` + `routers/{auth,profile,chat,admin}.py` |
| `backend/lib`, `backend/models` | **byte-identical to finance already** | same |
| `backend/app/` | Supabase REST client + `gap_analysis`/`allocation`/`insurance_matching` services (211 lines) | not present |
| DB | Supabase (`supabase==2.4.0`, SQLAlchemy, Alembic) | MongoDB (Motor), local `mongod` already listening on `127.0.0.1:27017` |
| Frontend | config files only, no `src/` | full app: 7 pages, shadcn/ui, i18n (en/hi/te/ta), 1,650 lines |
| Tests | none | 13 pytest files (~25 tests) + Playwright workspace |
| LLM | none | `emergentintegrations` → **not on PyPI** (`pip index versions` → "No matching distribution") |
| `backend/.env` | already has the finance key set (Mongo, JWT, admin, `EMERGENT_LLM_KEY`) | same |

Known defects in the finance code that this plan fixes: `/auth/me` returns 500 (eager `user["_id"]` default; a test currently *asserts* the 500), `seed_admin` silently creates a known-password admin when env is unset, requirements pull ~12 unused packages including `jq` (no Windows wheel).

## Open decisions (defaults chosen; say if you want otherwise)

1. **LLM provider** — default: Google `google-genai` with `GEMINI_API_KEY`, behind `lib/llm.py`. Alternative: keep Emergent's `EMERGENT_LLM_KEY` + private package index; then skip Task 2's adapter steps and add Emergent's `--extra-index-url` to `requirements.txt`. With no key set the chat already degrades to the deterministic, localized fallback, so the app runs either way.
2. **`DEMO_MODE` regulatory gate** — the old `CLAUDE.md` gate hid named insurers when `DEMO_MODE=false`. Finance's `routers/profile.py::_plans()` always shows named insurers with claim-settlement ratios. Default: **not ported** (finance is the new source of truth; portfolio demo). Say so if you want the gate back — it is a ~10-line change to `_plans()`.
3. **Secret hygiene** — `EMERGENT_LLM_KEY` and `JWT_SECRET` appear in plaintext in the shared `finance/` folder. Default: rotate the JWT secret in Task 2 and treat the Emergent key as compromised.

## File Structure

- `backend/server.py`, `routers/{auth,profile,chat,admin}.py` — copied from finance; `auth.py` gets a one-line fix, `chat.py` swaps its LLM call.
- `backend/lib/llm.py` — **new**: `llm_configured()`, `stream_answer(system_message, question)`; the only file that knows about Gemini.
- `backend/lib/auth.py`, `lib/db.py` — copied; small hardening edits.
- `backend/tests/` — copied 13 files + `test_llm_adapter.py`, `test_seed_admin.py` (new).
- `backend/requirements.txt` — rewritten lean.
- `frontend/**` — copied; `package.json` and `vite.config.ts` stripped of `@emergentbase/*`.
- `tests/` — Playwright workspace copied.
- Root: `.env.example`, `README.md`, `CLAUDE.md`, `.agents/**`, `docs/SURAKSHACFO_SPEC.md`, `.gitignore`.
- Deleted: `backend/app/`, `.next/`, root `node_modules/`, `finance/` (last three untracked; confirm before deleting).

---

### Task 1: Safety net

**Files:** none modified.

**Interfaces:**
- Produces: git tag `pre-finance-swap` to roll back to.

- [ ] **Step 1: Confirm the working tree change is safe to overwrite**

`backend/models/profile.py` is the only modified file, and `backend/models/` is identical to finance's.

Run: `cd /d/Fin && diff -rq backend/models finance/fintech-main/backend/models && diff -rq backend/lib finance/fintech-main/backend/lib && echo IDENTICAL`
Expected: `IDENTICAL` (no diff lines).

- [ ] **Step 2: Commit and tag the current state**

```bash
cd /d/Fin
git add backend/models/profile.py
git commit -m "chore: snapshot before replacing project with finance app"
git tag pre-finance-swap
```
Expected: commit succeeds; `git tag` lists `pre-finance-swap`.

- [ ] **Step 3: Confirm MongoDB is reachable**

Run: `cd /d/Fin && python -c "from pymongo import MongoClient; print(MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=3000).server_info()['version'])"`
Expected: a version string. If `ModuleNotFoundError`, do this step again after Task 2 Step 3 using `backend/.venv/Scripts/python`. If it times out, start `mongod` (port 27017 was listening at planning time) or point `MONGO_URL` at an Atlas cluster in Task 2 Step 9.

---

### Task 2: Backend swap with provider-neutral LLM adapter

**Files:**
- Delete: `backend/app/` (all of it), `backend/requirements.txt` (rewritten)
- Create: `backend/server.py`, `backend/routers/*.py`, `backend/pytest.ini`, `backend/tests/*` (copied), `backend/lib/llm.py`, `backend/tests/test_llm_adapter.py`
- Modify: `backend/routers/chat.py`, `backend/.env`

**Interfaces:**
- Produces: `lib.llm.llm_configured() -> bool`; `lib.llm.stream_answer(system_message: str, question: str) -> AsyncIterator[str]` (yields text deltas); `lib.llm._client()` (patch point for tests).
- Env: `GEMINI_API_KEY` (optional), `GEMINI_MODEL` (optional, default `gemini-3-flash-preview`).

- [ ] **Step 1: Remove the Supabase backend and copy the finance backend**

```bash
cd /d/Fin
git rm -r -q backend/app
SRC=finance/fintech-main
cp -r $SRC/backend/routers backend/
cp -r $SRC/backend/tests backend/
cp $SRC/backend/server.py $SRC/backend/pytest.ini backend/
find backend -name __pycache__ -prune -exec rm -rf {} +
ls backend backend/routers backend/tests | head -40
```
Expected: `server.py`, `pytest.ini`, `routers/{admin,auth,chat,profile,__init__}.py`, 14 files in `tests/`.

- [ ] **Step 2: Write the lean `backend/requirements.txt`**

Only packages the code imports (verified by grep: `httpx`, `pypdf`, `docx`, `pytest_asyncio`), plus runtime needs of FastAPI/Pydantic (`python-multipart` for `Form`/`UploadFile`, `email-validator` for `EmailStr`) and pytest-xdist (used by `pytest.ini`).

```
fastapi==0.141.1
uvicorn>=0.52.1
python-dotenv>=1.0.1
motor==3.7.1
pymongo>=4.9,<5
pydantic>=2.6.4
email-validator>=2.2.0
python-multipart>=0.0.9
pyjwt>=2.10.1
bcrypt>=4.0.1
tzdata>=2024.2
httpx>=0.27.0
pypdf==5.9.0
python-docx==1.2.0
google-genai>=1.0.0
pytest>=8.0.0
pytest-xdist>=3.6.0
pytest-asyncio>=0.24.0
```

- [ ] **Step 3: Create the venv and install**

```bash
cd /d/Fin/backend
python -m venv .venv
.venv/Scripts/python -m pip install -q -r requirements.txt
.venv/Scripts/python -c "import fastapi, motor, jwt, bcrypt, pypdf, docx, google.genai; print('deps ok')"
```
Expected: `deps ok`. (`.venv/` is already git-ignored via `backend/.venv/`.) Re-run Task 1 Step 3 with `.venv/Scripts/python` now if it was skipped.

- [ ] **Step 4: Write the failing adapter test**

Create `backend/tests/test_llm_adapter.py`:

```python
"""lib.llm is the only module that talks to Gemini; these tests never hit the network."""

import pytest

from lib import llm


def test_llm_configured_reflects_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert llm.llm_configured() is False
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert llm.llm_configured() is True


class _Chunk:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self):
        self.kwargs = None

    async def generate_content_stream(self, **kwargs):
        self.kwargs = kwargs

        async def gen():
            for text in ("Hello", None, " world"):
                yield _Chunk(text)

        return gen()


class _FakeClient:
    def __init__(self):
        self.aio = type("Aio", (), {"models": _FakeModels()})()


async def test_stream_answer_yields_only_non_empty_text(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(llm, "_client", lambda: fake)
    monkeypatch.setenv("GEMINI_MODEL", "test-model")

    deltas = [d async for d in llm.stream_answer("SYSTEM", "QUESTION")]

    assert deltas == ["Hello", " world"]
    assert fake.aio.models.kwargs["model"] == "test-model"
    assert fake.aio.models.kwargs["contents"] == "QUESTION"
    assert fake.aio.models.kwargs["config"].system_instruction == "SYSTEM"
```

- [ ] **Step 5: Run it to verify it fails**

Run: `cd /d/Fin/backend && .venv/Scripts/python -m pytest tests/test_llm_adapter.py -n 0 -q`
Expected: FAIL/ERROR — `ImportError: cannot import name 'llm' from 'lib'`. (`lib.db` needs `MONGO_URL`/`DB_NAME`; `lib/__init__` does not import it, so the import error is the only failure.)

- [ ] **Step 6: Implement `backend/lib/llm.py`**

```python
"""Single seam to the LLM provider. Swap providers by editing this file only."""

from __future__ import annotations

import os
from typing import AsyncIterator

DEFAULT_MODEL = "gemini-3-flash-preview"


def llm_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _client():
    from google import genai

    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


async def stream_answer(system_message: str, question: str) -> AsyncIterator[str]:
    from google.genai import types

    stream = await _client().aio.models.generate_content_stream(
        model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
        contents=question,
        config=types.GenerateContentConfig(system_instruction=system_message),
    )
    async for chunk in stream:
        if chunk.text:
            yield chunk.text
```

- [ ] **Step 7: Run the adapter test to verify it passes**

Run: `cd /d/Fin/backend && .venv/Scripts/python -m pytest tests/test_llm_adapter.py -n 0 -q`
Expected: `2 passed`.

- [ ] **Step 8: Point `chat.py` at the adapter**

In `backend/routers/chat.py` replace the import (line 12):

```python
from emergentintegrations.llm.chat import LlmChat, TextDelta, UserMessage
```
with (keep import order: put it after `from lib.auth import get_current_user` and `from lib.db import db`):
```python
from lib.llm import llm_configured, stream_answer
```

Replace `api_key = os.environ.get("EMERGENT_LLM_KEY", "")` / `if not api_key:` (lines ~201-202) with:
```python
        if not llm_configured():
```

Replace the `try:` block that builds `LlmChat` (lines ~217-223) with:
```python
        try:
            answer = ""
            async for delta in stream_answer(system_message, question.question):
                answer += delta
                yield _event({"type": "delta", "content": delta})
```
Leave the rest of the `try` body (insert of the advisor message, `done` event) and the `except Exception:` fallback unchanged. Then remove the now-unused `import os` if nothing else in the file uses it.

Run: `cd /d/Fin/backend && grep -n "emergent\|LlmChat\|TextDelta\|UserMessage\|os\.environ" routers/chat.py`
Expected: no output.

- [ ] **Step 9: Update `backend/.env`**

Edit in place (do not print values). Set/replace these keys; remove `EMERGENT_LLM_KEY`:

```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="fin"
CORS_ORIGINS="http://localhost:3000"
APP_URL="http://localhost:3000"
FRONTEND_URL="http://localhost:3000"
JWT_SECRET="<output of: python -c "import secrets; print(secrets.token_hex(32))">"
ADMIN_EMAIL="admin@surakshacfo.demo"
ADMIN_PASSWORD="DemoAdmin!2026"
GEMINI_API_KEY=""
```
`FRONTEND_URL` must be `http://` locally, otherwise cookies are marked `Secure` and plain-HTTP clients won't send them. `ADMIN_PASSWORD` must stay `DemoAdmin!2026` while the copied tests hardcode it. Leave `GEMINI_API_KEY` empty to test the fallback path; fill it to test streaming.

- [ ] **Step 10: Verify the app imports and boots**

```bash
cd /d/Fin/backend
.venv/Scripts/python -c "import server; print('import ok')"
```
Expected: `import ok`.

- [ ] **Step 11: Commit**

```bash
cd /d/Fin
git add -A backend
git status --short | grep -v "^[AMD]  backend/" ; echo "(nothing above = only backend staged)"
git commit -m "feat: replace Supabase backend with finance FastAPI/MongoDB app and Gemini adapter"
```

---

### Task 3: Live-server test suite green, plus known-bug fixes

**Files:**
- Modify: `backend/routers/auth.py:35` (`_public`), `backend/tests/test_tscheck_auth_flow.py:63-78`, `backend/lib/auth.py:99-120` (`seed_admin`), `backend/lib/db.py:20-29` (`INDEXES`)
- Create: `backend/tests/test_seed_admin.py`

**Interfaces:**
- Consumes: `lib.auth.seed_admin() -> None`, `lib.auth.db` (module attribute patched in test).
- Produces: `seed_admin` skips (logs a warning) when `ADMIN_EMAIL` or `ADMIN_PASSWORD` is unset.

- [ ] **Step 1: Start the backend and record a baseline**

```bash
cd /d/Fin/backend
.venv/Scripts/python -m uvicorn server:app --host 0.0.0.0 --port 8001 > ../scratch-uvicorn.log 2>&1 &
sleep 4
curl -s localhost:8001/api/
```
Expected: `{"message":"SurakshaCFO API ready"}`.

Run: `.venv/Scripts/python -m pytest -q 2>&1 | tail -30`
Expected: record the pass/fail list. `test_auth_me_endpoint_crashes_bug` should **pass** (it asserts the bug). Any other failure: use superpowers:systematic-debugging, and note whether it needs a live Gemini key (`GEMINI_API_KEY` empty means the deterministic fallback path). Only mark a test `skipif(not os.environ.get("GEMINI_API_KEY"))` if it truly needs live Gemini output — do not weaken assertions.

- [ ] **Step 2: Check the startup log for index errors**

Run: `grep -n "ensure_indexes" /d/Fin/scratch-uvicorn.log`
Expected on unmodified code: an `ERROR ensure_indexes(profiles.profile_id)` line (Mongo already owns the `_id` index). If there is none, skip the `profiles` half of Step 7.

- [ ] **Step 3: Flip the `/auth/me` test to expect the correct behavior (failing test first)**

Replace `test_auth_me_endpoint_crashes_bug` (lines 63-78 of `backend/tests/test_tscheck_auth_flow.py`) with:

```python
def test_auth_me_returns_current_user(client):
    email = _unique_email()
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Me Check", "email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == email
```

Run: `cd /d/Fin/backend && .venv/Scripts/python -m pytest tests/test_tscheck_auth_flow.py::test_auth_me_returns_current_user -n 0 -q`
Expected: FAIL with `assert 500 == 200` (uvicorn log shows `KeyError: '_id'`).

- [ ] **Step 4: Fix `_public`**

In `backend/routers/auth.py`, in `_public` (line 35) replace:

```python
        id=user.get("id", user["_id"]),
```
with:
```python
        id=user["id"] if "id" in user else user["_id"],
```

Uvicorn was started without `--reload`; restart it (kill the background job, rerun the Step 1 uvicorn command), then:

Run: `.venv/Scripts/python -m pytest tests/test_tscheck_auth_flow.py -n 0 -q`
Expected: `4 passed`.

- [ ] **Step 5: Write the failing `seed_admin` test**

Create `backend/tests/test_seed_admin.py`:

```python
"""seed_admin must never invent a default-password admin when env is unset."""

from lib import auth


class _NoDb:
    def __getattr__(self, name):
        raise AssertionError(f"db.{name} must not be touched when admin env is unset")


async def test_seed_admin_skips_without_password(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setattr(auth, "db", _NoDb())
    await auth.seed_admin()


async def test_seed_admin_skips_without_email(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.setenv("ADMIN_PASSWORD", "SomePassword!1")
    monkeypatch.setattr(auth, "db", _NoDb())
    await auth.seed_admin()
```

Run: `cd /d/Fin/backend && .venv/Scripts/python -m pytest tests/test_seed_admin.py -n 0 -q`
Expected: FAIL — `AssertionError: db.users must not be touched…` (current code falls back to `DemoAdmin!2026`).

- [ ] **Step 6: Fix `seed_admin`**

In `backend/lib/auth.py` add near the top imports `import logging` and after `REFRESH_DAYS = 7` add `logger = logging.getLogger(__name__)`. Replace the first two lines of `seed_admin`:

```python
    email = os.environ.get("ADMIN_EMAIL", "admin@surakshacfo.demo").lower()
    password = os.environ.get("ADMIN_PASSWORD", "DemoAdmin!2026")
```
with:
```python
    email = os.environ.get("ADMIN_EMAIL", "").lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        logger.warning("ADMIN_EMAIL/ADMIN_PASSWORD not set; skipping admin seed")
        return
```

Run: `.venv/Scripts/python -m pytest tests/test_seed_admin.py -n 0 -q`
Expected: `2 passed`.

- [ ] **Step 7: Drop dead index specs**

In `backend/lib/db.py` `INDEXES`, delete the `"status_checks"` entry (no route uses it) and, if Step 2 showed the error, the `"profiles"` entry (`_id` is always indexed). Result:

```python
INDEXES: dict[str, list[IndexModel]] = {
    "users": [IndexModel([("email", ASCENDING)], name="email_unique", unique=True)],
    "password_reset_tokens": [IndexModel([("expires_at", ASCENDING)], name="reset_expiry", expireAfterSeconds=0)],
    "login_attempts": [IndexModel([("identifier", ASCENDING)], name="login_identifier")],
    "rag_chunks": [IndexModel([("document_id", ASCENDING)], name="rag_document")],
    "rag_documents": [IndexModel([("created_at", DESCENDING)], name="rag_created")],
    "chat_messages": [IndexModel([("user_id", ASCENDING), ("created_at", ASCENDING)], name="chat_user_created")],
}
```

- [ ] **Step 8: Full suite against a fresh restart**

```bash
cd /d/Fin/backend
# stop the running uvicorn (kill the background job), then:
.venv/Scripts/python -m uvicorn server:app --host 0.0.0.0 --port 8001 > ../scratch-uvicorn.log 2>&1 &
sleep 4
grep -c "ERROR" ../scratch-uvicorn.log
.venv/Scripts/python -m pytest -q 2>&1 | tail -5
```
Expected: `0` errors in the log; pytest all passing (baseline failures from Step 1 resolved or explicitly skipped per Step 1's rule).

- [ ] **Step 9: Commit**

```bash
cd /d/Fin
rm -f scratch-uvicorn.log
git add backend
git commit -m "fix: /auth/me 500, refuse default-password admin seed, drop dead indexes"
```

---

### Task 4: Frontend swap without Emergent tooling

**Files:**
- Create/overwrite: `frontend/{index.html,package.json,components.json,vite.config.ts,tsconfig*.json,.oxlintrc.json}`, `frontend/public/**`, `frontend/src/**`
- Modify: `frontend/package.json`, `frontend/vite.config.ts`
- Delete: `frontend/yarn.lock` (not copied), `frontend/node_modules` if present

**Interfaces:**
- Consumes: backend on `http://localhost:8001` (Task 3), all routes under `/api`.
- Produces: dev server on `http://localhost:3000`; `npm run build`, `npm run typecheck`, `npm run lint` all clean.

- [ ] **Step 1: Copy the frontend (no `.env`, no `yarn.lock`)**

```bash
cd /d/Fin
SRC=finance/fintech-main
cp -r $SRC/frontend/src $SRC/frontend/public frontend/
cp $SRC/frontend/index.html $SRC/frontend/package.json $SRC/frontend/components.json \
   $SRC/frontend/vite.config.ts $SRC/frontend/tsconfig.json $SRC/frontend/tsconfig.app.json \
   $SRC/frontend/tsconfig.node.json $SRC/frontend/.oxlintrc.json frontend/
ls frontend frontend/src/pages
```
Expected: `src`, `public`, configs; 7 page files. `frontend/.env` and `.gitignore` already exist and are equivalent (the finance `.env` only contains a comment; the app has no `import.meta.env` usage).

- [ ] **Step 2: Remove the Emergent devDependencies from `frontend/package.json`**

Delete these two lines from `devDependencies`:

```json
    "@emergentbase/overlay": "https://assets.emergent.sh/npm/emergentbase-overlay-0.1.29.tgz",
    "@emergentbase/visual-edits": "https://assets.emergent.sh/npm/emergentbase-visual-edits-1.0.15.tgz",
```

- [ ] **Step 3: Simplify `frontend/vite.config.ts`**

Replace the whole file with (same aliases, proxy and pre-bundled deps; no Emergent plugins, no pod-only polling):

```ts
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: [
      { find: "@", replacement: path.resolve(__dirname, "./src") },
      // lucide 1.x dropped brand logos; src/lib/lucide-react.tsx restores them on top of the real package.
      { find: /^lucide-react$/, replacement: path.resolve(__dirname, "./src/lib/lucide-react.tsx") },
      { find: "lucide-react-upstream", replacement: path.resolve(__dirname, "./node_modules/lucide-react") },
      // recharts 3's Tooltip callback types reject common annotations; src/lib/recharts.tsx adapts them.
      { find: /^recharts$/, replacement: path.resolve(__dirname, "./src/lib/recharts.tsx") },
      { find: "recharts-upstream", replacement: path.resolve(__dirname, "./node_modules/recharts") },
    ],
  },
  optimizeDeps: {
    include: [
      "@base-ui/react/button",
      "@base-ui/react/checkbox",
      "@base-ui/react/dialog",
      "@base-ui/react/input",
      "@base-ui/react/menu",
      "@base-ui/react/merge-props",
      "@base-ui/react/popover",
      "@base-ui/react/select",
      "@base-ui/react/tabs",
      "@base-ui/react/use-render",
      "@tanstack/react-query",
      "class-variance-authority",
      "clsx",
      "date-fns",
      "@icons-pack/react-simple-icons",
      "lucide-react-upstream",
      "motion/react",
      "next-themes",
      "react",
      "react-day-picker",
      "react-dom/client",
      "react-is",
      "react-router-dom",
      "recharts-upstream",
      "sonner",
      "tailwind-merge",
    ],
  },
  server: {
    host: true,
    port: 3000,
    // The /api proxy convention: frontend code calls relative /api/*, never an absolute backend URL.
    proxy: {
      "/api": { target: "http://localhost:8001", changeOrigin: true },
    },
  },
});
```

- [ ] **Step 4: Install with npm and check it resolves**

```bash
cd /d/Fin/frontend
npm install 2>&1 | tail -15
```
Expected: completes and writes `package-lock.json`. If a pinned version in `package.json` (`typescript 7.0.2`, `vite 8.1.5`, etc.) fails to resolve, do not guess: run `npm view <pkg> versions --json | tail -5`, pick the nearest published version, and record the change in the commit message.

- [ ] **Step 5: Typecheck, lint, build**

```bash
cd /d/Fin/frontend
npm run typecheck && npm run lint && npm run build
```
Expected: all three exit 0. Fix any errors caused by the vite.config change (unused `import`s etc.) — do not touch page code unless the error is in it.

- [ ] **Step 6: Start the dev server and check the proxy**

```bash
cd /d/Fin/frontend && npm run dev > ../scratch-vite.log 2>&1 &
sleep 5
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/
curl -s http://localhost:3000/api/
```
Expected: `200` and `{"message":"SurakshaCFO API ready"}` (backend from Task 3 must still be running).

- [ ] **Step 7: Commit**

```bash
cd /d/Fin
rm -f scratch-vite.log
git add frontend
git commit -m "feat: replace frontend with finance React app, drop Emergent vite plugins"
```

---

### Task 5: Root config, docs and second brain

**Files:**
- Create/Modify: `.env.example`, `README.md`, `docs/SURAKSHACFO_SPEC.md`, `CLAUDE.md`, `.agents/context/*.md`, `.agents/decisions/log.md`, `.agents/projects/active-backlog.md`, `tests/` (Playwright workspace)
- Modify: `.gitignore`

**Interfaces:**
- Produces: documentation that matches the code; `CLAUDE.md` routing points at real files.

- [ ] **Step 1: Copy the Playwright workspace and the spec**

```bash
cd /d/Fin
SRC=finance/fintech-main
cp -r $SRC/tests ./tests
rm -rf tests/node_modules tests/yarn.lock
cp $SRC/memory/SPEC.md docs/SURAKSHACFO_SPEC.md
cp $SRC/memory/test_credentials.md docs/test_credentials.md
```
Expected: `tests/{package.json,playwright.config.ts,fixtures/helpers.ts,e2e/.gitkeep}` and updated spec.

- [ ] **Step 2: Rewrite `.env.example` for MongoDB**

```
# Backend (backend/.env)
MONGO_URL="mongodb://localhost:27017"
DB_NAME="fin"
CORS_ORIGINS="http://localhost:3000"
APP_URL="http://localhost:3000"
FRONTEND_URL="http://localhost:3000"   # https:// makes auth cookies Secure
JWT_SECRET="replace-with: python -c 'import secrets; print(secrets.token_hex(32))'"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="replace-me"            # admin is seeded only when both are set
GEMINI_API_KEY=""                      # optional; empty = deterministic fallback answers
# GEMINI_MODEL="gemini-3-flash-preview"
```

- [ ] **Step 3: Write a root `README.md`**

Base it on `finance/fintech-main/README.md` but keep only: layout, running (`uvicorn` on 8001, `npm run dev` on 3000), the `/api` proxy convention, MongoDB ids/`lib.db` rule, testing (pytest live-server + Playwright), env table from Step 2. Drop the "Pod conventions", supervisor, `/root/.venv` and `yarn` sections, and every mention of Emergent and "farm-ts". Add the disclaimer line: *Educational estimates only; not financial, tax, medical or insurance advice.*

- [ ] **Step 4: Update `.gitignore`**

Remove the now-stale lines `/.next/`, `next-env.d.ts`, `.vercel`, the Prisma-skills comment block; keep `.env*`, `backend/.venv/`, `frontend/node_modules/`, `frontend/dist/`, `__pycache__/`. Leave the `finance` line until Task 6 Step 4 removes the folder, then delete that line too.

- [ ] **Step 5: Rewrite `CLAUDE.md` and sync `.agents/`**

`CLAUDE.md` currently describes the old stack (Prisma/DB calls, `DEMO_MODE` gate, "deterministic no-ML gap analysis", `implementationplanv2.md`). Rewrite the header paragraph and routing table to: FastAPI + Motor/MongoDB + React app implementing `docs/SURAKSHACFO_SPEC.md`; keep the "How to Work Efficiently" and "After Any Change" sections verbatim. Then follow `.claude/commands/second-brain-close.md` to update `.agents/context/stack-and-rules.md` (new stack, file map, invariants from Global Constraints), `.agents/decisions/log.md` (append: "2026-09-21 replaced Supabase/Prisma v2 with finance app on MongoDB; Emergent LLM client → `lib/llm.py`; DEMO_MODE gate not ported"), and `.agents/projects/active-backlog.md` (remove stale v2 items; add the debt list in Task 6 Step 5). Do not read the whole `.agents/` tree — open only the file being edited.

- [ ] **Step 6: Commit**

```bash
cd /d/Fin
git add -A .env.example README.md .gitignore CLAUDE.md .agents docs tests
git commit -m "docs: document finance app on MongoDB, sync second brain"
```

---

### Task 6: End-to-end verification and cleanup

**Files:**
- Delete (with confirmation): `finance/`, `.next/`, root `node_modules/`, `implementationplanv2.md` (optional, stale)

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Fresh-clone-style check of both processes**

Stop any running dev servers, then:

```bash
cd /d/Fin/backend && .venv/Scripts/python -m uvicorn server:app --port 8001 &
cd /d/Fin/frontend && npm run dev &
sleep 6
# happy path + negatives, asserting status
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:3000/api/auth/login -H 'content-type: application/json' -d '{"email":"admin@surakshacfo.demo","password":"DemoAdmin!2026"}'
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:3000/api/auth/login -H 'content-type: application/json' -d '{"email":"admin@surakshacfo.demo","password":"wrong-password-1"}'
curl -s -o /dev/null -w "%{http_code}\n" localhost:3000/api/profile
```
Expected: `200`, `401`, `401`.

- [ ] **Step 2: Full backend suite**

Run: `cd /d/Fin/backend && .venv/Scripts/python -m pytest -q 2>&1 | tail -5`
Expected: all pass.

- [ ] **Step 3: One browser pass through the core journey**

Use the Playwright or chrome-devtools MCP against `http://localhost:3000`: register a new user → complete the 4-step profile → land on `/dashboard` (protection score + surplus card `mutual-fund-allocation-card` visible) → `/insurance` and send "why does term insurance matter?" (expect a streamed answer; with an empty `GEMINI_API_KEY` the profile-based deterministic answer) → log out → log in as admin and confirm redirect to `/admin/documents`. Screenshot the dashboard and the admin page.
Expected: no console errors, no failed `/api` requests other than the deliberate negatives.

- [ ] **Step 3b: If `GEMINI_API_KEY` is available, verify real streaming**

Set it in `backend/.env`, restart the backend, upload a small TXT titled "Test Plan Alpha" in `/admin/documents`, then ask "Tell me about Test Plan Alpha". Expected: SSE deltas arrive incrementally and the response is grounded in the uploaded text with the source title cited.

- [ ] **Step 4: Confirm-then-delete the leftovers**

Ask the user before running anything destructive; these are untracked/ignored, so there is no git recovery. Show sizes first (`du -sh finance .next node_modules`).

```bash
cd /d/Fin
git status --short   # must be clean before deleting
rm -rf finance .next node_modules
```
Then remove the `finance` line from `.gitignore`, and optionally `git rm implementationplanv2.md`. Everything remains recoverable from the `pre-finance-swap` tag except the untracked `finance/` folder — keep a copy elsewhere if you may want the original Emergent export.

- [ ] **Step 5: Record known tech debt in `.agents/projects/active-backlog.md`**

Append (facts confirmed while planning):
- RAG retrieval loads up to 5,000 chunks into Python and does cosine similarity there (`lib/rag.py:63`); 128-dim hashed bag-of-words "embeddings" are not semantic. Upgrade path: Atlas Vector Search + a real embedding model.
- `login_attempts` documents never expire (no TTL) and are keyed per IP+email.
- `/auth/forgot-password` returns the reset token in the response (demo-only until an email provider exists).
- Google sign-in is pending (no OAuth credentials).
- `_plans()` hard-codes named insurers and claim-settlement ratios; `DEMO_MODE` gate not ported.
- Rotate `EMERGENT_LLM_KEY` (it was in the shared folder) and any Supabase keys that were in the old `backend/.env`.

- [ ] **Step 6: Final commit**

```bash
cd /d/Fin
git add -A
git commit -m "chore: remove finance staging folder and stale Next.js artifacts; record tech debt"
```
Expected: `git status` clean; `git log --oneline -6` shows the commits from Tasks 1–6.

---

## Self-review

- **Spec coverage:** auth/roles, profile → dashboard, insurance chat (RAG, comparison tables, localization), admin documents, account settings — all come across in Tasks 2 and 4 verbatim from finance; Task 6 Step 3 exercises each flow. MongoDB retained (Global Constraints, Task 2 Step 9, Task 3 Step 7). The three behaviors that changed (LLM client, `/auth/me`, admin seeding) each have a failing test first.
- **Placeholders:** none; the only unknown is the Task 3 Step 1 baseline result, which is unknowable before the code runs, and the step states how to treat every outcome.
- **Type/name consistency:** `llm_configured`, `stream_answer`, `_client` used identically in the test, the module and `chat.py`; `seed_admin` env names match `.env` and `.env.example`; port 8001/3000 consistent with `vite.config.ts` and `conftest.py`.
