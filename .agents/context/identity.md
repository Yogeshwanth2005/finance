# Identity, Dev Persona & Code Style

## Who is working on this
Solo dev (git user Yogeshwanth2005) building this as a personal/portfolio
demo project — explicitly **not** a live financial or insurance service
(see `implementationplanv2.md` Section 0.2). Leans on the agent for
full-stack implementation: Next.js/React UI, Prisma schema + migrations,
and the deterministic gap-analysis/allocation business logic.

## Response Conventions
- Terse. No trailing "here's what I did" summaries — the diff/output speaks
  for itself.
- No comments explaining WHAT code does. A comment is only warranted for a
  non-obvious WHY (e.g. the DEMO_MODE/regulatory gate, the Prisma 7
  driver-adapter requirement).
- Don't invent fund/insurance reference data, NAVs, or premium figures —
  Section 9 requires real, sourced data (AMFI feed / insurer's own
  published pages) with an `external_url` and `source_note`/`last_synced_at`.

## Code Style Rules
- TypeScript throughout; no `any` in new code.
- All financial calculations (gap analysis, allocation, KPI ratios) are
  pure, deterministic functions — no ML/LLM calls anywhere in this app.
- Tunable constants live in `src/lib/config.ts`, never hardcoded inline
  (see Section 8 of the plan for the canonical list).
- Feature work that touches Sections 5.2/6.2/6.3 (fund/insurance examples)
  must stay gated behind `config.DEMO_MODE`.
