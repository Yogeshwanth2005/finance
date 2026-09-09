# Active Roadmap & Technical Debt

## Backlog
Build order per implementationplanv2.md Section 7. Status as of 2026-09-09:

| # | Task | Status |
|---|---|---|
| 1 | Project scaffold | Done |
| 2 | DB schema + migrations (`fund_reference`, `insurance_plan_reference`, 5 new `gap_analysis_results` columns) | **Next up** — schema.prisma has no models yet |
| 3 | Onboarding flow UI — two-part disclaimer (Section 3) | Not started |
| 4 | Gap analysis engine — 4.1–4.5 (emergency fund, debt priority, term/health gap, KPI layer) | Not started |
| 5 | Allocation engine — 5.1–5.2 (base allocation + fund examples) | Not started |
| 6 | Insurance reference matching logic | Not started |
| 7 | Seed reference data — AMFI sync script + hand-curated insurance seed | Not started |
| 8 | Dashboard UI — KPI display, fund/insurance cards, gated by `DEMO_MODE` | Not started |
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
- `prisma/schema.prisma` has zero models — anything referencing the data
  model (financial_profile, insurance_profile, allocation_results, etc.)
  is spec-only until Task 2 lands.
