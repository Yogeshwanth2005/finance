# Active Roadmap & Technical Debt

## Replace Fin v2 with the `finance` app on MongoDB (COMPLETED — 2026-09-21)
Plan: `docs/superpowers/plans/2026-09-21-replace-project-with-finance-app.md`. Rollback point:
git tag `pre-finance-swap`.

| Task | Area | Status |
|---|---|---|
| 1 | Snapshot commit + tag `pre-finance-swap` | **Done** |
| 2 | Backend swapped to FastAPI/Motor; `lib/llm.py` Gemini adapter replaces the Emergent client | **Done** — adapter tests pass without network |
| 3 | Live-server suite green; `/auth/me` 500, default-password admin seed and dead index fixed | **Done** — 32 pytest tests passing, 0 server errors |
| 4 | Frontend swapped, `@emergentbase/*` plugins removed | **Done** — typecheck, lint (warnings only) and build exit 0; dev proxy verified |
| 5 | Root config, README, docs, second brain | **Done** |
| 6 | Browser pass through the core journey; delete leftovers | **Done** — register → profile → dashboard → insurance chat (general + document-grounded) → logout → admin login all clean, no console errors or failed `/api` calls. Deleted stale `.next/` and root `node_modules/`. `finance/` was **kept** on purpose as a backup of the original export (still git-ignored). Live Gemini streaming (Step 3b) not run: no key |

---

## Deployment: Render + Vercel + Atlas (IN PROGRESS — 2026-09-21)
Architecture: browser → Vercel (static frontend; `frontend/vercel.json` rewrites `/api/*`) → Render
`fin-api` (`render.yaml`, FastAPI) → Atlas `Cluster0`, database `fin`. One origin for the browser, so
cookies work and no CORS/cookie code changes were needed.

| Piece | State |
|---|---|
| Atlas `Cluster0` (free M0, ap-south-1) | **Live** as the prod DB. App user `fin-app` (readWrite on `fin`). Network Access: Render range `74.220.60.0/24` plus the dev machine's original `/32` |
| Render `fin-api` (`https://fin-api-dyki.onrender.com`) | **Live**, `/api/` healthy, reset token hidden. Free tier sleeps when idle (first request ~1 min) |
| Real admin | `yashwanthchallagundla2805@gmail.com`, created by the backend from `ADMIN_EMAIL` on first start |
| **Old admin `admin@surakshacfo.demo`** (`_id c8997c06-…`, public demo password) | **OPEN, SECURITY**: a seeded document I inserted via the Atlas connector earlier; the live login returned 200 with the public password when last checked. Delete that one document in Atlas (Browse Collections → `fin.users`), then confirm the login returns 401 |
| Vercel project | **Not confirmed.** `frontend/vercel.json` is pushed (root dir `frontend`, `npm install --legacy-peer-deps`, `/api` rewrite to the Render URL). After deploy, set `FRONTEND_URL`, `APP_URL`, `CORS_ORIGINS` on Render to the `https://…vercel.app` URL |
| Insurance chat UI | **Done**: fixed-height panel with its own scroll, auto-scrolls to the newest message (commit 364d420) |
| Favicon | **Open**: the tab icon files in `frontend/public/` (`favicon.svg/.ico/-16/-32`, `apple-touch-icon.png`) are the Emergent logo copied from the finance export; replace with a SurakshaCFO icon |
| LLM (Groq) | **Working locally; Render not set**: `lib/llm.py` calls Groq's free tier (default `openai/gpt-oss-120b`, pin one with `GROQ_MODEL`), replacing Gemini 2026-09-23 (briefly OpenRouter, by a mix-up: the key was always a Groq `gsk_…` key, which is why Google returned `API_KEY_INVALID`). Verified live through the running app 2026-09-23: streamed open-mode chat, plan extraction on upload, and a cited plan-named answer, none with `fallback`. Still to do: set `GROQ_API_KEY` on Render (until then answers use the fallback and open-mode chat stays off), and run the live-server suite with the key set. Limits: 1,000 requests/day and 8,000 tokens/min per model, so a burst falls back silently |
| Plan cards from documents | **Built, unverified live**: draft-extract on upload, admin review/publish dialog, `GET /plans`, click-through detail dialog. Checked with unit tests, a fake-DB route script and a browser run against a mock API. Still to do: run `tests/test_tscheck_plan_cards.py` against a live server, and try a real brochure with a live `GROQ_API_KEY` to judge extraction quality (a small synthetic plan extracted correctly 2026-09-23; only the first 16,000 characters of a long document are sent). Needs the key on Render to extract; without it admins enter cards by hand |
| Open-mode chat | **Built; one live run passed 2026-09-23** (a general question streamed with no `fallback`). Still to do: the live-server suite with the key set. `test_tscheck_general_question_profile_based` and `test_tscheck_plan_specific_retrieval_gating` assert the old gated behaviour and will fail against a keyed server; rewrite them once open mode is confirmed |

