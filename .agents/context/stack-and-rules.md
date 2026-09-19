# Invariants, Tech Stack & File Map

## Tech Stack
- Frontend: Vite + React 18 + Tailwind CSS 4 (`frontend/src/`)
- Backend: Python 3.12 + FastAPI + SQLAlchemy 2.0 (`backend/app/`)
- Database: PostgreSQL via **Supabase**, with Alembic migrations (`backend/alembic/`) and SQLite support for offline dev/tests
- Auth / Session: Demo user session via `fin_demo_user_id` cookie (HttpOnly, SameSite=Lax)
- Testing: `pytest` for backend (42 tests), `vitest` for frontend (12 tests)
- No ML libraries, no LLM API calls anywhere in the core engines — every financial calculation is deterministic (implementationplanv2.md Section 1)

## Hard Invariants
1. **Quoted Column Names in SQLAlchemy**: Postgres schema columns use camelCase (`"monthlyIncome"`, `"emergencyFundMonths"`). All SQLAlchemy models in `backend/app/models.py` map to exact quoted names matching the PostgreSQL database schema.
2. **`DEMO_MODE` Regulatory Compliance Gate** (`backend/app/config.py`): Sections 5.2/6.2/6.3 (named fund and insurance plan examples) must stay strictly behind this boolean flag. Showing named financial products without SEBI RIA / IRDAI web-aggregator licensing is only permitted while this stays a private portfolio/educational demo. When `DEMO_MODE=false`, named fund and insurance examples are completely omitted from both the raw `GET /api/dashboard` JSON response and UI rendering.
3. **No ML/LLM Calls in Core Engine**: `gap_analysis.py`, `allocation.py`, and `insurance_matching.py` logic are pure, deterministic functions.
4. **Rule-Based Reference Matching**: Fund/insurance example selection is rule-based (sorted by AUM / sum-assured proximity) — never a ranked "best pick" or subjective score, to avoid crossing into personalized advice liabilities under SEBI/IRDAI regulations.

## File Map
- `backend/app/config.py` — editable tunable constants & `DEMO_MODE` gate
- `backend/app/db.py` — SQLAlchemy async engine and session dependency
- `backend/app/models.py` — SQLAlchemy ORM models matching database schema
- `backend/app/demo_user.py` — demo session tracking via `fin_demo_user_id` cookie
- `backend/app/services/gap_analysis.py` (+ `tests/test_gap_analysis.py`) — deterministic gap analysis engine
- `backend/app/services/allocation.py` (+ `tests/test_allocation.py`) — asset allocation engine
- `backend/app/services/insurance_matching.py` (+ `tests/test_insurance_matching.py`) — insurance reference matcher
- `backend/app/routers/onboarding.py` — `POST /api/onboarding/submit` endpoint
- `backend/app/routers/dashboard.py` — `GET /api/dashboard` endpoint
- `backend/app/seed.py` — AMFI mutual funds and insurance reference seeder
- `frontend/src/App.jsx` — React Router SPA shell
- `frontend/src/pages/Home.jsx` — landing page
- `frontend/src/pages/Onboarding.jsx` — disclaimer gate (Section 3)
- `frontend/src/pages/onboarding/OnboardingWizard.jsx` — 5-step onboarding intake wizard
- `frontend/src/pages/onboarding/screens.jsx` — individual wizard step forms and validators
- `frontend/src/pages/Dashboard.jsx` — dashboard rendering 5 KPI ring meters, asset allocation snapshot, and `DEMO_MODE`-gated comparison cards
- `frontend/src/components/KpiCard.jsx`, `FundCard.jsx`, `InsuranceCard.jsx` — dashboard card components
- `frontend/src/lib/format.js` — Indian numbering / Rupee currency formatting utilities
- `implementationplanv2.md` — full product spec and regulatory reasoning
