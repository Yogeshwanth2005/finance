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
## Insurance-Plan Document Intelligence & RAG Chatbot (COMPLETED — 2026-09-20)
Integrated SurakshaCFO RAG document extraction, deterministic 128-dim vector embedding, and regulatory guardrails into Fin v2.

| Area | Features | Status |
|---|---|---|
| RAG Core (`backend/app/services/rag/`) | Multi-format text extraction (`pypdf`, `docx`, `txt`), rolling chunker (900 words / 120 overlap), deterministic SHA256 unit-normalized 128-dim embeddings, and cosine similarity | **Done** — 5 pytest tests passing |
| Regulatory Guardrails (`backend/app/services/rag/guardrails.py`) | Hard pre-retrieval refusal for advice/comparison/ranking questions per Fin Invariant 4 | **Done** — Tested and verified |
| Database Models & Migrations (`backend/app/models.py`, `backend/alembic/`) | `InsuranceDocument`, `InsuranceDocumentChunk`, and `InsuranceChatMessage` with camelCase mapping and Alembic migration `a1f8c9e0d1b2` | **Done** — 3 pytest tests passing |
| API Router (`backend/app/routers/rag.py`) | `GET /api/insurance/rag/documents`, `POST /api/insurance/rag/chat`, `POST /api/insurance/rag/ingest` | **Done** — 4 pytest tests passing |
| Frontend UI (`frontend/src/`) | `PolicyDrawer.jsx` slide-over clause inspection drawer with live clause retrieval, similarity scoring, and regulatory refusal alerts, integrated with `InsuranceCard.jsx` and `Dashboard.jsx` | **Done** — 12 Vitest tests passing |

- **Fund return-history fact fields + daily auto-refresh** — idea
  captured 2026-09-18, not yet designed. Extend `FundReference` with
  since-inception, 1yr, 3yr, and 5yr trailing return % fields (same
  "plain fact field" category as the existing `aumCr` — display only,
  **never used to sort/rank the fund list**, per Invariant 4).

## Known Tech Debt
- **Supabase direct raw TCP ports (5432/6543)**: On networks with restricted outbound TCP ports, local development can use SQLite (`sqlite+aiosqlite:///./fin_app.db`) or the Supabase HTTPS REST API / MCP tools for direct DB interactions.
