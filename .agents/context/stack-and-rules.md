# Invariants, Tech Stack & File Map

## Tech Stack
- Frontend: Next.js 16 (App Router) + React 19 + Tailwind CSS 4
- Backend: Next.js API routes (same app, no separate server)
- Database: PostgreSQL, accessed via Prisma ORM 7.10.0 through the
  `@prisma/adapter-pg` driver adapter
- Auth: NextAuth v4, credentials provider (currently a stub — see
  subsystem-notes.md)
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
2. **No ML/LLM calls**: gap-analysis, allocation, and fund/insurance
   matching logic must stay pure/deterministic functions.
3. **`DEMO_MODE` gate** (`src/lib/config.ts`): Sections 5.2/6.2/6.3
   (named fund and insurance plan examples) must stay behind this flag.
   It exists because showing named financial products without SEBI RIA /
   IRDAI web-aggregator licensing is only legal while this stays an
   unpublished demo/portfolio project. Do not remove or bypass this gate
   without re-reading implementationplanv2.md Section 0.2 first.
4. Fund/insurance example selection must stay rule-based (sorted by
   AUM / sum-assured proximity) — never a ranked "best pick," to avoid
   crossing into personalized advice.

## File Map
- `src/lib/config.ts` — all editable tunable constants (plan Section 8)
- `src/lib/db.ts` — Prisma client singleton + `PrismaPg` adapter wiring
- `src/lib/auth.ts`, `src/app/api/auth/[...nextauth]/route.ts` — NextAuth
  config (credentials provider is currently a non-functional stub)
- `src/components/DisclaimerBanner.tsx` — persistent disclaimer banner
  (plan Section 6.4)
- `prisma/schema.prisma` — DB schema; no models yet (Task 2 of the build
  order, Section 7, is still pending)
- `prisma.config.ts` — Prisma 7 connection config (replaces
  `datasource.url`)
- `implementationplanv2.md` — full spec; source of truth for all business
  logic, config defaults, and the regulatory reasoning behind `DEMO_MODE`
