# Subsystem Notes & Load-Bearing Gotchas

## Prisma / DB (`src/lib/db.ts`, `prisma/schema.prisma`, `prisma.config.ts`)
Prisma 7 changed two things that aren't obvious from the docs' older
examples: (1) `datasource.url` no longer belongs in `schema.prisma` —
it moved to `prisma.config.ts`; (2) `PrismaClient` must be constructed
with a driver adapter (`@prisma/adapter-pg`'s `PrismaPg`) rather than
connecting directly from a connection string. Mixing old-style
`schema.prisma` with a `prisma`/`@prisma/client` version mismatch is what
broke the initial setup (fixed in commit `b787329`). If `prisma generate`
or `prisma migrate` starts failing after a dependency bump, check version
alignment between `prisma` and `@prisma/client` first.

## Local dev: the office Wi-Fi blocks Supabase Postgres ports — confirmed recurring
Hit twice on 2026-09-16. Connections to Supabase's pooler (`DATABASE_URL`
port 6543, `DIRECT_URL` port 5432) fail — not a credentials/config issue,
and not a Windows Firewall or local-antivirus rule (checked both times,
clean; no VPN client/proxy running either). Confirmed cause: **the office
Wi-Fi network's gateway blocks outbound ports 5432/6543 specifically**
(a common corporate IT policy against outbound DB traffic) — Supabase's
own HTTPS API (443) and unrelated hosts on 443/22 all connect fine from
the same network, isolating it to those two ports, not a general
non-web-port block. Fixed both times by switching networks (mobile
hotspot). Error signature varies (`ETIMEDOUT` one time, `ECONNREFUSED`
after a consistent ~2s delay another) — don't rely on the exact error
code, rely on the pattern: connection string checks out, other ports/
hosts work fine from the same machine, only 5432/6543 to Supabase fail.
**If `prisma migrate`/the app can't reach the DB on this network, don't
re-diagnose — just switch off the office Wi-Fi (mobile hotspot or home
network) before doing DB work.**

## Auth (`src/lib/auth.ts`)
The credentials provider's `authorize()` unconditionally returns `null` —
this is scaffolding, not broken auth. Real auth provider wiring is
explicitly deferred to deploy time (see the file's own comment). Don't
"fix" this by wiring up fake credential validation; it needs a real
provider decision first.

## Fund/Insurance reference data (Sections 5.2, 6.2, 6.3 — not yet built)
This is the most compliance-sensitive part of the app. Two traps once
it's implemented:
- The selection logic must stay deterministic/rule-based (AUM or
  sum-assured proximity sort) — introducing any "best match" scoring
  heuristic edges toward personalized advice, which is the exact thing
  Section 0.2 says this project is not licensed to do.
- `DEMO_MODE=false` must fully fall back to v1's category-only behavior
  (no named products at all), not just hide the UI cards while still
  returning named data from the API.
