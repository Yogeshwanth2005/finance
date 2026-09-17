# Active Roadmap & Technical Debt

## Python/FastAPI + React Rewrite (active — supersedes the Next.js stack below)
Full rewrite per `docs/superpowers/specs/2026-09-17-python-fastapi-react-rewrite-design.md`
and `docs/superpowers/plans/2026-09-17-python-fastapi-react-rewrite.md` —
see decisions/log.md's 2026-09-17 entry for the why/scope. Status:

| Tasks | Area | Status |
|---|---|---|
| 1-9 | Backend (`backend/`): FastAPI scaffold, SQLAlchemy models, gap-analysis/allocation/insurance-matching engines, demo-user cookie, onboarding + dashboard routers, seed script | **Done** — 42 pytest tests passing; verified end-to-end against the live Supabase DB via curl (submit → compute → persist → dashboard fetch, including the `DEMO_MODE=false` compliance gate) |
| 10-15 | Frontend (`frontend/`): Vite/React (JS) scaffold, app shell, disclaimer gate, onboarding wizard, dashboard + cards | **Done** — 12 Vitest tests passing; disclaimer gate → 5-step wizard → review screen verified live via Playwright (₹-formatted review, inline validation blocking, Back/Next state preserved) through to a successful submit |
| 16 | Manual parity verification (submit → dashboard render with `DEMO_MODE` toggled, browser devtools cookie check) + retire `src/`/`prisma/` | **Blocked** — Supabase's raw Postgres ports (5432/6543) intermittently unreachable from this session's networks (same office-Wi-Fi pattern as `subsystem-notes.md`, confirmed to also affect at least one hotspot tried). HTTPS/443 being reachable does **not** mean these ports are — they're a different protocol/port pair entirely, not proxied by whatever's blocking web traffic. Resume from the onboarding-submit step of the plan's Task 16 once on a network where `nc`/`/dev/tcp` to `aws-0-ap-south-1.pooler.supabase.com:6543` succeeds. Both dev servers (`uvicorn app.main:app --port 8000`, `npm run dev` in `frontend/`) are otherwise ready to go |

**Until Task 16's cutover step runs**, the old Next.js/Prisma stack
(`src/`, `prisma/`) stays in place untouched — don't delete it early even
though the Python stack is functionally complete. See
subsystem-notes.md's "Two DB-migration tools" entry before running
`prisma migrate dev` against this DB in the meantime.

## Backlog (original Next.js/Prisma stack — being replaced above)
Build order per implementationplanv2.md Section 7. Status as of 2026-09-17:

| # | Task | Status |
|---|---|---|
| 1 | Project scaffold | Done |
| 2 | DB schema + migrations (`fund_reference`, `insurance_plan_reference`, 5 new `gap_analysis_results` columns) | **Done** — migration `20260916152548_init` applied to Supabase, all 8 models live (`prisma migrate status` confirms schema in sync). Note: the 4 carried-over v1 models were reconstructed from context, not a v1 source doc — see decisions/log.md 2026-09-16 entry for the specific assumptions to verify |
| 3 | Onboarding flow UI — two-part disclaimer (Section 3) | **Done** — Screens 2-6 built at `/onboarding/profile` (`src/app/onboarding/profile/page.tsx` + `screens.tsx`): 5-step wizard (personal basics, income/savings, debts, insurance cover, review+consent), client-state only, inline validation, POSTs to `/api/onboarding/submit` on final submit. Verified in-browser via Playwright (all 5 steps, validation blocking, Review screen ₹ formatting) — 2026-09-17 |
| 4 | Gap analysis engine — 4.1–4.5 (emergency fund, debt priority, term/health gap, KPI layer) | **Done and now wired** — `computeGapAnalysis` is called from `POST /api/onboarding/submit` (`src/app/api/onboarding/submit/route.ts`), which converts persisted `Decimal` reads to `number` at the boundary before calling it, per the tech-debt note this resolves |
| 5 | Allocation engine — 5.1–5.2 (base allocation + fund examples) | **Done and now wired** — `computeAllocation` + `selectFundExamples` called from the submit route and `src/app/dashboard/page.tsx` respectively |
| 6 | Insurance reference matching logic | **Done** — `src/lib/insurance-matching.ts` (`selectInsuranceExamples`), built TDD, 5 passing Vitest tests, same closest-sum-assured-match pattern as `selectFundExamples`. Wired into the dashboard |
| 7 | Seed reference data — AMFI sync script + hand-curated insurance seed | **Code done, not yet run** — `prisma/seed.ts` (18 funds across 6 categories, 4 insurance plans across 2 types), `tsx` wired via `prisma.config.ts`'s `migrations.seed`. Blocked on DB access (office Wi-Fi port block, see subsystem-notes.md) — run `npx prisma db seed` once reachable |
| 8 | Dashboard UI — KPI display, fund/insurance cards, gated by `DEMO_MODE` | **Code done, not yet verified against live data** — `/dashboard` (`src/app/dashboard/page.tsx` + `KpiCard`/`FundCard`/`InsuranceCard.tsx`): 5 KPI ring meters, allocation snapshot, `DEMO_MODE`-gated fund/insurance cards (single-plan card vs. neutral comparison table per the Section 6.3 amendment). Type-checks clean; DB-backed rendering not yet confirmed in-browser (blocked on DB access) |
| 9 | End-to-end test | **Partially done** — the non-DB-dependent half of the manual walkthrough (wizard UI, validation, navigation) verified via Playwright 2026-09-17. The DB-dependent half (submit → dashboard render, KPI value check against hand-computed expected values, `DEMO_MODE=false` check, external link check) is blocked on DB access — see `docs/superpowers/plans/2026-09-17-onboarding-intake-and-dashboard.md` Task 7 Step 7 for the exact steps to run once reachable |
| 10 | Deploy to Vercel (`DEMO_MODE=true`, private link only) | Not started |

