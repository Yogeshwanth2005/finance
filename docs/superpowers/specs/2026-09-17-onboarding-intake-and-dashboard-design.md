# Onboarding Intake (Screens 2–6) + Dashboard UI (Task 8) — Design

**Status:** Approved 2026-09-17, ready for implementation planning.

## Context

Per `implementationplanv2.md` Section 7's build order, Tasks 4 and 5 (the
gap-analysis and allocation engines) are done as pure functions, but
nothing in the app calls them yet. Task 3's `/onboarding/profile` is a
placeholder stub, and Task 8 (dashboard) hasn't been started. This spec
covers building both, plus the minimum backend prerequisites (Task 6
insurance matching, the pending schema migration, and a lean Task 7 seed)
needed for the dashboard to render real data — see
`.agents/projects/active-backlog.md` for full task numbering.

No v1 source document exists for Screens 2–6's field-by-field layout (the
plan only says "unchanged from v1" without a v1 doc in this repo's
history) — the screen breakdown below is derived directly from the
`FinancialProfile` / `ExistingDebt` / `InsuranceProfile` schema, which is
itself an inferred-from-context reconstruction (see
`.agents/decisions/log.md`, 2026-09-16 entries). Treat both as
best-effort, not authoritative.

## Decisions made during brainstorming

1. **User identity**: real auth (`src/lib/auth.ts`) is an intentional
   stub deferred to deploy time. Rather than pulling that decision
   forward, intake uses a single auto-provisioned "demo user" per
   browser, identified by a cookie. No login UI.
2. **Sequencing**: build the full intake wizard, its persistence/engine
   wiring, and the full dashboard (plus their shared prerequisites)
   before doing end-to-end testing — testing happens once at the end,
   not gated between the two sub-projects.
3. **Task 7 scope**: a lean, hand-curated seed script — not the full
   automated AMFI sync. Real, well-known scheme/plan names, but
   illustrative figures, clearly commented as best-effort.

## 1. Demo user identity

`src/lib/demo-user.ts` exports `getOrCreateDemoUser()`:
- Reads a `fin_demo_user_id` cookie (httpOnly, long-lived, e.g. 1 year).
- If present and the `User` row exists, return it.
- Otherwise create a `User` (placeholder email `demo-<cuid>@fin.local`,
  no password), set the cookie, return it.

Called from every server action / API route that needs a `userId`. No
NextAuth changes, no login screen.

## 2. Onboarding Screens 2–6 — wizard at `/onboarding/profile`

Replaces the current stub. Client component, same visual language as
Screen 1 (`src/app/onboarding/page.tsx`) — mono label + heading + body
copy pattern, `accent` color tokens, dark-mode variants.

Five steps, Back/Next between them, state held in the wizard component
(no draft persistence to DB until final submit):

- **Screen 2 — Personal basics**: `age` (number), `dependentsCount`
  (number, default 0), `riskTolerance` (radio:
  conservative/moderate/aggressive), `investmentHorizonYears` (number)
- **Screen 3 — Income & savings**: `monthlyIncome`, `monthlyExpenses`,
  `currentSavings` (all Decimal-backed number inputs, ₹)
- **Screen 4 — Existing debts**: repeatable rows — `label` (text),
  `outstandingAmount`, `interestRatePct`, `tenureMonths`. Add/remove row
  controls. Zero rows is valid (no debts).
