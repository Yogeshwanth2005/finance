# Active Roadmap & Technical Debt

## Backlog
Build order per implementationplanv2.md Section 7. Status as of 2026-09-16:

| # | Task | Status |
|---|---|---|
| 1 | Project scaffold | Done |
| 2 | DB schema + migrations (`fund_reference`, `insurance_plan_reference`, 5 new `gap_analysis_results` columns) | **Done** — migration `20260916152548_init` applied to Supabase, all 8 models live (`prisma migrate status` confirms schema in sync). Note: the 4 carried-over v1 models were reconstructed from context, not a v1 source doc — see decisions/log.md 2026-09-16 entry for the specific assumptions to verify |
| 3 | Onboarding flow UI — two-part disclaimer (Section 3) | **Done (Screen 1 only)** — `/onboarding` gate with both required acknowledgments, verified in-browser (checkbox states, Continue enable/disable, navigation). Screens 2–6 (the actual data-entry form) are out of scope here — no v1 spec exists for their field-by-field layout, and Task 4's engine isn't built yet to consume submissions — `/onboarding/profile` is a placeholder stub |
| 4 | Gap analysis engine — 4.1–4.5 (emergency fund, debt priority, term/health gap, KPI layer) | **Done** — `src/lib/gap-analysis.ts`, built TDD, 15 passing Vitest tests (`npm test`). Pure functions only: not yet wired to a DB read/write or an API route, and inputs/outputs are plain numbers, not Prisma `Decimal` |
| 5 | Allocation engine — 5.1–5.2 (base allocation + fund examples) | **Done** — `src/lib/allocation.ts`, built TDD, 12 passing Vitest tests. `computeAllocation` (5.1) and `selectFundExamples` (5.2) are pure functions, not wired to a DB read/write yet. Found while building this: `fund_reference` is missing the AUM column 5.2 needs — see Known Tech Debt |
| 6 | Insurance reference matching logic | Not started |
| 7 | Seed reference data — AMFI sync script + hand-curated insurance seed | Not started |
| 8 | Dashboard UI — KPI display, fund/insurance cards, gated by `DEMO_MODE` | Not started. Section 6.3 now also calls for a neutral comparison table (cost/features/claim settlement ratio/claim settlement time) when 2+ same-type plans are shown — amended 2026-09-16, see decisions/log.md |
| 9 | End-to-end test | Not started |
| 10 | Deploy to Vercel (`DEMO_MODE=true`, private link only) | Not started |

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
  user.
- `/onboarding/profile` (Screens 2–6: income/expenses/debt/insurance
  intake) is an unbuilt placeholder — needs real field spec (tied to the
  `FinancialProfile`/`InsuranceProfile`/`ExistingDebt` schema) and
  somewhere to submit to (Task 4's engine) before it can be built for
  real.
- `financial_profile`/`insurance_profile`/`allocation_results` and
  `gap_analysis_results`' base columns have no v1 source document — their
  shape in `prisma/schema.prisma` is inferred, not authoritative. The two
  schema-level open questions (health cover combination, debt-EMI fields)
  are resolved as of Task 4 — see decisions/log.md's 2026-09-16
  gap-analysis-engine entry. What's still open: the emergency-fund status
  thresholds and the flat (not dependents-scaled) health cover baseline
  are new assumptions from that same entry, not verified against a real
  v1 source either.
- `computeGapAnalysis` (Task 4) isn't wired to anything yet — no API
  route calls it, and it takes/returns plain `number`s while
  `prisma/schema.prisma` stores money as `Decimal`. Whichever task wires
  it up (likely Task 3's `/onboarding/profile` or a new API route) needs
  to convert `Decimal` ↔ `number` at that boundary.
- `InsurancePlanReference` needs 2 new columns (claim settlement ratio,
  average claim settlement time) + a migration for the amended Section
  6.3 comparison table — not yet added to `prisma/schema.prisma`. Real
  values must come from IRDAI's public annual disclosures when Task 7
  (seed reference data) runs, not invented.
- `FundReference` is also missing a column: `aumCr` (or similar), needed
  for Section 5.2's "sort by AUM descending" rule — a Task 2 oversight,
  caught while building Task 5. Bundle this migration with the
  `InsurancePlanReference` one above (both blocked on the same office-Wi-Fi
  port issue as of 2026-09-16 — see subsystem-notes.md).
- `computeAllocation`/`selectFundExamples` (Task 5), like `computeGapAnalysis`
  (Task 4), aren't wired to a DB or API route yet.