---

## Restore glide-path allocation and analysis tests (COMPLETED — 2026-09-23)
Restored from git history (`dddc580^`); reasoning and rejected alternatives in decisions/log.md, 2026-09-23.

| Task | Area | Status |
|---|---|---|
| 1 | `lib/{allocation,gap_analysis,insurance_matching,finance_config}.py` plus the 32 original tests in `tests/unit/` | **Done**: logic differs from the originals only on the import line |
| 2 | `risk_tolerance` / `investment_horizon_years` on `ProfileInput`, wizard step 4, i18n in four languages | **Done**: stored profiles default to moderate / 10 years |
| 3 | Dashboard allocation card reads `analysis.allocation` (from `compute_allocation`) | **Done**: browser-verified. It shows only after the emergency-fund and insurance-budget checks pass, as before |
| 4 | Direct `_analysis()` edge-case tests (`tests/unit/test_analysis_edge_cases.py`) | **Done**: 23 tests, 12/12 mutation checks caught. Full suite: 174 passing |

---

## Proposed / Not Yet Scoped
- **SIP management (CAS import, view-only)** — idea only. See decisions/log.md's
  2026-09-17/18 entries for the narrowing history before resuming. No design, schema or code exists.

## Known Tech Debt
- **Atlas loose ends.** Local dev still runs on the local `mongod` (`backend/.env`); prod uses Atlas
  (see Deployment). (1) The dev machine's egress IP rotates across several addresses, so a single-IP
  Network Access entry fails the TLS handshake (`TLSV1_ALERT_INTERNAL_ERROR`) intermittently; use a
  stable network or a temporary `0.0.0.0/0` with an expiry. (2) The `atlasAdmin` user from Atlas
  onboarding still exists; keep it off servers. Check that `fin-app` no longer holds
  `readWriteAnyDatabase`. (3) `~/Downloads/atlas-credentials.env` (and a copy in the repo root, now
  git-ignored via `*.env`) hold a plaintext password; move it to a password manager. (4) `.mcp.json`
  (read-only `mongodb-mcp-server`) is committed but needs `MDB_MCP_CONNECTION_STRING` and is unused
  while the claude.ai Atlas connector works. Its session expires; reconnect with `remote-atlas-connect`.
- **Upload limits on the live site are untested**: Vercel's proxy may cap request bodies below the
  10 MB document limit; if large PDFs fail only in prod, upload straight to the Render URL.
- **`finance/` folder still on disk**: it holds the original Emergent export, including a plaintext
  `EMERGENT_LLM_KEY` and `JWT_SECRET` in its `.env` files. Delete it once the backup is no longer
  needed (then drop the `finance` line from `.gitignore`).
- **Rotate secrets**: treat `EMERGENT_LLM_KEY` as compromised. decisions/log.md (2026-09-16) records real Supabase credentials in the root
  `.env`; revoke them if that project is still live. (`JWT_SECRET` was already regenerated during
  the swap.)