- **Screen 5 — Insurance cover**: `existingTermCoverAmount`,
  `personalHealthCoverAmount`, `employerHealthCoverAmount` (default 0
  each, matching the schema's `@default(0)`)
- **Screen 6 — Review & consent**: read-only summary of every value
  entered across Screens 2–5, plus a required consent checkbox
  (`consentGivenAt`), Submit button

**Validation**: inline, client-side only — required fields, numbers ≥ 0,
`age` in a sane range (e.g. 18–100), `investmentHorizonYears` ≥ 1. No new
form/validation library; plain component state + inline error text,
matching the existing codebase's lack of one.

## 3. Submit → persist → compute

`POST /api/onboarding/submit`, given the full wizard payload:

1. `getOrCreateDemoUser()` → `userId`.
2. `$transaction`:
   - Upsert `FinancialProfile` (by `userId`), converting form numbers to
     `Decimal`.
   - Delete existing `ExistingDebt` rows for that profile, insert the
     submitted rows fresh (simplest correct approach for a 1-row-per-user
     profile with a replaceable child list — no diffing needed).
   - Upsert `InsuranceProfile` (by `userId`).
3. Convert the persisted `Decimal` values back to `number` (the
   established boundary-conversion point, per
   `.agents/projects/active-backlog.md`'s tech-debt note) and call
   `computeGapAnalysis` + `computeAllocation`.
4. Insert new `GapAnalysisResult` + `AllocationResult` rows (versioned
   history, per the schema's existing design — a resubmission adds a new
   row, doesn't overwrite).
5. Return success; wizard redirects to `/dashboard`.

## 4. Task 6 — Insurance matching (pure function)

`src/lib/insurance-matching.ts`, same decoupled-from-Prisma pattern as
`selectFundExamples` in `src/lib/allocation.ts`:

```ts
selectInsuranceExamples(planType, gapAmount, plans, count = config.insurance_examples_per_gap_type)
```

Filters by `planType`, sorts by `Math.abs(sumAssuredMax - gapAmount)`
ascending (closest match — never "largest" or "cheapest", to avoid a
ranking signal), takes the first `count`. Built TDD with Vitest, mirroring
`allocation.test.ts`'s style.

## 5. Pending DB migration

One new migration adds:
- `FundReference.aumCr` — `Decimal @db.Decimal(12, 2)` (fund size in ₹
  crore; needed for Section 5.2's AUM-descending sort, already assumed
  by `selectFundExamples`'s `FundReferenceLike` type)
- `InsurancePlanReference.claimSettlementRatioPct` — `Decimal
  @db.Decimal(5, 2)`
- `InsurancePlanReference.avgClaimSettlementDays` — `Int`

Before running `prisma migrate dev`, verify DB reachability first — this
was blocked twice by an office-Wi-Fi port block (see
`.agents/context/subsystem-notes.md`); if the same symptom recurs, that's
the known network issue, not a new bug.

## 6. Task 7 — Lean seed data

`prisma/seed.ts` (wired to `package.json`'s `prisma.seed` field per
Prisma's seeding convention). Hand-curated, not the automated AMFI sync:

- At least 3 `FundReference` rows per `FundCategory` (6 categories × 3 =
  18 rows), using real, well-known scheme/AMC names so the UI reads as
  realistic, but NAV/expense-ratio/AUM figures are illustrative
  placeholders — commented in the seed file as best-effort, not live
  AMFI data, consistent with `DEMO_MODE`'s "illustrative only" framing.
- At least 2 `InsurancePlanReference` rows per `InsurancePlanType` (term,
  health) from real, well-known insurers, with illustrative sum-assured
  ranges, claim settlement ratio, and settlement days — same
  best-effort framing.

This unblocks Task 8's cards without waiting on a real AMFI integration,
which stays a separate, later backlog item.

## 7. Task 8 — Dashboard UI at `/dashboard`

Server component. Loads the demo user (`getOrCreateDemoUser()`), then
their latest `GapAnalysisResult` + `AllocationResult` (`computedAt desc`,
take 1 each). If neither exists, redirect to `/onboarding`.

Sections, top to bottom:

1. **Persistent disclaimer banner** (`DisclaimerBanner.tsx`) — append the
   new v2 sentence: *"Fund and insurance plan examples shown are
   illustrative only — this is a demo project, not a live service."*
2. **KPI section (6.1)** — 5 gauge/ring-style cards: emergency fund
   coverage %, term cover adequacy %, health cover adequacy %, savings
   rate %, debt-to-income %. Each card shows the ₹-amount gap
   underneath as supporting detail (percentage summarizes, doesn't
   replace the rupee figure, per the plan's explicit framing).
3. **Allocation snapshot** — equity/debt/gold percentages (existing v1
   behavior, carried over unchanged).
4. **Fund reference cards (6.2)** — only rendered when
   `config.DEMO_MODE === true` (checked server-side, before the DB query
   even runs — a `DEMO_MODE=false` request must never fetch named
   product rows, not just hide them client-side). For each allocation
   bucket, `selectFundExamples` → cards: scheme name, AMC, category,
   expense ratio, latest NAV, "View scheme details" link
   (`external_url`, neutral label, opens in a new tab).
5. **Insurance reference cards (6.3)** — same `DEMO_MODE` server-side
   gate. Only rendered per gap type when that gap > 0
   (`termCoverGap`/`healthCoverGap`). `selectInsuranceExamples` → either:
   - 1 plan: a single card (insurer, plan name, sum assured range, 2–3
     key features, indicative premium note, claim settlement ratio, avg.
     settlement time, "Show more details" → `external_url` new tab), or
   - 2+ same-`planType` plans: the neutral comparison table variant
     (same fields, tabular) per the 2026-09-16 amendment — no ranking,
     no "best value" badge, no score, no sort implying one plan is
     better.

## Testing approach

Per your direction, testing happens once everything above is built, not
incrementally:
- Unit tests (Vitest, TDD as-built) for `insurance-matching.ts`, matching
  existing `gap-analysis.test.ts` / `allocation.test.ts` coverage style.
- A manual end-to-end browser walkthrough at the end: fill the wizard →
  submit → land on `/dashboard` → verify KPI numbers match hand-computed
  expected values → verify fund/insurance cards render → verify
  `DEMO_MODE=false` hides named products → verify external links open
  the correct URL in a new tab.
- This matches Task 9 in the backlog (End-to-end test), effectively
  folding it into this pass rather than treating it as separate future
  work.

## Out of scope for this pass

- Real NextAuth provider / login UI (still deferred to deploy time).
- Automated AMFI sync script (Task 7's full form — the seed above is a
  hand-curated stand-in).
- Vercel deployment (Task 10).
- The insurance admin CRUD page (separate design doc, 2026-09-17,
  unrelated to this one).
