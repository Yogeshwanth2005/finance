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

## Dashboard restructure: status → invest → insurance (COMPLETED — 2026-09-23)
Reasoning and rejected alternatives in decisions/log.md, 2026-09-23. The layout landed in the same commit as the glide-path work above.

| Task | Area | Status |
|---|---|---|
| 1 | Page order: headline metrics → score ring + cashflow → "What to do next" → 8-KPI grid → formula card | **Done**: typecheck clean |
| 2 | Investment card gated emergency gap → insurance affordability → monthly split (`investable_surplus ÷ 12`) | **Done**: the split is the glide-path `analysis.allocation` (Equity/Debt/Gold buckets), not named funds. The card now lives on `/investments` (see "Investments page" below) |
| 3 | Insurance status card: held vs recommended vs gap for term and health, premium budget, link to `/insurance` with the published-plan count | **Done**: adds a `GET /plans` query to the dashboard |

---

## Fund explorer and inflation-goal check (COMPLETED — 2026-09-24)
Plan: `docs/superpowers/plans/2026-09-24-fund-explorer-and-goal-check.md` (local only, `docs/` is git-ignored).
It supersedes the 2026-09-23 curated 15-fund idea: AMFI's file gives category and fund house for every scheme,
so the explorer lists real Direct Growth funds instead of a hand-picked shortlist. Reasoning, real counts and
assumptions in decisions/log.md, 2026-09-24.

| Task | Area | Status |
|---|---|---|
| 1–3 | `compute_equity_split` and `compute_goal_check` in `lib/allocation.py`; `analysis.equity_split` and `analysis.goal_check` on `/profile` | **Done**: `analysis.allocation` unchanged; constants editable in `lib/finance_config.py` |
| 4 | Investment card shows Large / Mid / Small cap, Debt, Gold plus a goal line and a crash line (`GoalCheckLines`, `lib/goalText.ts`) | **Done**: 6 Vitest tests, browser-verified for age 35 and 50, horizons 10 and 3 (on the dashboard then; now on `/investments`) |
| 5–8 | `lib/funds.py` (AMFI catalog, returns, in-process cache) behind `GET /api/funds/top` and `/api/funds/search` | **Done**: 173 new unit tests (276 in all); warmed against live AMFI and mfapi.in. **Data source and cache superseded the same day** by the all-funds work below (mfapi.in and the in-process cache are gone) |
| 9 | `FundExplorer` (built on the dashboard, now on `/investments`): 1Y / 3Y / 5Y / Max toggle, fund-house search, warming and stale states | **Done**: browser-verified, including the warming message and the automatic fill-in |
| 10 | Stress falls re-measured (constants stand); second brain synced | **Done** |

---

## All funds by fund house, stored in MongoDB (COMPLETED — 2026-09-24)
Plan: `docs/superpowers/plans/2026-09-24-all-funds-stored-cache.md` (local only). Builds on the explorer above and
replaces its data source. Reasoning, measurements and assumptions in decisions/log.md, 2026-09-24 (first entry).

| Task | Area | Status |
|---|---|---|
| 1 | Catalog keeps every live Direct Growth scheme with AMFI's own category label (`parse_navall`, `CatalogEntry.category`) | **Done** |
| 2–3 | AMFI's dated NAV reports: `parse_nav_report`, `fetch_nav_range`; `fetch_plan`, `compute_window_returns`, `compute_max_return` | **Done**: 1Y / 3Y / 5Y matched mfapi.in to 0.000 pp on 67 fund-windows |
| 4 | `lib/fund_repo.py`: `StoredFund`, `MongoFundRepo` on `fund_rows`; a stored first NAV is never overwritten | **Done**: rules also run against a real local MongoDB |
| 5–7 | `lib/fund_store.py`: boot from stored rows, atomic refresh (once a day), `top`, sectioned `search`, resumable first-NAV pass | **Done**: refresh 21 s, restart load 16 ms, first-NAV pass 2 min 50 s |
| 8 | API returns `sections` and `max_pending`; `server.py` builds the store on `db.fund_rows`; mfapi code removed | **Done**: 355 unit tests |
| 9 | Explorer: one card per section, Max pending note, polling 5 s / 30 s / 15 s | **Done**: 13 Vitest tests; browser-driven against live AMFI |
| 10 | Live verification and second brain | **Done** locally. **Not pushed or deployed**; Render and Atlas untested |

