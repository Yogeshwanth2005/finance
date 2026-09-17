# Historical Decisions & Migrations

## Migration Index
- `20260916152548_init` — first migration, applied 2026-09-16. Creates
  all 8 models (see the same-day decision below for the full list and
  the assumptions behind the 4 reconstructed-from-context ones).
  Confirmed applied via `prisma migrate status` ("Database schema is up
  to date"). Required being off the office Wi-Fi — see
  context/subsystem-notes.md's port-blocking gotcha.
- **Pending**: `prisma/schema.prisma` now has `FundReference.aumCr`,
  `InsurancePlanReference.claimSettlementRatioPct`, and
  `InsurancePlanReference.avgClaimSettlementDays` (added 2026-09-17, see
  the same-day entry below), but the migration itself hasn't been created
  or applied — blocked on the office-Wi-Fi port issue again today (`P1001`
  on port 5432, same signature as 2026-09-16). Run
  `npx prisma migrate dev --name add_aum_and_claim_settlement_columns`
  then `npx prisma generate` once off that network, per
  `docs/superpowers/plans/2026-09-17-onboarding-intake-and-dashboard.md`
  Task 1.

## Decisions
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
