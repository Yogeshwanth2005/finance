# Active Roadmap & Technical Debt

## Python/FastAPI + React Rewrite (COMPLETED — 2026-09-19)
Full rewrite per `docs/superpowers/specs/2026-09-17-python-fastapi-react-rewrite-design.md`
and `docs/superpowers/plans/2026-09-17-python-fastapi-react-rewrite.md`.

| Tasks | Area | Status |
|---|---|---|
| 1-9 | Backend (`backend/`): FastAPI scaffold, SQLAlchemy models with quoted camelCase mapping, gap-analysis/allocation/insurance-matching engines, demo-user cookie, onboarding + dashboard routers, seed script | **Done** — 42 pytest tests passing; verified end-to-end against live calculations, including `DEMO_MODE=false` compliance gate |
| 10-15 | Frontend (`frontend/`): Vite/React 18 SPA scaffold, disclaimer gate, 5-step onboarding wizard, review screen with ₹-formatting, dashboard with 5 KPI ring meters, asset allocation snapshot, and gated comparison cards | **Done** — 12 Vitest tests passing; production build clean |
| 16 | Manual parity verification + cutover | **Done** — Backend test suite (42 tests) and frontend test suite (12 tests) passing; legacy Next.js/Prisma files (`src/`, `prisma/`, `next.config.ts`, `tsconfig.json`, `eslint.config.mjs`, `postcss.config.mjs`) retired; second-brain updated |

---

## Proposed / Not Yet Scoped
- **SIP management (CAS import, view-only)** — new feature, not part of
  implementationplanv2.md's original Task 1-10 build order. Brainstorming
  paused 2026-09-17 pending a decision on CAS parser format scope — see
  decisions/log.md's 2026-09-17 entry for the full narrowing history
  before resuming this conversation. No design doc, schema, or code
  exists yet.
- **Insurance-plan document intelligence + Q&A chatbot** — idea captured
  2026-09-18, scope narrowed same day, not yet designed. Since insurance
  plans can't be fetched via an API, the idea is: (1) ingest a plan's
  official policy-wordings PDF for any new health/term plan and
  extract/summarize the info that actually matters (coverage, exclusions,
  waiting periods, claim process, etc.) instead of a human reading the
  full document, and (2) a chatbot over that ingested doc set so users
  can ask **factual questions about a single plan** ("does this cover
  maternity," "what's the waiting period," "how do I file a claim") and
  get answers in plain language, grounded/citable back to the source
  document. Effectively a RAG pipeline (doc ingestion + chunking +
  retrieval + LLM answer synthesis) layered on top of
  `insurance_plan_reference`.
  **Explicitly out of scope** (per user, 2026-09-18): comparing plans or
  recommending which plan to choose — this is plan-fact lookup only, not
  advice. That scope boundary is what keeps this out of `DEMO_MODE`
  advice-liability territory; the bot needs a hard refusal path for any
  "which plan is better for me" style question rather than answering it,
  to keep that boundary enforced at runtime, not just on paper.
- **Fund return-history fact fields + daily auto-refresh** — idea
  captured 2026-09-18, not yet designed. Extend `FundReference` with
  since-inception, 1yr, 3yr, and 5yr trailing return % fields (same
  "plain fact field" category as the existing `aumCr` — display only,
  **never used to sort/rank the fund list**, per Invariant 4).

## Known Tech Debt
- **Supabase direct raw TCP ports (5432/6543)**: On networks with restricted outbound TCP ports, local development can use SQLite (`sqlite+aiosqlite:///./fin_app.db`) or the Supabase HTTPS REST API / MCP tools for direct DB interactions.