## Proposed / Not Yet Scoped
- **SIP management (CAS import, view-only)** — new feature, not part of
  implementationplanv2.md's original Task 1-10 build order. Brainstorming
  paused 2026-09-17 pending a decision on CAS parser format scope — see
  decisions/log.md's 2026-09-17 entry for the full narrowing history
  before resuming this conversation. No design doc, schema, or code
  exists yet.

## Tooling Notes
- `graphify` (codebase knowledge-graph/wiki index) is installed via
  `uv tool install graphifyy` but **not yet built**. Its own detection
  step measured this repo at ~3,900 words / 21 files and reported
  "fits in a single context window — you may not need a graph." Revisit
  once Tasks 2–6 (schema, gap-analysis engine, allocation engine) land
  and the codebase is large enough that grep/read costs outweigh the
  extraction cost. Run `/graphify --wiki` then; the `CLAUDE.md` routing
  block already references `graphify-out/wiki/` conditionally, so no
  further wiring is needed once it exists.

## Known Tech Debt
- `src/lib/auth.ts`: credentials provider `authorize()` always returns
  `null` — intentional stub, real provider decision deferred to deploy
  time. Not a bug, but blocks any feature that needs a real logged-in
  user. Unaffected by today's work — the wizard/dashboard use the
  separate cookie-identified "demo user" (`src/lib/demo-user.ts`), not
  NextAuth.
- `financial_profile`/`insurance_profile`/`allocation_results` and
  `gap_analysis_results`' base columns have no v1 source document — their
  shape in `prisma/schema.prisma` is inferred, not authoritative. The two
  schema-level open questions (health cover combination, debt-EMI fields)
  are resolved as of Task 4 — see decisions/log.md's 2026-09-16
  gap-analysis-engine entry. What's still open: the emergency-fund status
  thresholds and the flat (not dependents-scaled) health cover baseline
  are new assumptions from that same entry, not verified against a real
  v1 source either.
- **Migration pending DB access**: `prisma/schema.prisma` already has
  `FundReference.aumCr`, `InsurancePlanReference.claimSettlementRatioPct`,
  `InsurancePlanReference.avgClaimSettlementDays` (added 2026-09-17), but
  `prisma migrate dev` hasn't been run yet — blocked on the office-Wi-Fi
  port issue (see subsystem-notes.md), hit again today. Run it, then
  `npx prisma db seed`, before Tasks 7-9 can actually be exercised against
  a live DB.
- `getOrCreateDemoUser()` (`src/lib/demo-user.ts`) can't set its cookie
  when called from a Server Component (Next.js restriction — only Server
  Actions/Route Handlers may write cookies). A first-ever visit straight
  to `/dashboard` (no cookie yet) creates an orphaned `User` row with no
  profile, then redirects to `/onboarding` without the cookie persisting;
  the real cookie gets set once the wizard's `POST` route runs. Harmless
  demo-data debris, not a correctness bug — documented in the file's own
  comment.
- Dashboard KPI ring meters (`src/app/dashboard/KpiCard.tsx`) all use a
  single neutral hue (the app's `--accent` token), not a red/amber/green
  status color, for 4 of 5 cards — only the emergency-fund card shows a
  status label, and only because `emergencyFundStatus` is already
  computed data. Deliberate: the other 4 KPIs (term/health adequacy,
  savings rate, debt-to-income) have no v1-sourced good/bad thresholds,
  and inventing them would be new, unreviewed advice-adjacent judgment —
  see decisions/log.md's 2026-09-17 entry.
