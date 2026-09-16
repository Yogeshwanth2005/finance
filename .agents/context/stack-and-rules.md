# Invariants, Tech Stack & File Map

## Tech Stack
- Frontend: Next.js 16 (App Router) + React 19 + Tailwind CSS 4
- Backend: Next.js API routes (same app, no separate server)
- Database: PostgreSQL via **Supabase**, accessed via Prisma ORM 7.10.0
  through the `@prisma/adapter-pg` driver adapter
- Auth: NextAuth v4, credentials provider (currently a stub — see
  subsystem-notes.md)
- Testing: Vitest (`npm test`) — added 2026-09-16 for the gap-analysis
  engine's pure functions; not wired into a CI step yet
- Hosting target: Vercel
- No ML libraries, no LLM API calls anywhere in the app — every
  calculation is deterministic (implementationplanv2.md Section 1)

## Hard Invariants
1. **Prisma 7 driver-adapter requirement**: `datasource.url` must NOT be
   added back to `prisma/schema.prisma` — Prisma 7 removed that path.
   Connection config lives in `prisma.config.ts`; `PrismaClient` must be
   constructed with the `PrismaPg` adapter (`src/lib/db.ts`). Keep `prisma`
   and `@prisma/client` pinned to the same version — a version mismatch
   (8.0.0-rc.13 vs 7.10.0) previously broke client generation. See
   decisions/log.md.
2. **Two Supabase connection strings, not one**: `DATABASE_URL` (pooled,
   Supavisor transaction mode, port 6543) is what the running app uses via
   the adapter in `src/lib/db.ts`. `DIRECT_URL` (direct, port 5432) is what
   `prisma.config.ts` uses for `prisma migrate`/introspection — the pooler
   doesn't support the DDL + shadow-database operations migrate needs.
   Never point `prisma.config.ts`'s datasource at the pooled URL.
3. **No ML/LLM calls**: gap-analysis, allocation, and fund/insurance
   matching logic must stay pure/deterministic functions.
4. **`DEMO_MODE` gate** (`src/lib/config.ts`): Sections 5.2/6.2/6.3
   (named fund and insurance plan examples) must stay behind this flag.
   It exists because showing named financial products without SEBI RIA /
   IRDAI web-aggregator licensing is only legal while this stays an
   unpublished demo/portfolio project. Do not remove or bypass this gate
   without re-reading implementationplanv2.md Section 0.2 first.
5. Fund/insurance example selection must stay rule-based (sorted by
   AUM / sum-assured proximity) — never a ranked "best pick," to avoid
   crossing into personalized advice.

## File Map
- `src/lib/config.ts` — all editable tunable constants (plan Section 8)
- `src/lib/db.ts` — Prisma client singleton + `PrismaPg` adapter wiring
- `src/lib/gap-analysis.ts` (+ `.test.ts`) — Section 4.1-4.5 pure
  functions (`computeGapAnalysis` is the composed entry point); not yet
  wired to an API route or the DB
- `src/lib/auth.ts`, `src/app/api/auth/[...nextauth]/route.ts` — NextAuth
  config (credentials provider is currently a non-functional stub)
- `src/components/DisclaimerBanner.tsx` — persistent disclaimer banner
  (plan Section 6.4)
- `src/app/onboarding/page.tsx` — Screen 1, the two-part disclaimer gate
  (plan Section 3); `src/app/onboarding/profile/page.tsx` is an unbuilt
  placeholder for Screens 2-6
- `prisma/schema.prisma` — all 8 models, migrated (Task 2 done
  2026-09-16); the 4 carried-over-from-v1 models were reconstructed from
  context, not a real v1 source — see decisions/log.md
- `prisma.config.ts` — Prisma 7 connection config (replaces
  `datasource.url`)
- `implementationplanv2.md` — full spec; source of truth for all business
  logic, config defaults, and the regulatory reasoning behind `DEMO_MODE`
