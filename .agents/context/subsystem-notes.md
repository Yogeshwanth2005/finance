# Subsystem Notes & Load-Bearing Gotchas

## Backend tests depend on seeded data (`backend/tests/conftest.py`)
Five test modules log in as `retest.1789882160559@example.com` and ask about "Secure Life
Shield Policy" and "Retest Family Term Policy". They were written against a database that
already held them. `conftest.py` has a session-scoped autouse fixture that registers the user
(409 is fine) and uploads both documents as the admin if missing, so a fresh DB passes.
- With `-n 2`, both xdist workers seed at once; the fixture then deletes duplicate titles
  (keeps the oldest). Don't remove that dedupe.
- The seed text is tuned: cosine ranking must put Secure Life Shield before Retest Family Term
  for "Compare Secure ... vs Retest ..." queries (tests assert source order), and both texts
  carry a ₹ value (grounded-language tests assert one is quoted). Re-check ordering with
  `lib.rag.embed`/`cosine` before editing the text.
- If the retest user is missing, the failed logins pile up: 5 failures per IP+email lock the
  account for 15 minutes and every further login returns **429**, not 401. Clear with
  `db.login_attempts.delete_many({"identifier": {"$regex": "retest"}})`.
- The suite needs `ADMIN_EMAIL=admin@surakshacfo.demo` / `ADMIN_PASSWORD=DemoAdmin!2026` in
  `backend/.env` (the tests hardcode them).
- Tests never clean up: `tscheck-*` documents and users accumulate in the DB. Language tests
  share one retest user and PATCH its `preferred_language`, so parallel modules can race on it.

## Chat retrieval (`backend/routers/chat.py`, `backend/lib/rag.py`)
`_matching_document_ids` matches a question to documents by **title words** (>= 4 chars, minus
generic words) or an exact title. Two consequences:
- A content-only term in the question never triggers retrieval; the answer is "general" mode
  with sources `["Your financial profile"]`.
- Documents whose titles share words (e.g. `tscheck-chat-doc-*`) all match together, and
  `retrieve` keeps only the top 5 chunks by cosine. A test that must find one specific chunk
  should also put a distinctive content term in the question.
Comparison answers list sources in chunk-rank order, not question order.

## LLM seam (`backend/lib/llm.py`)
`_client()` is the patch point for tests (they stub it; nothing calls the network). Any
exception inside the streaming block in `chat.py` falls through to the deterministic fallback
with `"fallback": true`, so a bad key or model name degrades silently rather than erroring.
Real streaming has not been verified without a live `GEMINI_API_KEY`.

## Auth (`backend/lib/auth.py`, `backend/routers/auth.py`)
- `_public()` must not use `user.get("id", user["_id"])`: the default is evaluated eagerly and
  `get_current_user()` builds dicts with only `id`, which used to 500 `/auth/me`.
- Auth cookies are marked `Secure` when `FRONTEND_URL` starts with `https://`. Keep it `http://`
  locally or plain-HTTP clients won't send them.
- `/auth/forgot-password` returns `demo_token` only when `EXPOSE_RESET_TOKEN=true` (no email provider
  exists). Local `backend/.env` sets it so the reset pytest runs; without it that test skips. Never set
  it on a public deployment: it would let anyone reset any account, including the admin's.

## Frontend build
- `npm install` (plain) crashes npm 10.9.8 in `#loadPeerSet` on the optional peers of
  `vitest@4.1.10`. Use `npm install --legacy-peer-deps`. `yarn` is broken on this machine by
  `C:\hadoop\bin\libexec\yarn-config.sh`, so stay on npm.
- `vite.config.ts` aliases `lucide-react` and `recharts` to wrappers in `src/lib/`; the real
  packages are reachable as `lucide-react-upstream` / `recharts-upstream`. Import the plain
  names in app code, never the `-upstream` ones.

## Deployment (Render + Vercel + Atlas)
- **`SSL handshake failed ... TLSV1_ALERT_INTERNAL_ERROR` from pymongo means the caller's IP is not
  on Atlas Network Access.** It is not a credentials error (that is `OperationFailure: bad auth`,
  which arrives after the handshake). For Render add its Outbound ranges (service → Connect →
  Outbound); the dev machine's egress IP rotates across several addresses, so a `/32` is unreliable.
- `server.py` runs `seed_admin()` at startup, so an unreachable DB kills the app (`Exited with status
  3`), and `seed_admin` **creates a second admin** if `ADMIN_EMAIL` differs from an existing admin
  document. Never pre-insert an admin into prod; a leftover one with the demo password stays valid.
- After every deploy check `POST /api/auth/login` with the public demo admin password returns 401.
- `FRONTEND_URL` must be `https://` in prod or auth cookies are not marked `Secure`. `vercel.json`
  cannot read env vars, so the Render URL is hardcoded in its `/api` rewrite.
- Vercel's install command must be `npm install --legacy-peer-deps` (see Frontend build).
- The insurance chat panel has a fixed height (`h-[min(640px,75vh)]`) and its message list needs
  `min-h-0 flex-1 overflow-y-auto`; with only a `min-h-*` parent the list never scrolls and the page
  grows. Auto-scroll sets the list's `scrollTop`, not `scrollIntoView`, so the page does not jump.

## Running on Windows
`uvicorn` is started without `--reload` in this setup, so restart it after backend edits. Find
the process by port (`Get-NetTCPConnection -LocalPort 8001 -State Listen`) rather than by name.