---

## Investments page (COMPLETED — 2026-09-24)
Reasoning in decisions/log.md, 2026-09-24 (first entry). Frontend only; no backend or API change.

| Task | Area | Status |
|---|---|---|
| 1 | `pages/Investments.tsx` at `/investments` (behind `ProtectedRoute`, same profile-complete redirect and sample fallback as the dashboard) with a nav tab in `AppShell` | **Done**: typecheck clean, 13 Vitest tests pass, `vite build` ok |
| 2 | Surplus direction card extracted to `components/SurplusDirectionCard.tsx` (prop `block`: `"emergency"` / `"insurance"` / `null`, computed once in the page and shared with `FundExplorer`); `data-testid`s unchanged | **Done** |
| 3 | Dashboard drops the card, `FundExplorer` and the "Investable next" metric (metric row is now 3 wide); a link card to `/investments` takes the card's place | **Done**. **Not looked at in a browser**: it needs the backend, and starting that connects to Atlas and refreshes from AMFI |

---

## Proposed / Not Yet Scoped
- **Midnight trigger for the daily refresh** — a GitHub Actions job calls a token-protected endpoint that starts the
  same refresh, then polls a status endpoint (Render only counts incoming requests as activity, so the polling keeps it
  awake). The request-triggered path keeps working if the job breaks. Proposed only; the refresh today starts on the
  first fund request after the rows are a day old.
- **Pre-built "combinations"** (10–20 weightings across the cap segments, filtered by the monthly amount, with a
  blended return and a risk label) — the user deferred these on 2026-09-23 and they were not part of the fund
  explorer. Idea only.
- **SIP management (CAS import, view-only)** — idea only. See decisions/log.md's
  2026-09-17/18 entries for the narrowing history before resuming. No design, schema or code exists.

## Known Tech Debt
- **AMFI is the only fund data source, untested from Render, and its dated-report endpoint is undocumented**
  (2026-09-24). `NAVAll.txt` and `DownloadNAVHistoryReport_Po.aspx` were fetched from the dev machine only; if
  Render blocks them, options are a bundled catalog snapshot or another host. A layout change makes
  `parse_nav_report` fail loudly (a missing header line is "not the report") and the last stored rows keep serving as
  `stale`. Atlas M0 behaviour, Render's wake time and a multi-day refresh across real sleeps are unmeasured.
  (mfapi.in and the 135 s warm-up are gone.)
- **Max return is approximate** (2026-09-24). It is annualised from a first NAV seen on a month-start snapshot, so
  it can start up to about a month after launch (14 funds checked: within 0.7 pp of mfapi). If that is not good
  enough, the fallback the spec names is replacing Max with a 10Y window. The first-NAV pass reads about 181 reports
  (about 165 MB) the first time only.
- **A future-dated NAV in AMFI's file stalls the refresh** (2026-09-24). `parse_navall` takes "newest" from the
  largest date in the file, so one bad row makes every other scheme look dead; the store now treats a catalog under
  half the stored size as a bad download (rows kept, status `stale`, retry after 5 min) but does not ignore the bad
  row. Also: a refresh landing while the first-NAV pass saves can leave `returns.max` null in Mongo until the next
  refresh; near-duplicate AMFI labels ("FoF Domestic" / "Fund of Funds Scheme (Domestic)") show as separate cards.
- **The goal line rests on assumptions with no source or owner** (2026-09-24). `INFLATION_PCT`,
  `RETURN_MARGIN_PCT`, `EXPECTED_RETURN_PCT` and the cap-split shares in `lib/finance_config.py` are
  rules of thumb; `STRESS_FALL_PCT` is one crash (Jan to Apr 2020 median), with debt and gold assumed flat.
  They drive the "expects ≈ N%" and "about N% equity would reach it" text, so decide who owns them or find
  a source before treating the wording as more than illustrative.
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
- **`investable_surplus` ignores the emergency-fund gap** (2026-09-23). `_analysis()` subtracts only the
  estimated insurance premium; `emergency_gap` is tracked separately and never reserved. Only
  `Dashboard.tsx` withholds the SIP figure while the gap is open, so the API value, and anything else that
  reads it, still looks like investable money for someone with no safety net. Either gate every consumer
  or reserve the gap in the formula (the second changes existing numbers and tests).
