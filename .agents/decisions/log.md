# Historical Decisions & Migrations

## Migration Index
- `20260916152548_init` — first migration, applied 2026-09-16. Creates
  all 8 models (see the same-day decision below for the full list and
  the assumptions behind the 4 reconstructed-from-context ones).
  Confirmed applied via `prisma migrate status` ("Database schema is up
  to date"). Required being off the office Wi-Fi — see
  context/subsystem-notes.md's port-blocking gotcha.
- **Resolved, but not via Prisma**: `FundReference.aumCr`,
  `InsurancePlanReference.claimSettlementRatioPct`, and
  `InsurancePlanReference.avgClaimSettlementDays` were applied to the live
  DB 2026-09-17 via a hand-trimmed **Alembic** migration
  (`backend/alembic/versions/6eed1f0685fe_...py`, part of the Python
  rewrite below), not `npx prisma migrate dev`. `prisma/schema.prisma`
  still declares these columns with no corresponding Prisma migration
  file — if the TS stack is used again before it's retired, `prisma
  migrate dev` will see this as drift. See
  `context/subsystem-notes.md`'s "Two DB-migration tools" entry before
  touching Prisma migrations on this DB again.

## Decisions
- **2026-09-20** | Promoted and integrated SurakshaCFO RAG document extraction, deterministic offline vector embeddings, regulatory guardrail refusal gate, and policy intelligence drawer into root Fin v2 architecture | **why**: User request to promote `finance/` features to root Fin application and integrate policy intelligence without compromising Fin's strict compliance invariants (Invariant 1: camelCase SQLAlchemy mappings; Invariant 2: `DEMO_MODE` gate; Invariant 3: deterministic financial calculations; Invariant 4: hard refusal gate for comparisons/recommendations) | **verification**: 52 backend pytest tests passing, 12 frontend Vitest tests passing, Alembic migration `a1f8c9e0d1b2` generated, specification preserved in `docs/SURAKSHACFO_SPEC.md` | **cleanup**: Ignored redundant staging files in `.gitignore` and updated second-brain state.
- **2026-09-19** | Completed full stack cutover from Next.js 15/Prisma/TypeScript to Python 3.12/FastAPI/SQLAlchemy 2.0/Alembic + Vite/React 18 (Task 16) | **why**: Architectural rewrite to a decoupled Python FastAPI backend and Vite React SPA frontend per `docs/superpowers/specs/2026-09-17-python-fastapi-react-rewrite-design.md` and `docs/superpowers/plans/2026-09-17-python-fastapi-react-rewrite.md` | **verification**: 42 backend pytest tests passing, 12 frontend Vitest tests passing, production build verified, `DEMO_MODE` regulatory gate fully operational | **retired**: Removed legacy Next.js routes (`src/`), Prisma schemas/migrations (`prisma/`), and TypeScript build configs (`next.config.ts`, `tsconfig.json`, `eslint.config.mjs`).

- **2026-09-18** | Brainstormed (not spec'd) two proposed features —
  **insurance-plan document Q&A chatbot** and **SIP-ranking display** —
  narrowed across several rounds to stay inside the existing
  regulatory-gate boundary rather than reopening it | **why**: user idea,
  "insurance docs can't be fetched via API, so build a RAG chatbot over
  the policy PDFs" | **insurance chatbot narrowed to**: plan-fact lookup
  only (coverage, exclusions, waiting periods, claim process), grounded
  in the source document with citations — **explicitly not** plan
  comparison or "which plan should I choose," which the user confirmed
  themselves unprompted ("they wont be asking suggestions... it just
  clears doubts... not like which to choose"). Needs a runtime refusal
  path for recommendation-shaped questions, not just a scope note on
  paper. See backlog entry for the open design questions (PDF sourcing,
  schema, provider) | **also explored and rejected, in order**: (1) AI
  freely suggesting a plan from income/family inputs with a disclaimer —
  rejected because a disclaimer fixes legal exposure, not the
  hallucination/inconsistency risk of an ungrounded LLM judgment call;
  (2) a "reader extracts facts, then deterministic rules pick the best
  plan, AI explains the pick" hybrid — this looked safer since the
  picker is plain rules, not AI, but on cross-check against
  `stack-and-rules.md` Invariant 5 it's still a "ranked best pick" by
  definition, just computed differently, so it was rejected too; (3)
  ranking the *fund catalog* (not the user's own holdings) by XIRR, then
  by 1yr/3yr/5yr returns, to surface a "top funds" list — same rejection
  each time: sorting investable options by past performance and
  presenting the order **is** the recommendation, regardless of whether
  a human, a rule, or an AI produced the ranking, and this is exactly the
  kind of content SEBI requires "past performance is not indicative of
  future returns" disclosures for | **landed on, both confirmed safe**:
  (a) showing returns/facts as an **unsorted** table (user can eyeball
  and rank mentally themselves — matches the existing insurance
  comparison-table pattern, Invariant 5 stays intact); (b) showing a
  **user's own SIP holdings'** performance since that specific SIP's
  start date (computed from the real CAS transaction history — XIRR
  applied to the user's own past, not to rank a catalog for a future
  decision) — this was the resolving reframe: "since I invested" is a
  fact about the user's own account, not a recommendation about what to
  buy, so it doesn't touch Invariant 5 at all | **not yet done**: neither
  feature has a design doc, schema, or code — this stays at the
  brainstorming/backlog stage, see `projects/active-backlog.md`'s
  "Proposed / Not Yet Scoped" section.
- **2026-09-17** | Full rewrite of the app from Next.js/React/Prisma to
  **FastAPI (Python) backend + Vite/React (plain JavaScript, no
  TypeScript) frontend**, per a written design spec
  (`docs/superpowers/specs/2026-09-17-python-fastapi-react-rewrite-design.md`)
  and 16-task implementation plan
  (`docs/superpowers/plans/2026-09-17-python-fastapi-react-rewrite.md`) |
  **why**: explicit user request — no TypeScript anywhere, Python on the
  backend, React with plain JS/HTML/CSS on the frontend | **scope**:
  reproduces the existing feature set 1:1 (disclaimer gate, 5-step
  onboarding wizard, gap-analysis/allocation/insurance-matching engines,
  dashboard KPIs/fund/insurance cards) against the *same* Supabase
  Postgres database — not a redesign of business logic |
  **status**: backend (`backend/`, Tasks 1-9) fully built, 42 pytest tests
  passing, and verified end-to-end against the live DB via curl (submit →
  compute → persist → dashboard fetch → `DEMO_MODE=false` compliance gate
  all confirmed with real data). Frontend (`frontend/`, Tasks 10-15) fully
  built, 12 Vitest tests passing, and the disclaimer gate → 5-step wizard
  → review screen verified live via Playwright through to a successful
  submit (₹-formatted review values, inline validation blocking bad
  input, Back/Next state preservation). Task 16 (final live browser
  walkthrough of submit → dashboard render with `DEMO_MODE` toggled, and
  retiring `src/`/`prisma/`) is **not done** — see Known Tech Debt below |
  **two real bugs found only by testing against the live DB**, both fixed
  and documented in `context/subsystem-notes.md`: psycopg3 rejecting
  Prisma's `pgbouncer=true` URL param, and Prisma's `@updatedAt` having no
  DB-level default (SQLAlchemy's `server_default` silently produced NULL
  inserts) | **also surfaced**: `_prisma_migrations`'s counterpart problem
  — the pending `aumCr`/`claimSettlementRatioPct`/`avgClaimSettlementDays`
  migration (see Migration Index above) got applied via Alembic instead
  of Prisma, since the Python rewrite needed it working; that's now a
  cross-stack drift risk documented in subsystem-notes.md | **rejected**:
  a same-origin/monolith deployment (FastAPI serving the built React
  static files) — chose separate deploys (Render for the API,
  Vercel/Netlify for the static frontend) instead, deferred to the deploy
  task same as the original stack's Vercel deploy was | **not yet
  decided**: real hosting configuration (deferred, matches how the
  original backlog already deferred deploy specifics).
- **2026-09-17** | Built Tasks 3 (Screens 2-6), 6 (insurance matching), 7
  (seed data, code only), and 8 (dashboard UI) from a written design spec
  (`docs/superpowers/specs/2026-09-17-onboarding-intake-and-dashboard-design.md`)
  and implementation plan
  (`docs/superpowers/plans/2026-09-17-onboarding-intake-and-dashboard.md`) |
  **why**: next items in the build order, bundled into one plan since the
  dashboard can't render anything real without the intake wizard and its
  prerequisites feeding it | **found while building this**: `.gitignore`
  had bare `src`/`.agents` lines (from commit `ffb20fe`) silently
  gitignoring all *new* files under those directories — already-tracked
  files were unaffected, which is why it went unnoticed, but every file
  in this session's build would have been invisible to git until fixed.
  Fixed as the first step (commit `4160598`) | **assumptions made, not
  from a v1 source**:
  - Demo user identity (`src/lib/demo-user.ts`) is a cookie only, no
    NextAuth involvement — per the design spec's Section 1 decision.
    `getOrCreateDemoUser()` can't set the cookie when called from a
    Server Component (Next.js restriction); documented as tech debt
    rather than worked around, since the one caller affected
    (`/dashboard` on a cookie-less first visit) redirects to `/onboarding`
    immediately anyway.
  - KPI dashboard cards (`src/app/dashboard/KpiCard.tsx`) render as
    single-hue ring meters using the app's own `--accent` token, not a
    red/amber/green status color — deliberate, not an oversight. Only the
    emergency-fund card shows a status label, reusing the already-computed
    `emergencyFundStatus` enum; the other 4 KPIs (term/health adequacy,
    savings rate, debt-to-income) have no v1-sourced good/bad thresholds
    in `gap-analysis.ts`, and inventing UI-only thresholds for them would
    be new advice-adjacent judgment never reviewed as business logic —
    same caution as the "no ranking signal" rule already applied to
    fund/insurance selection (see stack-and-rules.md Invariant 5).
  - Seed data (`prisma/seed.ts`) uses real, well-known AMC/insurer/bank
    names (HDFC, ICICI Prudential, SBI, Axis, Star Health, RBI for SGBs,
    etc.) with illustrative NAV/AUM/expense-ratio/premium/claim figures,
    each row commented as such — matches the design spec's Section 6
    framing ("real names, illustrative figures"). External URLs point to
    each institution's real homepage, not a guessed deep link to a
    specific scheme page (avoids linking to a URL that was never
    verified to exist).
  **rejected**: running the seed against fabricated/placeholder company
  names instead of real ones — the design spec explicitly calls for real,
  recognizable names so the UI reads as realistic | **not yet done**: the
  schema migration and the seed script itself haven't run (DB
  unreachable, office-Wi-Fi port block — see Migration Index above); the
  DB-dependent half of the manual E2E walkthrough (submit → dashboard
  render, KPI value spot-check, `DEMO_MODE=false` check, external link
  check) is correspondingly unverified — see the plan doc's Task 7 Step 7
  for the exact steps once DB access is restored.
- **2026-09-17** | Brainstormed (not yet spec'd) a new "SIP management"
  feature — scope narrowed across several rounds of clarification, paused
  before a design doc was written | **why**: user request, starting from
  a vague "add SIP management" ask | **narrowed to, in order**:
  1. Not manual record-keeping and not simulated buy/sell — user wants
     their *real* SIP/holdings status shown, like Groww.
  2. Not a live broker API integration (Groww etc. don't offer public
     retail-aggregation APIs to third parties — infeasible for a personal
     project) — instead, **CAS (Consolidated Account Statement) PDF
     import**: user uploads their real CAMS/KFintech/NSDL statement, app
     parses it.
  3. **View-only**: CAS is the single source of truth, re-uploaded to
     refresh; no manual add/edit/buy/sell on top of it.
  **explicitly rejected in this conversation**: manual SIP entry (all
  variants), simulated paper-trading buy/sell, live broker/API
  integration, hybrid CAS+manual overlay.
  **not yet decided — picking back up later**: how to handle CAS format
  variety across RTAs (CAMS/KFintech/NSDL each lay out statements
  differently). Two options were on the table when paused: (a) support
  only CAMS "detailed" CAS with a clear error for other formats
  (narrower, safer — matches this project's existing "curated, not
  universal" pattern), or (b) best-effort parsing across all three
  (more useful, higher risk of silently-wrong numbers in a finance app).
  **not yet done**: no data model, no design doc, no code — this is pure
  scope-narrowing, next step is finishing the brainstorming session
  (parser scope question) before writing
  `docs/superpowers/specs/YYYY-MM-DD-sip-management-design.md` and
  handing off to writing-plans. Also unaddressed: CAS PDFs are
  password-protected with sensitive financial PII (every AMC holding
  across a person's whole portfolio) — password/file handling (never
  persist either) needs to be part of that design, tied to the same DPDP
  consent pattern already used for `FinancialProfile`/`InsuranceProfile`.
- **2026-09-16** | Built the allocation engine (`src/lib/allocation.ts`,
  TDD, 12 passing Vitest tests) covering Section 5.1 (age-based base
  equity, risk-tolerance scaling, short-horizon shift) and 5.2's fund
  selection logic (bucket-to-category mapping, AUM-descending sort) |
  **why**: next item in the build order (Task 5) | **assumptions made,
  not from a v1 source** (new config constants, both documented inline):
  - `base_equity_pct = config.base_equity_age_constant (100) - age` — the
    standard "100 minus age" glide-path rule of thumb; v1 could have used
    a different constant (110, 120) or a non-linear curve.
  - Gold is a flat `config.gold_allocation_pct` (10%) diversification
    sleeve, capped by whatever's left after equity so equity+debt+gold
    always sums to exactly 100 — not derived from age/risk/horizon. No
    spec at all for the debt/gold split existed before this.
  - Equity is clamped to [0, 100] before the gold/debt split, so extreme
    inputs (very young + aggressive, or very old + conservative +
    short-horizon) can't push debt or gold negative.
  **found while building this**: `fund_reference` (Task 2's schema) has
  no AUM/fund-size column, but Section 5.2 requires sorting fund examples
  by AUM descending — an oversight from Task 2, not a new assumption.
  Added to the Migration Index above as pending; `selectFundExamples`
  itself is written against a plain `{ id, category, aumCr }` shape
  decoupled from Prisma, same pattern as `gap-analysis.ts`, so the pure
  function needed no changes once the column exists — only the DB-wiring
  step (still not built, see Task 4's same open item) will need it.
- **2026-09-16** | Amended Section 6.3 to allow a side-by-side comparison
  table of same-`plan_type` insurance plans (in addition to individual
  cards), and added claim settlement ratio + average claim settlement
  time as new fields to show | **why**: user request, after two rounds
  of narrowing — first proposed "AI suggests insurance" (rejected, see
  below), then clarified to "just compare packages on cost/features/other
  factors, don't suggest what to pick." Original Section 6.3 banned
  comparison tables specifically to avoid a "here's our pick" read; a
  *neutral fact table* doesn't have that problem, only a *ranked* one
  does — so the fix was narrowing the rule (no ranking signal), not
  keeping the table ban | **explicitly still rejected in this same
  conversation**: using an LLM to choose, rank, or "suggest" which
  insurance plan to take — that's a personalized recommendation, which
  requires SEBI RIA / IRDAI licensing for a real service (Section 0.2)
  and is exactly what Section 5.2's "never a ranked best pick" rule
  exists to prevent. Also proposed and separately deferred: an
  insurance/SIP-only chatbot (bigger risk surface than a comparison
  table — open-ended Q&A can drift off-topic or hallucinate specifics
  about a named plan) and AI-based translation/simplification of plan
  text (fine in principle, but should happen once at content-authoring
  time, human-reviewed, saved as static content — not a live per-request
  LLM call) | **not yet done**: `InsurancePlanReference` needs 2 new
  columns (claim settlement ratio, avg. settlement time) + a migration;
  the comparison-table UI itself isn't built — both still pending
  whichever task actually builds Section 6.3 (Task 8, Dashboard UI, per
  the current build order — Task 5 Allocation Engine is next in
  sequence). Real values for the new fields must come from IRDAI's
  public annual claim-settlement disclosures, per identity.md's "don't
  invent reference data" rule — same sourcing standard as everything
  else in `fund_reference`/`insurance_plan_reference`.
- **2026-09-16** | Built the gap-analysis engine (`src/lib/gap-analysis.ts`,
  TDD, 15 passing Vitest tests) covering Sections 4.1-4.5: emergency fund,
  debt EMI/prioritization, term/health cover gap, and the 4.5 KPI layer,
  composed into `computeGapAnalysis` | **why**: next item in the build
  order (Section 7, Task 4); pure/deterministic functions per the
  no-ML invariant | **resolves the two open schema questions from the
  Task 2 entry below**:
  - Effective health cover = `personalHealthCoverAmount +
    employerHealthCoverAmount` (straight sum) — no v1 source for a
    weighting rule, so the simplest defensible combination was used.
  - `ExistingDebt`'s EMI fields (`outstandingAmount`, `interestRatePct`,
    `tenureMonths`) map directly onto the plan's Section 4.5 EMI formula
    with no gaps.
  **new assumptions made, not from a v1 source**:
  - Emergency fund status thresholds: `adequate` at ≥100% of target,
    `inadequate` below 50%, `building` in between. The plan names the
    three states but never gives thresholds.
  - `recommended_health_cover` is `config.health_cover_baseline` flat,
    not scaled by `dependentsCount` — matches the config comment's literal
    wording ("baseline"), but this is a real product decision someone
    could reasonably make differently.
  - Zero-interest debts fall back to straight-line EMI (`outstanding /
    tenureMonths`) since the compound-interest formula divides by zero
    at a 0% rate — an implementation necessity, not a business-logic
    guess.
  **rejected**: guessing v1's exact thresholds instead of picking and
  documenting new ones — no source existed to guess from | **not yet
  done**: not wired to a DB read/write or an API route — `computeGapAnalysis`
  takes plain numbers in, returns plain numbers out, with no persistence
  or Prisma Decimal handling yet.
- **2026-09-16** | Wrote the full `schema.prisma` (all 8 models: `User`,
  `FinancialProfile`, `ExistingDebt`, `InsuranceProfile`,
  `AllocationResult`, `GapAnalysisResult`, `FundReference`,
  `InsurancePlanReference`), not just the two v2-NEW tables |
  **why**: implementationplanv2.md Section 2 says `users`,
  `financial_profile`, `insurance_profile`, and `allocation_results`
  "carry over unchanged from v1," but no v1 plan/schema document exists
  anywhere in this repo or its git history (`git log --all` shows only
  `implementationplanv2.md` was ever committed) — so there was no source
  of truth to copy. User chose (2026-09-16, in response to being asked)
  to have these designed from context rather than left out or supplied
  separately | **assumptions made, not sourced from a v1 doc — verify
  before treating as final**:
  - `FinancialProfile`/`InsuranceProfile` are 1 row per user (onboarding
    form, updated in place); `GapAnalysisResult`/`AllocationResult` are
    N rows per user (a `computedAt`-stamped history), since the plan's
    "computed_at" column implies recomputation over time, not a single
    snapshot.
  - `existing_debts` (Section 4.5's EMI formula) is a separate
    `ExistingDebt` table FK'd to `FinancialProfile`, with
    `outstandingAmount`/`interestRatePct`/`tenureMonths`/a free-text
    `label` — the plan never names the debt fields directly, only the
    EMI formula that consumes them.
  - `InsuranceProfile.personalHealthCoverAmount` +
    `employerHealthCoverAmount` are two separate stored fields; the
    plan's `effective_existing_cover` (Section 4.5) is treated as a
    computed value the gap-analysis engine derives from both, not a
    stored column — the combination rule (e.g. does employer cover count
    in full?) still needs to be decided when Task 4 (gap analysis
    engine) is built.
  - `recommended_term_cover` / `recommended_health_cover` (referenced in
    the Section 4.5 formulas) are treated as computed-not-stored,
    reconstructible from `termCoverGap`/`healthCoverGap` +
    `existingTermCoverAmount`/effective health cover — only the gap and
    the adequacy percentage are persisted, matching the plan's literal
    column list for `gap_analysis_results`.
  - `consentGivenAt` (nullable timestamp) added to both
    `FinancialProfile` and `InsuranceProfile` per the plan's mention of
    "v1 consent rules for `financial_profile` and `insurance_profile`"
    and Section 3's "consent tracking unchanged" — the actual consent
    *flow* (what triggers it, what text is shown) is still undefined
    pending Task 3 (onboarding UI).
  - All money amounts are `Decimal` (never `Float`), percentages are
    `Decimal(7,2)` — avoids floating-point rounding on financial figures.
  - IDs are `cuid()` strings (Prisma's zero-dependency default), not
    `uuid()` — no particular reason to prefer one for a demo project.
  **rejected**: scoping Task 2 down to only the two NEW tables (would
  leave `gap_analysis_results` unable to store its base v1 columns, and
  block Tasks 4-6 which read/write the carried-over models) | **applied**:
  migration `20260916152548_init` (see Migration Index above) — the
  assumptions above are still unverified against a real v1 source, just
  no longer blocking Task 2.
- **2026-09-09** | Chose **Supabase** as the managed Postgres provider
  (plan Section 1 previously left it open between Supabase/Neon) | **why**:
  user decision | **implementation**: two connection strings —
  `DATABASE_URL` (pooled/Supavisor, port 6543) for the app runtime via
  `src/lib/db.ts`'s adapter, `DIRECT_URL` (direct, port 5432) for
  `prisma migrate`/introspection via `prisma.config.ts`, since Supabase's
  pooler doesn't support the DDL + shadow-database work migrate needs |
  **resolved 2026-09-16**: see below.
- **2026-09-16** | Created the real Supabase project (ref
  `kyjsothfwxsbqxaaqqqt`, ap-south-1) and dropped real credentials into
  `.env`, replacing the placeholder `DATABASE_URL`/`DIRECT_URL` | **why**:
  unblocks Task 2 (DB schema + migrations), the item this was gating |
  **verified**: both the pooled (6543) and direct (5432) connection
  strings reach the database — confirmed via a raw `pg` connection and
  via `prisma migrate status`, which reports no migrations yet (expected,
  since `schema.prisma` still has zero models) | **note**: an initial
  `prisma migrate status` attempt returned P1001 (unreachable); a retry
  seconds later succeeded, consistent with the project still finishing
  cold-start provisioning — not a config problem.
- **2026-09-09** | Pinned `prisma` and `@prisma/client` to matching
  `7.10.0`, added `@prisma/adapter-pg`, moved connection config from
  `schema.prisma`'s `datasource.url` to `prisma.config.ts` | **why**:
  Prisma 7 removed `datasource.url` from the schema and requires
  driver-adapter-based `PrismaClient` construction; the project had
  drifted to a mismatched `prisma@8.0.0-rc.13` / `@prisma/client@7.10.0`,
  which broke generation | **rejected**: staying on the mismatched
  versions, or using `prisma-client-js` without an adapter (unsupported
  in v7). Commit `b787329`.
- **2026-09-09** | Disabled Next.js's auto-generated `AGENTS.md`/
  `CLAUDE.md` agent-rule files | **why**: they conflict with a
  hand-maintained second-brain `CLAUDE.md` | **rejected**: letting
  Next.js regenerate them on every `next dev`/`next build`.
- **(plan-level, predates this repo)** v2 shows real, named fund and
  insurance plan examples where v1 deliberately showed categories only |
  **why**: naming specific products is only legal here because this is an
  unpublished personal/portfolio demo, not a live service — doing so for
  a real service would require SEBI RIA registration (fund advice) and
  IRDAI web-aggregator licensing (insurance leads) | **rejected**: keeping
  v1's category-only behavior permanently. **Revisit trigger**: if the
  project ever moves toward real users beyond demo/portfolio use (the
  "closed beta with friends/family" milestone named in Section 7) — see
  implementationplanv2.md Sections 0.2 and 7.
