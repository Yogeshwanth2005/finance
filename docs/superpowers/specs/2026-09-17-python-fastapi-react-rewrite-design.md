# Design: Rewrite Fin as FastAPI (Python) backend + React (JS) frontend

Date: 2026-09-17
Status: Approved for planning

## Context

The current app (`feature/fin-v2-implementation` branch) is a Next.js 16 +
React 19 + Prisma app, per `implementationplanv2.md`. 9 of 10 build-order
tasks are done: onboarding wizard, gap-analysis engine, allocation engine,
insurance-matching engine, dashboard UI. Only deployment (#10) is
outstanding.

The user wants a full rewrite: backend in Python, frontend in React with
plain JavaScript/HTML/CSS — explicitly no TypeScript. This spec covers
that rewrite. `implementationplanv2.md` remains the source of truth for
all business logic, config defaults, and the `DEMO_MODE` regulatory
reasoning — this rewrite changes implementation language/framework only,
not behavior.

## Goals

- Reproduce the existing feature set 1:1: two-part disclaimer gate,
  5-step onboarding wizard, gap-analysis engine (Sections 4.1-4.5),
  allocation engine (5.1-5.2), insurance-matching engine, dashboard UI
  (KPI meters, allocation snapshot, `DEMO_MODE`-gated fund/insurance
  cards).
- No TypeScript anywhere. Backend is Python; frontend is JavaScript/JSX.
- Preserve all hard invariants from `stack-and-rules.md`: deterministic
  logic only (no ML/LLM), the `DEMO_MODE` gate, rule-based (not "best
  pick") fund/insurance selection.
- Reuse the existing Supabase Postgres database and schema as-is.

## Non-goals

- No new features beyond what's in the current backlog (SIP
  management/CAS import stays "proposed, not scoped").
- No change to business logic, thresholds, or the schema's field shapes
  — this is a language/framework port, not a redesign.
- Not solving real authentication — the demo-user cookie pattern stays,
  same as today's stub.

## Architecture

Two independently deployable apps in the same repo, replacing the single
Next.js app:

- **`backend/`** — FastAPI (Python 3.12+). JSON REST API. SQLAlchemy
  models mirror `prisma/schema.prisma`'s 8 models exactly, against the
  same Supabase Postgres instance. Alembic replaces `prisma migrate` for
  future schema changes (schema itself is unchanged by this rewrite).
- **`frontend/`** — Vite + React, plain JavaScript (`.jsx`, no
  TypeScript). React Router replaces Next.js App Router. Talks to the
  backend only via `fetch` through `src/api/client.js`.

`DEMO_MODE` and the tunable constants move into `backend/app/config.py`
(same semantics as today's `src/lib/config.ts`).

### Session/auth

Demo-user identification stays cookie-based (no real login), matching
current behavior. Because frontend and backend are separate origins in
production:

- FastAPI sets an httpOnly cookie (`SameSite=None; Secure` in
  production, `SameSite=Lax` acceptable for local same-origin dev).
- React's `api/client.js` calls `fetch` with `credentials: 'include'`.
- FastAPI CORS middleware allows the frontend's origin with
  `allow_credentials=True`.

This is the same demo-user pattern as `src/lib/demo-user.ts`, adapted for
cross-origin. It is actually simpler than the current implementation:
FastAPI has no Server-Component-style restriction on setting cookies, so
the documented tech-debt item (orphaned `User` row on first `/dashboard`
visit) does not recur.

## Components

**Backend (`backend/app/`):**
- `main.py` — FastAPI app + CORS config
- `models.py` — SQLAlchemy models, 1:1 mirror of `prisma/schema.prisma`
- `db.py` — SQLAlchemy engine/session against the existing
  `DATABASE_URL`/`DIRECT_URL` pair
- `config.py` — port of `src/lib/config.ts`, including `DEMO_MODE`
- `services/gap_analysis.py` — port of `src/lib/gap-analysis.ts`
  (`compute_gap_analysis`)
- `services/allocation.py` — port of `src/lib/allocation.ts`
  (`compute_allocation`, `select_fund_examples`)
- `services/insurance_matching.py` — port of
  `src/lib/insurance-matching.ts` (`select_insurance_examples`)
- `routers/onboarding.py` — `POST /api/onboarding/submit`
- `routers/dashboard.py` — `GET /api/dashboard` (new endpoint; today's
  dashboard fetches server-side inside a Server Component, which has no
  SPA equivalent, so this data now needs an explicit endpoint)
- `demo_user.py` — port of `getOrCreateDemoUser`
- `seed.py` — port of `prisma/seed.ts` (18 funds, 4 insurance plans)
- `alembic/` — migration setup, pointed at the existing schema (initial
  migration should match current DB state, not recreate it)

**Frontend (`frontend/src/`):**
- `pages/Onboarding.jsx` — two-part disclaimer gate
- `pages/OnboardingWizard.jsx` + `components/WizardSteps.jsx` — 5-step
  wizard (personal basics, income/savings, debts, insurance cover,
  review+consent), client-side validation, POSTs on final step
- `pages/Dashboard.jsx` + `components/KpiCard.jsx`, `FundCard.jsx`,
  `InsuranceCard.jsx` — fetch from `GET /api/dashboard` via a
  `useEffect`, since there's no server-side rendering in a Vite SPA
- `components/DisclaimerBanner.jsx`
- `api/client.js` — fetch wrapper, `credentials: 'include'` baked in
- `lib/format.js` — port of `src/lib/format.ts` (currency formatting)

## Data flow

1. User opens the app → disclaimer gate → wizard (client-state only,
   same 5 steps as today) → final step `POST /api/onboarding/submit`
   with the full profile as JSON.
2. Backend creates/updates `User`, `FinancialProfile`,
   `InsuranceProfile`; runs `compute_gap_analysis` then
   `compute_allocation`; persists `GapAnalysisResult` and
   `AllocationResult`; sets the demo-user cookie if not already set;
   returns success.
3. Frontend redirects to `/dashboard`.
4. Dashboard mounts, calls `GET /api/dashboard` (cookie sent
   automatically via `credentials: 'include'`).
5. Backend loads the demo user from the cookie, reads persisted
   gap-analysis/allocation results, runs `select_fund_examples` /
   `select_insurance_examples` gated by `DEMO_MODE`, returns JSON.
6. React renders KPI cards, allocation snapshot, and (if `DEMO_MODE`)
   fund/insurance cards.

## Error handling

- Request validation: Pydantic models on all POST bodies → FastAPI's
  automatic 422 with field errors → surfaced inline in the wizard steps
  (same UX as today's inline validation).
- No demo-user cookie on `GET /api/dashboard` → 404 → frontend redirects
  to `/onboarding`.
- `DEMO_MODE=false` → backend must omit named fund/insurance data from
  the JSON response entirely (not filter client-side) — preserves the
  compliance invariant noted in `subsystem-notes.md`: hiding UI cards
  while still returning named data from the API is not compliant.

## Testing

- Backend: pytest for `services/gap_analysis.py`, `allocation.py`,
  `insurance_matching.py` — port the existing Vitest test cases 1:1
  (same inputs/expected outputs; logic is unchanged, only the language
  is). `httpx.TestClient` for router integration tests
  (`/api/onboarding/submit`, `/api/dashboard`).
- Frontend: Vitest + React Testing Library for wizard validation and
  dashboard rendering (replaces the type-checking safety net TS used to
  provide). Manual Playwright walkthrough, same scope as the current
  backlog's end-to-end test item.

## Migration / cutover

1. Build `backend/` and `frontend/` alongside the existing `src/`,
   `prisma/` — don't delete anything yet.
2. Point the new backend at the same Supabase database (reuses existing
   data/seed once run).
3. Verify parity via the same manual walkthrough as the current
   backlog's end-to-end test item, run against the new stack.
4. Once parity is confirmed, retire `src/`, `prisma/`, `next.config.ts`,
   and Next.js/Prisma dependencies from `package.json` (or remove
   `package.json` entirely if nothing else in the repo needs Node).
5. Update `.agents/context/stack-and-rules.md` and the file map to
   reflect the new stack (per this repo's own second-brain-close
   convention).

## Deployment (deferred detail, same as current backlog item #10)

FastAPI backend → Render (web service). Vite React build →
Vercel/Netlify (static site). Exact configuration deferred to the
deploy task, matching how the current backlog already defers hosting
specifics.

## Open items carried over unchanged from the current backlog

These are pre-existing, not introduced by this rewrite:
- Real auth provider decision still deferred to deploy time.
- Emergency-fund status thresholds and flat health-cover baseline are
  unverified assumptions (see `decisions/log.md`).
- SIP management (CAS import) stays proposed/unscoped.