- **RAG is not semantic**: `lib/rag.py` `retrieve` loads up to 5,000 chunks into Python and does
  cosine there, over 128-dim hashed bag-of-words vectors. Upgrade path: Atlas Vector Search plus a
  real embedding model (a hosted one). Discussed with the user 2026-09-21, not started; existing
  documents would need re-uploading because old and new vectors are incompatible.
- **`login_attempts` never expire** (no TTL index) and are keyed per IP+email.
- **Password reset has no delivery channel.** `/auth/forgot-password` returns the token only when
  `EXPOSE_RESET_TOKEN=true` (local dev/tests); it is off by default and not in `render.yaml`, so on a
  public deployment users cannot reset a forgotten password until an email provider exists.
- **Google sign-in** is pending (no OAuth credentials).
- **`_plans()` is gone** (removed in commit 9fafa39): plan cards now come only from published
  documents. The old `DEMO_MODE` gate was never ported (see decisions/log.md, 2026-09-21).
- **`chat.py` swallows LLM errors without logging**: a bad key, a retired model or a Groq rate limit
  (429) all fall back to the deterministic answer with `fallback: true` and leave no log line, so they
  look like "no key". Consider a `logger.warning` in both `except Exception` blocks. (Streaming itself was
  verified live 2026-09-23.)
- **Pure tests in `tests/` root need a live server**: `tests/conftest.py`'s autouse session fixture logs
  in to `BACKEND_URL`, so `test_chat_context`, `test_plan_extract` and `test_reset_token_gate` (pure logic)
  error with `ConnectError` unless a backend is up. Only `tests/unit/` overrides it; the LLM adapter tests
  were moved there 2026-09-23. Moving the rest would let them run without Mongo or a server.
- **Admin URL upload is an SSRF hole**: `POST /admin/documents` with `source_url` fetches any http(s)
  address from the server, including `127.0.0.1` and other internal hosts. Admin-only, but block loopback,
  private and link-local ranges before a public deploy.
- **Frontend install**: needs `npm install --legacy-peer-deps` (npm 10.9.8 arborist crash on
  vitest's optional peers). `npm audit` reports 4 vulnerabilities (2 moderate, 2 high), untriaged.
- **Test hygiene**: tests never clean up (`tscheck-*` docs and users accumulate), and the language
  tests share one retest user, so parallel modules can race on `preferred_language`.
- **Playwright workspace** (`tests/`) has no specs yet.
- **`implementationplanv2.md`** is stale product history; remove it or archive it.
- **Restored engines are unwired** (2026-09-23). `lib/gap_analysis.py`, `lib/insurance_matching.py`
  and `select_fund_examples` (in `lib/allocation.py`) are tested but no live flow calls them. Live
  `_analysis()` uses different rules (15× combined income + liabilities, tiered ₹10–25L health, one
  `monthly_emi`), so wiring them means choosing one definition first. `HIGH_INTEREST_DEBT_THRESHOLD`
  in `lib/finance_config.py` was never referenced, in the original either.
- **`frontend/src/lib/sampleData.ts` is hand-written and stale.** For the sample profile it shows a
  term need of 4.3 Cr, score 43 and insurance budget ₹1,81,250; `_analysis()` returns 5.64 Cr, 25 and
  ₹1,23,950. Regenerate it from the engine.
- **Unsourced premium constants in `_analysis()`**: ₹17,500 per crore of term gap and ₹22,000 +
  ₹4,000 per dependent for health feed `investable_surplus`. The `max(10, …)` floor on the health need
  never applies (its smallest result is 12).
- **hi/te/ta labels** for risk tolerance and investment horizon (`i18n.ts`) have had no native review.
- **Allocation defaults are silent**: stored profiles without the two new fields read as moderate /
  10 years until the user re-saves the profile.
