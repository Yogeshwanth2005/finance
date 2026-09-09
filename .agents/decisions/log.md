# Historical Decisions & Migrations

## Migration Index
No Prisma migrations yet — `schema.prisma` has no models. DB schema +
migrations is Task 2 of the build order (implementationplanv2.md Section 7)
and is still pending.

## Decisions
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
