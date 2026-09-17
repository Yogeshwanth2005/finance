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

## Python backend (`backend/app/db.py`, `backend/app/models.py`) — SQLAlchemy against the same Supabase DB as Prisma
Three gotchas hit while building the parallel FastAPI/SQLAlchemy stack
(`docs/superpowers/plans/2026-09-17-python-fastapi-react-rewrite.md`),
none obvious from either SQLAlchemy's or FastAPI's docs:
- **psycopg3 rejects Prisma's `pgbouncer=true` query param.** The pooled
  `DATABASE_URL` has `?pgbouncer=true` (a Prisma/asyncpg-side hint for
  Supabase's transaction-mode pooler). psycopg3 passes unrecognized query
  params straight to libpq, which errors with `invalid connection option
  "pgbouncer"`. `db.py`'s `_to_psycopg_url()` strips it — `NullPool` +
  `connect_args={"prepare_threshold": None}` already give the same
  "don't rely on server-side prepared statements/pool state" behavior
  that flag exists for on the Prisma/asyncpg side.
- **Prisma's `@updatedAt` has no DB-level default — unlike
  `@default(now())`.** `createdAt`/`computedAt`/`lastSyncedAt` columns
  (`@default(now())`) really do have a Postgres `DEFAULT
  CURRENT_TIMESTAMP` — confirmed via `alembic revision --autogenerate`,
  which showed `existing_server_default` for those but not for
  `updatedAt`. Prisma manages `@updatedAt` entirely client-side (every
  write it issues includes the value). A SQLAlchemy model using
  `server_default=func.now()` for `updatedAt` silently omits the column
  from its `INSERT`, and Postgres NOT-NULLs the insert. Fix: Python-side
  `default=`/`onupdate=` (a plain callable), not `server_default=`. Any
  new Prisma-carried-over model must use this pattern for every
  `@updatedAt` field, never `server_default`.
- **A masked backend 500 shows up in the browser as a CORS error.**
  Starlette's `CORSMiddleware` never gets to attach
  `Access-Control-Allow-Origin` to a response that came from an
  *unhandled* exception (the ASGI server's generic 500 response bypasses
  it). The browser then reports "blocked by CORS policy" even though
  CORS config is correct — confirmed by curling the same endpoint with an
  `Origin` header: preflight `OPTIONS` returns full CORS headers, but the
  real `POST` returns a bare 500 with none. **When a fetch that used to
  work suddenly "fails CORS," check the backend's actual response status
  and server-side traceback before touching CORS config at all.**

## Two DB-migration tools now point at the same Supabase database
As of the Python/React rewrite, this project has two independent
migration tools that have both touched the same live schema:
Prisma (`prisma/schema.prisma` + `prisma migrate`, the original TS
stack) and Alembic (`backend/alembic/`, the new FastAPI stack). The
`FundReference.aumCr` / `InsurancePlanReference.claimSettlementRatioPct`
/ `avgClaimSettlementDays` columns that Prisma's schema declared but
never migrated (see the "Pending" migration note in decisions/log.md's
2026-09-17 entry) were applied via a **hand-trimmed Alembic migration**
(`backend/alembic/versions/6eed1f0685fe_...py`), not `prisma migrate
dev`. Prisma's own `_prisma_migrations` bookkeeping table was
deliberately left untouched. **Consequence: if the old TS stack is used
again before Task 16's cutover, running `prisma migrate dev` will detect
schema drift** (schema.prisma declares these columns; Prisma's migration
history has no migration that added them) and will likely fail or
prompt confusingly, since the columns already exist physically. Don't
run `prisma migrate dev` against this database without reconciling that
first — either accept Prisma's drift-resolution flow explicitly, or
retire the Prisma stack entirely per Task 16 before touching it again.

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
