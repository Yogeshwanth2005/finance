# Python/FastAPI + React Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the Fin app's backend in Python (FastAPI) and frontend in React with plain JavaScript (no TypeScript), reproducing the existing onboarding/gap-analysis/allocation/dashboard feature set 1:1 against the same Supabase Postgres database.

**Architecture:** Two independently deployable apps in the same repo: `backend/` (FastAPI + SQLAlchemy, JSON REST API) and `frontend/` (Vite + React JS, SPA). Cross-origin httpOnly cookie identifies the demo user, same pattern as today's `src/lib/demo-user.ts` but adapted for two origins.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, psycopg (v3), pytest, httpx — Vite, React 18 (`.jsx`, no TypeScript), react-router-dom, Vitest + React Testing Library.

**Spec:** `docs/superpowers/specs/2026-09-17-python-fastapi-react-rewrite-design.md`

## Global Constraints

- No TypeScript anywhere in `backend/` or `frontend/` — Python and plain JS/JSX only.
- No ML/LLM calls — gap-analysis, allocation, and insurance-matching logic stay pure/deterministic functions (mirrors `stack-and-rules.md` hard invariant #3).
- `DEMO_MODE` gate (`backend/app/config.py`) must fully omit named fund/insurance data from JSON responses when `False`, not just hide it client-side (hard invariant #4, and the trap noted in `subsystem-notes.md`).
- Fund/insurance example selection stays rule-based (AUM / sum-assured proximity sort) — never a ranked "best pick" (hard invariant #5). The insurance comparison table shows plain facts only, no ranking signal.
- Reuse the existing Supabase Postgres database and schema as-is — SQLAlchemy models must mirror `prisma/schema.prisma` exactly, including exact camelCase column names (Prisma does not snake_case columns; every column is a quoted camelCase identifier in Postgres, e.g. `"userId"`, `"monthlyIncome"`).
- Business logic values (multipliers, thresholds) must match `backend/app/config.py`'s port of `src/lib/config.ts` exactly — do not invent new defaults.
- Don't delete `src/`, `prisma/`, or Next.js config until Task 16 (final cutover) — earlier tasks build alongside the existing app.

## File Structure

```
backend/
  requirements.txt
  .env                      # copied from repo-root .env values (not committed)
  alembic.ini
  alembic/
    env.py
    versions/
  app/
    __init__.py
    main.py                 # FastAPI app, CORS
    config.py                # port of src/lib/config.ts
    db.py                     # SQLAlchemy engine/session, pgbouncer-safe
    models.py                 # SQLAlchemy models mirroring prisma/schema.prisma
    demo_user.py               # port of src/lib/demo-user.ts
    services/
      __init__.py
      gap_analysis.py          # port of src/lib/gap-analysis.ts
      allocation.py             # port of src/lib/allocation.ts
      insurance_matching.py      # port of src/lib/insurance-matching.ts
    routers/
      __init__.py
      onboarding.py              # port of src/app/api/onboarding/submit/route.ts
      dashboard.py                # new: GET /api/dashboard (was server-side in page.tsx)
    seed.py                        # port of prisma/seed.ts
  tests/
    conftest.py
    test_gap_analysis.py
    test_allocation.py
    test_insurance_matching.py
    test_onboarding_router.py
    test_dashboard_router.py

frontend/
  package.json
  vite.config.js
  index.html
  src/
    main.jsx
    App.jsx                    # routes + DisclaimerBanner layout, port of layout.tsx
    index.css                  # Tailwind entry, port of globals.css
    api/
      client.js                 # fetch wrapper, credentials: 'include'
    lib/
      format.js                  # port of src/lib/format.ts
    components/
      DisclaimerBanner.jsx
      KpiCard.jsx
      FundCard.jsx
      InsuranceCard.jsx           # + InsuranceComparisonTable
    pages/
      Home.jsx                     # port of src/app/page.tsx
      Onboarding.jsx                 # port of src/app/onboarding/page.tsx (disclaimer gate)
      onboarding/
        screens.jsx                  # port of screens.tsx (validators + step components)
        OnboardingWizard.jsx          # port of profile/page.tsx (wizard shell)
      Dashboard.jsx                   # port of dashboard/page.tsx, fetches GET /api/dashboard
    __tests__/
      screens.test.jsx
      Dashboard.test.jsx
```

---

### Task 1: Backend scaffold — requirements, config, DB engine, FastAPI app

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env` (values copied from repo-root `.env` — do not commit; add `backend/.env` to `.gitignore`)
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_main.py`

**Interfaces:**
- Produces: `app.config.DEMO_MODE: bool`, `app.config.EMERGENCY_FUND_MULTIPLIER`, `app.config.INCOME_REPLACEMENT_MULTIPLIER`, `app.config.HEALTH_COVER_BASELINE`, `app.config.BASE_EQUITY_AGE_CONSTANT`, `app.config.RISK_TOLERANCE_MULTIPLIERS: dict[str, float]`, `app.config.SHORT_HORIZON_THRESHOLD`, `app.config.SHORT_HORIZON_SHIFT`, `app.config.GOLD_ALLOCATION_PCT`, `app.config.FUND_EXAMPLES_PER_CATEGORY`, `app.config.INSURANCE_EXAMPLES_PER_GAP_TYPE`. `app.db.SessionLocal` (sessionmaker), `app.db.get_db()` (FastAPI dependency yielding a session). `app.main.app` (FastAPI instance).

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
psycopg[binary]==3.2.3
alembic==1.14.0
pydantic==2.9.2
python-dotenv==1.0.1
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Create `backend/.env`**

Copy `DATABASE_URL` and `DIRECT_URL` verbatim from the repo-root `.env` file (same Supabase pooled/direct connection strings the current app uses — do not change the values or ports). Add one line:

```
DEMO_MODE=true
```

Then add `backend/.env` to the repo's `.gitignore` if not already covered by an existing `.env` ignore rule.

- [ ] **Step 3: Write `backend/app/config.py`**

Direct port of `src/lib/config.ts`'s values (verify against that file — do not re-derive):

```python
import os

DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() == "true"

EMERGENCY_FUND_MULTIPLIER = 6
INCOME_REPLACEMENT_MULTIPLIER = 10
HEALTH_COVER_BASELINE = 500_000
HIGH_INTEREST_DEBT_THRESHOLD = 12

BASE_EQUITY_AGE_CONSTANT = 100
RISK_TOLERANCE_MULTIPLIERS = {
    "conservative": 0.8,
    "moderate": 1.0,
    "aggressive": 1.2,
}
SHORT_HORIZON_THRESHOLD = 3
SHORT_HORIZON_SHIFT = 20
GOLD_ALLOCATION_PCT = 10

FUND_EXAMPLES_PER_CATEGORY = 3
INSURANCE_EXAMPLES_PER_GAP_TYPE = 2
```

- [ ] **Step 4: Write `backend/app/db.py`**

`DATABASE_URL` points at Supabase's transaction-mode pgbouncer pooler (port 6543), which does not support server-side prepared statements — psycopg3 must disable them via `prepare_threshold=None`, and the pool must not hold persistent server-side state across the pooler, so use `NullPool`. This mirrors the same class of load-bearing connection-config detail as the Prisma driver-adapter requirement in `stack-and-rules.md`.

```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    connect_args={"prepare_threshold": None},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Write `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Fin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Write the smoke test `backend/tests/test_main.py`**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 7: Install dependencies and run the test**

Run: `cd backend && pip install -r requirements.txt && pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/app/config.py backend/app/db.py backend/app/main.py backend/app/__init__.py backend/tests/test_main.py .gitignore
git commit -m "feat: scaffold FastAPI backend with config, DB engine, health check"
```

---

### Task 2: SQLAlchemy models mirroring `prisma/schema.prisma`

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `app.db.Base` (from Task 1)
- Produces: `app.models.User`, `FinancialProfile`, `ExistingDebt`, `InsuranceProfile`, `AllocationResult`, `GapAnalysisResult`, `FundReference`, `InsurancePlanReference` — SQLAlchemy ORM classes with `__tablename__` matching Prisma's `@@map(...)` values, and every column name matching Prisma's exact camelCase field name (Postgres columns are quoted camelCase identifiers, not snake_case — Prisma does not `@map` individual fields in this schema).

- [ ] **Step 1: Write `backend/app/models.py`**

Every `Numeric` precision/scale below matches the `@db.Decimal(p, s)` annotation on the corresponding Prisma field exactly. Every Postgres enum type name matches the Prisma enum name exactly (Prisma creates a native enum type named after the enum, unmapped) — `create_type=False` because the type already exists from the Prisma migration; do not let SQLAlchemy try to create it.

```python
import uuid
from datetime import datetime, date

from sqlalchemy import (
    String, Integer, Numeric, DateTime, Date, ForeignKey, JSON, Index,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


def _new_id() -> str:
    return str(uuid.uuid4())


RiskTolerance = ENUM(
    "conservative", "moderate", "aggressive",
    name="RiskTolerance", create_type=False,
)
EmergencyFundStatus = ENUM(
    "inadequate", "building", "adequate",
    name="EmergencyFundStatus", create_type=False,
)
FundCategory = ENUM(
    "equity_large_cap", "equity_diversified", "debt_short_duration",
    "fixed_deposit", "gold_etf", "sovereign_gold_bond",
    name="FundCategory", create_type=False,
)
InsurancePlanType = ENUM(
    "term", "health", name="InsurancePlanType", create_type=False,
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column("id", String, primary_key=True, default=_new_id)
    email: Mapped[str] = mapped_column("email", String, unique=True)
    name: Mapped[str | None] = mapped_column("name", String, nullable=True)
    hashedPassword: Mapped[str | None] = mapped_column("hashedPassword", String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FinancialProfile(Base):
    __tablename__ = "financial_profile"

    id: Mapped[str] = mapped_column("id", String, primary_key=True, default=_new_id)
    userId: Mapped[str] = mapped_column("userId", String, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    age: Mapped[int] = mapped_column("age", Integer)
    dependentsCount: Mapped[int] = mapped_column("dependentsCount", Integer, default=0)
    monthlyIncome: Mapped[float] = mapped_column("monthlyIncome", Numeric(14, 2))
    monthlyExpenses: Mapped[float] = mapped_column("monthlyExpenses", Numeric(14, 2))
    currentSavings: Mapped[float] = mapped_column("currentSavings", Numeric(14, 2))
    riskTolerance: Mapped[str] = mapped_column("riskTolerance", RiskTolerance)
    investmentHorizonYears: Mapped[int] = mapped_column("investmentHorizonYears", Integer)
    consentGivenAt: Mapped[datetime | None] = mapped_column("consentGivenAt", DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    existingDebts: Mapped[list["ExistingDebt"]] = relationship(back_populates="financialProfile", cascade="all, delete-orphan")


class ExistingDebt(Base):
    __tablename__ = "existing_debt"

    id: Mapped[str] = mapped_column("id", String, primary_key=True, default=_new_id)
    financialProfileId: Mapped[str] = mapped_column("financialProfileId", String, ForeignKey("financial_profile.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column("label", String)
    outstandingAmount: Mapped[float] = mapped_column("outstandingAmount", Numeric(14, 2))
    interestRatePct: Mapped[float] = mapped_column("interestRatePct", Numeric(5, 2))
    tenureMonths: Mapped[int] = mapped_column("tenureMonths", Integer)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())

    financialProfile: Mapped["FinancialProfile"] = relationship(back_populates="existingDebts")


class InsuranceProfile(Base):
    __tablename__ = "insurance_profile"

    id: Mapped[str] = mapped_column("id", String, primary_key=True, default=_new_id)
    userId: Mapped[str] = mapped_column("userId", String, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    existingTermCoverAmount: Mapped[float] = mapped_column("existingTermCoverAmount", Numeric(14, 2), default=0)
    personalHealthCoverAmount: Mapped[float] = mapped_column("personalHealthCoverAmount", Numeric(14, 2), default=0)
    employerHealthCoverAmount: Mapped[float] = mapped_column("employerHealthCoverAmount", Numeric(14, 2), default=0)
    consentGivenAt: Mapped[datetime | None] = mapped_column("consentGivenAt", DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AllocationResult(Base):
    __tablename__ = "allocation_results"
    __table_args__ = (Index("ix_allocation_results_userId_computedAt", "userId", "computedAt"),)

    id: Mapped[str] = mapped_column("id", String, primary_key=True, default=_new_id)
    userId: Mapped[str] = mapped_column("userId", String, ForeignKey("users.id", ondelete="CASCADE"))
    equityPct: Mapped[float] = mapped_column("equityPct", Numeric(5, 2))
    debtPct: Mapped[float] = mapped_column("debtPct", Numeric(5, 2))
    goldPct: Mapped[float] = mapped_column("goldPct", Numeric(5, 2))
    computedAt: Mapped[datetime] = mapped_column("computedAt", DateTime(timezone=True), server_default=func.now())


class GapAnalysisResult(Base):
    __tablename__ = "gap_analysis_results"
    __table_args__ = (Index("ix_gap_analysis_results_userId_computedAt", "userId", "computedAt"),)

    id: Mapped[str] = mapped_column("id", String, primary_key=True, default=_new_id)
    userId: Mapped[str] = mapped_column("userId", String, ForeignKey("users.id", ondelete="CASCADE"))
    emergencyFundTarget: Mapped[float] = mapped_column("emergencyFundTarget", Numeric(14, 2))
    emergencyFundCurrent: Mapped[float] = mapped_column("emergencyFundCurrent", Numeric(14, 2))
    emergencyFundStatus: Mapped[str] = mapped_column("emergencyFundStatus", EmergencyFundStatus)
    debtPriorityOrder: Mapped[list] = mapped_column("debtPriorityOrder", JSON)
    termCoverGap: Mapped[float] = mapped_column("termCoverGap", Numeric(14, 2))
    healthCoverGap: Mapped[float] = mapped_column("healthCoverGap", Numeric(14, 2))
    emergencyFundCoveragePct: Mapped[float] = mapped_column("emergencyFundCoveragePct", Numeric(7, 2))
    termCoverAdequacyPct: Mapped[float] = mapped_column("termCoverAdequacyPct", Numeric(7, 2))
    healthCoverAdequacyPct: Mapped[float] = mapped_column("healthCoverAdequacyPct", Numeric(7, 2))
    savingsRatePct: Mapped[float] = mapped_column("savingsRatePct", Numeric(7, 2))
    debtToIncomePct: Mapped[float] = mapped_column("debtToIncomePct", Numeric(7, 2))
    computedAt: Mapped[datetime] = mapped_column("computedAt", DateTime(timezone=True), server_default=func.now())


class FundReference(Base):
    __tablename__ = "fund_reference"
    __table_args__ = (Index("ix_fund_reference_category", "category"),)

    id: Mapped[str] = mapped_column("id", String, primary_key=True, default=_new_id)
    schemeCode: Mapped[str] = mapped_column("schemeCode", String, unique=True)
    schemeName: Mapped[str] = mapped_column("schemeName", String)
    amcName: Mapped[str] = mapped_column("amcName", String)
    category: Mapped[str] = mapped_column("category", FundCategory)
    expenseRatio: Mapped[float] = mapped_column("expenseRatio", Numeric(5, 2))
    aumCr: Mapped[float] = mapped_column("aumCr", Numeric(12, 2))
    latestNav: Mapped[float] = mapped_column("latestNav", Numeric(10, 4))
    navDate: Mapped[date] = mapped_column("navDate", Date)
    externalUrl: Mapped[str] = mapped_column("externalUrl", String)
    lastSyncedAt: Mapped[datetime] = mapped_column("lastSyncedAt", DateTime(timezone=True), server_default=func.now())


class InsurancePlanReference(Base):
    __tablename__ = "insurance_plan_reference"
    __table_args__ = (Index("ix_insurance_plan_reference_planType", "planType"),)

    id: Mapped[str] = mapped_column("id", String, primary_key=True, default=_new_id)
    insurerName: Mapped[str] = mapped_column("insurerName", String)
    planName: Mapped[str] = mapped_column("planName", String)
    planType: Mapped[str] = mapped_column("planType", InsurancePlanType)
    sumAssuredMin: Mapped[float] = mapped_column("sumAssuredMin", Numeric(14, 2))
    sumAssuredMax: Mapped[float] = mapped_column("sumAssuredMax", Numeric(14, 2))
    indicativePremiumNote: Mapped[str] = mapped_column("indicativePremiumNote", String)
    claimSettlementRatioPct: Mapped[float] = mapped_column("claimSettlementRatioPct", Numeric(5, 2))
    avgClaimSettlementDays: Mapped[int] = mapped_column("avgClaimSettlementDays", Integer)
    keyFeatures: Mapped[list] = mapped_column("keyFeatures", JSON)
    externalUrl: Mapped[str] = mapped_column("externalUrl", String)
    lastUpdatedAt: Mapped[datetime] = mapped_column("lastUpdatedAt", DateTime(timezone=True), server_default=func.now())
    sourceNote: Mapped[str] = mapped_column("sourceNote", String)
```

- [ ] **Step 2: Write `backend/tests/test_models.py`** — verifies the models import cleanly and table/column names match Prisma's mapping (this is a static-shape check, not a DB-hitting test, so it runs without network access)

```python
from app.models import User, FinancialProfile, ExistingDebt, InsuranceProfile, AllocationResult, GapAnalysisResult, FundReference, InsurancePlanReference


def test_table_names_match_prisma_map():
    assert User.__tablename__ == "users"
    assert FinancialProfile.__tablename__ == "financial_profile"
    assert ExistingDebt.__tablename__ == "existing_debt"
    assert InsuranceProfile.__tablename__ == "insurance_profile"
    assert AllocationResult.__tablename__ == "allocation_results"
    assert GapAnalysisResult.__tablename__ == "gap_analysis_results"
    assert FundReference.__tablename__ == "fund_reference"
    assert InsurancePlanReference.__tablename__ == "insurance_plan_reference"


def test_financial_profile_column_names_are_exact_camel_case():
    columns = {c.name for c in FinancialProfile.__table__.columns}
    assert "monthlyIncome" in columns
    assert "investmentHorizonYears" in columns
    assert "monthly_income" not in columns
```

- [ ] **Step 3: Run the test**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 4: Set up Alembic pointed at `DIRECT_URL`, and stamp the existing schema as the baseline (do not create tables — they already exist)**

Run: `cd backend && alembic init alembic`

Edit `backend/alembic.ini`: set `sqlalchemy.url` to a placeholder (overridden in `env.py`).

Edit `backend/alembic/env.py` — add near the top, after the existing imports:

```python
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from app.db import Base
from app import models  # noqa: F401 — registers models on Base.metadata

target_metadata = Base.metadata
```

Find the line `config.set_main_option("sqlalchemy.url", ...)` or the `run_migrations_online`/`run_migrations_offline` functions, and set the URL from `DIRECT_URL` (session-mode pooler, required for DDL — same reasoning as `prisma.config.ts`'s split between `DATABASE_URL` and `DIRECT_URL`):

```python
config.set_main_option("sqlalchemy.url", os.environ["DIRECT_URL"])
```

Run: `cd backend && alembic revision --autogenerate -m "baseline: mirror existing prisma schema"`

Inspect the generated migration file in `backend/alembic/versions/` — it should show no `op.create_table` calls that would recreate existing tables (the schema already exists via Prisma's migration). If it does propose creating tables, that means a models.py column/type mismatch against the live DB — stop and reconcile column types/names against `prisma/schema.prisma` before proceeding.

Run: `cd backend && alembic stamp head`

This marks the current DB as already being at this revision without running any DDL — required because Prisma, not Alembic, created these tables.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py backend/alembic.ini backend/alembic/
git commit -m "feat: add SQLAlchemy models mirroring prisma schema, stamp Alembic baseline"
```

---

### Task 3: Port the gap-analysis engine (`src/lib/gap-analysis.ts` → `backend/app/services/gap_analysis.py`)

**Files:**
- Create: `backend/app/services/__init__.py` (empty)
- Create: `backend/app/services/gap_analysis.py`
- Test: `backend/tests/test_gap_analysis.py`

**Interfaces:**
- Consumes: `app.config.EMERGENCY_FUND_MULTIPLIER`, `INCOME_REPLACEMENT_MULTIPLIER`, `HEALTH_COVER_BASELINE` (Task 1)
- Produces: `calculate_emi(outstanding_amount, interest_rate_pct, tenure_months) -> float`, `prioritize_debts(debts: list[dict]) -> list[str]`, `compute_emergency_fund(monthly_expenses, current_savings) -> dict`, `compute_term_cover_gap(annual_income, existing_term_cover_amount) -> dict`, `compute_health_cover_gap(personal_health_cover_amount, employer_health_cover_amount) -> dict`, `compute_kpis(**kwargs) -> dict`, `compute_gap_analysis(**kwargs) -> dict` — used by `routers/onboarding.py` (Task 7)

- [ ] **Step 1: Write the failing tests in `backend/tests/test_gap_analysis.py`** — ported 1:1 from `src/lib/gap-analysis.test.ts`'s expected values

```python
import pytest
from app.services.gap_analysis import (
    calculate_emi, prioritize_debts, compute_emergency_fund,
    compute_term_cover_gap, compute_health_cover_gap, compute_kpis,
    compute_gap_analysis,
)


def test_calculate_emi_standard_amortized():
    emi = calculate_emi(outstanding_amount=100000, interest_rate_pct=12, tenure_months=12)
    assert emi == pytest.approx(8884.88, abs=0.1)


def test_calculate_emi_zero_interest_falls_back_to_straight_line():
    emi = calculate_emi(outstanding_amount=120000, interest_rate_pct=0, tenure_months=12)
    assert emi == pytest.approx(10000, abs=0.00001)


def test_prioritize_debts_orders_highest_interest_first():
    order = prioritize_debts([
        {"id": "car-loan", "outstanding_amount": 300000, "interest_rate_pct": 9, "tenure_months": 48},
        {"id": "credit-card", "outstanding_amount": 50000, "interest_rate_pct": 36, "tenure_months": 12},
        {"id": "personal-loan", "outstanding_amount": 100000, "interest_rate_pct": 14, "tenure_months": 24},
    ])
    assert order == ["credit-card", "personal-loan", "car-loan"]


def test_prioritize_debts_empty():
    assert prioritize_debts([]) == []


def test_emergency_fund_target_is_six_months_expenses():
    result = compute_emergency_fund(monthly_expenses=40000, current_savings=0)
    assert result["target"] == 240000


def test_emergency_fund_adequate_at_target():
    result = compute_emergency_fund(monthly_expenses=40000, current_savings=240000)
    assert result["status"] == "adequate"


def test_emergency_fund_inadequate_below_half():
    result = compute_emergency_fund(monthly_expenses=40000, current_savings=100000)
    assert result["status"] == "inadequate"


def test_emergency_fund_building_between_half_and_full():
    result = compute_emergency_fund(monthly_expenses=40000, current_savings=180000)
    assert result["status"] == "building"


def test_term_cover_gap_ten_times_annual_income():
    result = compute_term_cover_gap(annual_income=600000, existing_term_cover_amount=2000000)
    assert result["recommended_term_cover"] == 6000000
    assert result["gap"] == 4000000


def test_term_cover_gap_clamped_to_zero():
    result = compute_term_cover_gap(annual_income=600000, existing_term_cover_amount=9000000)
    assert result["gap"] == 0


def test_health_cover_gap_sums_personal_and_employer():
    result = compute_health_cover_gap(personal_health_cover_amount=200000, employer_health_cover_amount=100000)
    assert result["effective_existing_cover"] == 300000
    assert result["recommended_health_cover"] == 500000
    assert result["gap"] == 200000


def test_health_cover_gap_clamped_to_zero():
    result = compute_health_cover_gap(personal_health_cover_amount=400000, employer_health_cover_amount=300000)
    assert result["gap"] == 0


def test_compute_kpis_all_five_percentages():
    result = compute_kpis(
        emergency_fund_current=180000, emergency_fund_target=240000,
        existing_term_cover_amount=2000000, recommended_term_cover=6000000,
        effective_existing_cover=300000, recommended_health_cover=500000,
        monthly_income=50000, monthly_expenses=40000,
        debts=[{"id": "credit-card", "outstanding_amount": 100000, "interest_rate_pct": 12, "tenure_months": 12}],
    )
    assert result["emergency_fund_coverage_pct"] == pytest.approx(75, abs=0.00001)
    assert result["term_cover_adequacy_pct"] == pytest.approx(33.33, abs=0.1)
    assert result["health_cover_adequacy_pct"] == pytest.approx(60, abs=0.00001)
    assert result["savings_rate_pct"] == pytest.approx(20, abs=0.00001)
    assert result["debt_to_income_pct"] == pytest.approx(17.77, abs=0.1)


def test_compute_kpis_sums_emi_across_debts():
    result = compute_kpis(
        emergency_fund_current=0, emergency_fund_target=1,
        existing_term_cover_amount=0, recommended_term_cover=1,
        effective_existing_cover=0, recommended_health_cover=1,
        monthly_income=50000, monthly_expenses=0,
        debts=[
            {"id": "a", "outstanding_amount": 120000, "interest_rate_pct": 0, "tenure_months": 12},
            {"id": "b", "outstanding_amount": 120000, "interest_rate_pct": 0, "tenure_months": 12},
        ],
    )
    assert result["debt_to_income_pct"] == pytest.approx(40, abs=0.00001)


def test_compute_gap_analysis_composes_all_layers():
    result = compute_gap_analysis(
        monthly_income=50000, monthly_expenses=40000, current_savings=180000,
        existing_term_cover_amount=2000000, personal_health_cover_amount=200000,
        employer_health_cover_amount=100000,
        debts=[
            {"id": "credit-card", "outstanding_amount": 100000, "interest_rate_pct": 12, "tenure_months": 12},
            {"id": "car-loan", "outstanding_amount": 300000, "interest_rate_pct": 9, "tenure_months": 48},
        ],
    )
    assert result["emergency_fund_target"] == 240000
    assert result["emergency_fund_current"] == 180000
    assert result["emergency_fund_status"] == "building"
    assert result["debt_priority_order"] == ["credit-card", "car-loan"]
    assert result["term_cover_gap"] == 4000000
    assert result["health_cover_gap"] == 200000
    assert result["emergency_fund_coverage_pct"] == pytest.approx(75, abs=0.00001)
    assert result["savings_rate_pct"] == pytest.approx(20, abs=0.00001)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_gap_analysis.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.gap_analysis'`

- [ ] **Step 3: Write `backend/app/services/gap_analysis.py`** — direct port of `src/lib/gap-analysis.ts`, same formulas, same "no v1 source" call-outs preserved as comments

```python
from app.config import (
    EMERGENCY_FUND_MULTIPLIER, INCOME_REPLACEMENT_MULTIPLIER, HEALTH_COVER_BASELINE,
)


def calculate_emi(outstanding_amount: float, interest_rate_pct: float, tenure_months: int) -> float:
    monthly_rate = interest_rate_pct / 12 / 100
    if monthly_rate == 0:
        return outstanding_amount / tenure_months
    growth = (1 + monthly_rate) ** tenure_months
    return (outstanding_amount * monthly_rate * growth) / (growth - 1)


def prioritize_debts(debts: list[dict]) -> list[str]:
    return [d["id"] for d in sorted(debts, key=lambda d: d["interest_rate_pct"], reverse=True)]


# No v1 source for the status thresholds (see decisions/log.md); halfway
# to target is the dividing line between "inadequate" and "building".
def compute_emergency_fund(monthly_expenses: float, current_savings: float) -> dict:
    target = monthly_expenses * EMERGENCY_FUND_MULTIPLIER
    if current_savings >= target:
        status = "adequate"
    elif current_savings >= target / 2:
        status = "building"
    else:
        status = "inadequate"
    return {"target": target, "current": current_savings, "status": status}


def compute_term_cover_gap(annual_income: float, existing_term_cover_amount: float) -> dict:
    recommended_term_cover = annual_income * INCOME_REPLACEMENT_MULTIPLIER
    return {
        "recommended_term_cover": recommended_term_cover,
        "gap": max(0, recommended_term_cover - existing_term_cover_amount),
    }


# No v1 source for how personal + employer cover combine (see
# decisions/log.md); treated as a straight sum.
def compute_health_cover_gap(personal_health_cover_amount: float, employer_health_cover_amount: float) -> dict:
    effective_existing_cover = personal_health_cover_amount + employer_health_cover_amount
    recommended_health_cover = HEALTH_COVER_BASELINE
    return {
        "effective_existing_cover": effective_existing_cover,
        "recommended_health_cover": recommended_health_cover,
        "gap": max(0, recommended_health_cover - effective_existing_cover),
    }


def compute_kpis(
    emergency_fund_current: float, emergency_fund_target: float,
    existing_term_cover_amount: float, recommended_term_cover: float,
    effective_existing_cover: float, recommended_health_cover: float,
    monthly_income: float, monthly_expenses: float, debts: list[dict],
) -> dict:
    total_emi = sum(calculate_emi(d["outstanding_amount"], d["interest_rate_pct"], d["tenure_months"]) for d in debts)
    return {
        "emergency_fund_coverage_pct": (emergency_fund_current / emergency_fund_target) * 100,
        "term_cover_adequacy_pct": (existing_term_cover_amount / recommended_term_cover) * 100,
        "health_cover_adequacy_pct": (effective_existing_cover / recommended_health_cover) * 100,
        "savings_rate_pct": ((monthly_income - monthly_expenses) / monthly_income) * 100,
        "debt_to_income_pct": (total_emi / monthly_income) * 100,
    }


# Composes 4.1-4.4 (emergency fund, debt priority, term/health gap) with
# the 4.5 KPI layer into the shape gap_analysis_results persists.
def compute_gap_analysis(
    monthly_income: float, monthly_expenses: float, current_savings: float,
    existing_term_cover_amount: float, personal_health_cover_amount: float,
    employer_health_cover_amount: float, debts: list[dict],
) -> dict:
    emergency_fund = compute_emergency_fund(monthly_expenses, current_savings)
    term_cover = compute_term_cover_gap(monthly_income * 12, existing_term_cover_amount)
    health_cover = compute_health_cover_gap(personal_health_cover_amount, employer_health_cover_amount)
    debt_priority_order = prioritize_debts(debts)
    kpis = compute_kpis(
        emergency_fund_current=emergency_fund["current"],
        emergency_fund_target=emergency_fund["target"],
        existing_term_cover_amount=existing_term_cover_amount,
        recommended_term_cover=term_cover["recommended_term_cover"],
        effective_existing_cover=health_cover["effective_existing_cover"],
        recommended_health_cover=health_cover["recommended_health_cover"],
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        debts=debts,
    )
    return {
        "emergency_fund_target": emergency_fund["target"],
        "emergency_fund_current": emergency_fund["current"],
        "emergency_fund_status": emergency_fund["status"],
        "debt_priority_order": debt_priority_order,
        "term_cover_gap": term_cover["gap"],
        "health_cover_gap": health_cover["gap"],
        **kpis,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_gap_analysis.py -v`
Expected: PASS (17 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/gap_analysis.py backend/tests/test_gap_analysis.py
git commit -m "feat: port gap-analysis engine to Python"
```

---

### Task 4: Port the allocation engine (`src/lib/allocation.ts` → `backend/app/services/allocation.py`)

**Files:**
- Create: `backend/app/services/allocation.py`
- Test: `backend/tests/test_allocation.py`

**Interfaces:**
- Consumes: `app.config.BASE_EQUITY_AGE_CONSTANT`, `RISK_TOLERANCE_MULTIPLIERS`, `SHORT_HORIZON_THRESHOLD`, `SHORT_HORIZON_SHIFT`, `GOLD_ALLOCATION_PCT`, `FUND_EXAMPLES_PER_CATEGORY` (Task 1)
- Produces: `compute_allocation(age, risk_tolerance, investment_horizon_years) -> dict`, `select_fund_examples(bucket, funds, count=None) -> list[dict]` — used by `routers/onboarding.py` and `routers/dashboard.py` (Tasks 7-8)

- [ ] **Step 1: Write the failing tests in `backend/tests/test_allocation.py`** — ported 1:1 from `src/lib/allocation.test.ts`

```python
import pytest
from app.services.allocation import compute_allocation, select_fund_examples


def test_moderate_long_horizon():
    result = compute_allocation(age=30, risk_tolerance="moderate", investment_horizon_years=10)
    assert result["equity_pct"] == 70
    assert result["gold_pct"] == 10
    assert result["debt_pct"] == 20


def test_aggressive_scales_equity_up():
    result = compute_allocation(age=30, risk_tolerance="aggressive", investment_horizon_years=10)
    assert result["equity_pct"] == 84
    assert result["gold_pct"] == 10
    assert result["debt_pct"] == 6


def test_conservative_scales_equity_down():
    result = compute_allocation(age=30, risk_tolerance="conservative", investment_horizon_years=10)
    assert result["equity_pct"] == 56
    assert result["gold_pct"] == 10
    assert result["debt_pct"] == 34


def test_short_horizon_shifts_equity_to_debt():
    result = compute_allocation(age=30, risk_tolerance="moderate", investment_horizon_years=2)
    assert result["equity_pct"] == 50
    assert result["gold_pct"] == 10
    assert result["debt_pct"] == 40


def test_gold_capped_by_remaining_after_equity():
    result = compute_allocation(age=20, risk_tolerance="aggressive", investment_horizon_years=10)
    assert result["equity_pct"] == 96
    assert result["gold_pct"] == 4
    assert result["debt_pct"] == 0


def test_equity_clamped_to_100():
    result = compute_allocation(age=5, risk_tolerance="aggressive", investment_horizon_years=10)
    assert result["equity_pct"] == 100
    assert result["gold_pct"] == 0
    assert result["debt_pct"] == 0


def test_equity_clamped_to_0():
    result = compute_allocation(age=90, risk_tolerance="conservative", investment_horizon_years=2)
    assert result["equity_pct"] == 0
    assert result["gold_pct"] == 10
    assert result["debt_pct"] == 90


def test_buckets_always_sum_to_100():
    result = compute_allocation(age=45, risk_tolerance="moderate", investment_horizon_years=1)
    assert result["equity_pct"] + result["debt_pct"] + result["gold_pct"] == 100


ALL_FUNDS = [
    {"id": "e1", "category": "equity_large_cap", "aum_cr": 5000},
    {"id": "e2", "category": "equity_diversified", "aum_cr": 12000},
    {"id": "e3", "category": "equity_large_cap", "aum_cr": 8000},
    {"id": "d1", "category": "debt_short_duration", "aum_cr": 3000},
    {"id": "d2", "category": "fixed_deposit", "aum_cr": 9000},
    {"id": "g1", "category": "gold_etf", "aum_cr": 2000},
    {"id": "g2", "category": "sovereign_gold_bond", "aum_cr": 1000},
]


def test_equity_bucket_maps_both_categories_sorted_by_aum_desc():
    result = select_fund_examples("equity", ALL_FUNDS, count=2)
    assert [f["id"] for f in result] == ["e2", "e3"]


def test_debt_bucket_maps_debt_and_fixed_deposit():
    result = select_fund_examples("debt", ALL_FUNDS, count=3)
    assert [f["id"] for f in result] == ["d2", "d1"]


def test_gold_bucket_maps_gold_etf_and_sgb():
    result = select_fund_examples("gold", ALL_FUNDS, count=3)
    assert [f["id"] for f in result] == ["g1", "g2"]


def test_defaults_count_to_config_value():
    many_equity_funds = [{"id": f"e{i}", "category": "equity_large_cap", "aum_cr": i} for i in range(5)]
    assert len(select_fund_examples("equity", many_equity_funds)) == 3
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_allocation.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `backend/app/services/allocation.py`**

```python
from app.config import (
    BASE_EQUITY_AGE_CONSTANT, RISK_TOLERANCE_MULTIPLIERS,
    SHORT_HORIZON_THRESHOLD, SHORT_HORIZON_SHIFT, GOLD_ALLOCATION_PCT,
    FUND_EXAMPLES_PER_CATEGORY,
)

# Section 5.2's example: equity_pct -> "large-cap index fund or diversified
# equity mutual fund category" implies each bucket spans 2 category values,
# not 1 - mirrored here explicitly since the plan never spells the mapping
# out as a table.
BUCKET_CATEGORIES = {
    "equity": ["equity_large_cap", "equity_diversified"],
    "debt": ["debt_short_duration", "fixed_deposit"],
    "gold": ["gold_etf", "sovereign_gold_bond"],
}


# No v1 source for the base equity formula or the gold sleeve (see
# decisions/log.md): base equity is the standard "constant minus age"
# glide path, and gold is a flat diversification sleeve capped by
# whatever equity leaves behind, so the three buckets always sum to 100.
def compute_allocation(age: int, risk_tolerance: str, investment_horizon_years: int) -> dict:
    base_equity_pct = BASE_EQUITY_AGE_CONSTANT - age
    equity_pct = base_equity_pct * RISK_TOLERANCE_MULTIPLIERS[risk_tolerance]

    if investment_horizon_years <= SHORT_HORIZON_THRESHOLD:
        equity_pct -= SHORT_HORIZON_SHIFT

    equity_pct = min(100, max(0, equity_pct))

    gold_pct = min(GOLD_ALLOCATION_PCT, 100 - equity_pct)
    debt_pct = 100 - equity_pct - gold_pct

    return {"equity_pct": equity_pct, "debt_pct": debt_pct, "gold_pct": gold_pct}


def select_fund_examples(bucket: str, funds: list[dict], count: int | None = None) -> list[dict]:
    if count is None:
        count = FUND_EXAMPLES_PER_CATEGORY
    categories = BUCKET_CATEGORIES[bucket]
    matching = [f for f in funds if f["category"] in categories]
    matching.sort(key=lambda f: f["aum_cr"], reverse=True)
    return matching[:count]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_allocation.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/allocation.py backend/tests/test_allocation.py
git commit -m "feat: port allocation engine to Python"
```

---

### Task 5: Port insurance matching (`src/lib/insurance-matching.ts` → `backend/app/services/insurance_matching.py`)

**Files:**
- Create: `backend/app/services/insurance_matching.py`
- Test: `backend/tests/test_insurance_matching.py`

**Interfaces:**
- Consumes: `app.config.INSURANCE_EXAMPLES_PER_GAP_TYPE` (Task 1)
- Produces: `select_insurance_examples(plan_type, gap_amount, plans, count=None) -> list[dict]` — used by `routers/dashboard.py` (Task 8)

- [ ] **Step 1: Write the failing tests in `backend/tests/test_insurance_matching.py`** — ported 1:1 from `src/lib/insurance-matching.test.ts`

```python
from app.services.insurance_matching import select_insurance_examples

ALL_PLANS = [
    {"id": "t1", "plan_type": "term", "sum_assured_max": 5000000},
    {"id": "t2", "plan_type": "term", "sum_assured_max": 10000000},
    {"id": "t3", "plan_type": "term", "sum_assured_max": 20000000},
    {"id": "h1", "plan_type": "health", "sum_assured_max": 500000},
    {"id": "h2", "plan_type": "health", "sum_assured_max": 1000000},
]


def test_filters_by_plan_type():
    result = select_insurance_examples("health", 500000, ALL_PLANS, count=5)
    assert [p["id"] for p in result] == ["h1", "h2"]


def test_sorts_by_closest_sum_assured_ascending_distance():
    result = select_insurance_examples("term", 9000000, ALL_PLANS, count=3)
    assert [p["id"] for p in result] == ["t2", "t1", "t3"]


def test_never_sorts_by_largest_or_cheapest_closest_only():
    result = select_insurance_examples("term", 4000000, ALL_PLANS, count=1)
    assert [p["id"] for p in result] == ["t1"]


def test_takes_only_first_count():
    result = select_insurance_examples("term", 9000000, ALL_PLANS, count=1)
    assert len(result) == 1


def test_defaults_count_to_config_value():
    many_term_plans = [{"id": f"t{i}", "plan_type": "term", "sum_assured_max": i * 1000000} for i in range(5)]
    assert len(select_insurance_examples("term", 5000000, many_term_plans)) == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_insurance_matching.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `backend/app/services/insurance_matching.py`**

```python
from app.config import INSURANCE_EXAMPLES_PER_GAP_TYPE


# Closest sum-assured match to the computed gap — never "largest" or
# "cheapest" — to avoid the selection itself acting as a ranking signal
# (see .agents/context/subsystem-notes.md).
def select_insurance_examples(plan_type: str, gap_amount: float, plans: list[dict], count: int | None = None) -> list[dict]:
    if count is None:
        count = INSURANCE_EXAMPLES_PER_GAP_TYPE
    matching = [p for p in plans if p["plan_type"] == plan_type]
    matching.sort(key=lambda p: abs(p["sum_assured_max"] - gap_amount))
    return matching[:count]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_insurance_matching.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/insurance_matching.py backend/tests/test_insurance_matching.py
git commit -m "feat: port insurance-matching engine to Python"
```

---

### Task 6: Demo-user dependency (`src/lib/demo-user.ts` → `backend/app/demo_user.py`)

**Files:**
- Create: `backend/app/demo_user.py`
- Test: `backend/tests/test_demo_user.py`

**Interfaces:**
- Consumes: `app.db.get_db` (Task 1), `app.models.User` (Task 2)
- Produces: `COOKIE_NAME: str`, `get_or_create_demo_user(request: Request, response: Response, db: Session = Depends(get_db)) -> User` — usable directly as a FastAPI dependency (`Depends(get_or_create_demo_user)`) in Tasks 7-8

FastAPI has no Server-Component-style restriction on setting cookies, so unlike the TS version's documented tech debt (orphaned `User` row on a first-ever `/dashboard` visit), this can always set the cookie when it creates a user.

- [ ] **Step 1: Write the failing tests in `backend/tests/test_demo_user.py`**

```python
from unittest.mock import MagicMock
from fastapi import Response

from app.demo_user import get_or_create_demo_user, COOKIE_NAME
from app.models import User


def _fake_request(cookie_value=None):
    request = MagicMock()
    request.cookies = {COOKIE_NAME: cookie_value} if cookie_value else {}
    return request


def test_returns_existing_user_when_cookie_matches_a_row():
    existing_user = User(id="user-1", email="demo-1@fin.local")
    db = MagicMock()
    db.get.return_value = existing_user

    result = get_or_create_demo_user(_fake_request("user-1"), Response(), db)

    assert result is existing_user
    db.add.assert_not_called()


def test_creates_new_user_and_sets_cookie_when_no_cookie_present():
    db = MagicMock()
    db.get.return_value = None

    response = Response()
    get_or_create_demo_user(_fake_request(None), response, db)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert "set-cookie" in response.headers
    assert COOKIE_NAME in response.headers["set-cookie"]


def test_creates_new_user_when_cookie_id_not_found_in_db():
    db = MagicMock()
    db.get.return_value = None

    get_or_create_demo_user(_fake_request("stale-id"), Response(), db)

    db.add.assert_called_once()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_demo_user.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `backend/app/demo_user.py`**

```python
import os
import uuid

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

COOKIE_NAME = "fin_demo_user_id"
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365


def get_or_create_demo_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    existing_id = request.cookies.get(COOKIE_NAME)

    if existing_id:
        existing = db.get(User, existing_id)
        if existing:
            return existing

    created = User(email=f"demo-{uuid.uuid4()}@fin.local")
    db.add(created)
    db.commit()
    db.refresh(created)

    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    response.set_cookie(
        key=COOKIE_NAME,
        value=created.id,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="none" if is_production else "lax",
        secure=is_production,
        path="/",
    )

    return created
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_demo_user.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/demo_user.py backend/tests/test_demo_user.py
git commit -m "feat: port demo-user cookie dependency to Python"
```

---

### Task 7: Onboarding submit router (`src/app/api/onboarding/submit/route.ts` → `backend/app/routers/onboarding.py`)

**Files:**
- Create: `backend/app/routers/__init__.py` (empty)
- Create: `backend/app/routers/onboarding.py`
- Modify: `backend/app/main.py` — register the router
- Test: `backend/tests/test_onboarding_router.py`

**Interfaces:**
- Consumes: `get_or_create_demo_user` (Task 6), `compute_gap_analysis` (Task 3), `compute_allocation` (Task 4), `FinancialProfile`/`ExistingDebt`/`InsuranceProfile`/`GapAnalysisResult`/`AllocationResult` (Task 2)
- Produces: `router: APIRouter` mounted at `POST /api/onboarding/submit`, accepting the same JSON shape the frontend wizard already sends (camelCase keys, matching `OnboardingSubmission` in the current `route.ts`)

Deliberate small deviation from the TS version: the gap-analysis/allocation computation uses the validated request payload's values directly rather than re-reading them back from the just-committed DB row. This is numerically identical (the TS version's `Number(financialProfile.monthlyIncome)` round-trip through Postgres `Decimal` doesn't change the value) and removes an unnecessary read.

- [ ] **Step 1: Write `backend/app/routers/onboarding.py`**

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.demo_user import get_or_create_demo_user
from app.models import (
    FinancialProfile, ExistingDebt, InsuranceProfile,
    GapAnalysisResult, AllocationResult, User,
)
from app.services.gap_analysis import compute_gap_analysis
from app.services.allocation import compute_allocation

router = APIRouter()


class DebtIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label: str
    outstanding_amount: float = Field(alias="outstandingAmount")
    interest_rate_pct: float = Field(alias="interestRatePct")
    tenure_months: int = Field(alias="tenureMonths")


class OnboardingSubmission(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    age: int
    dependents_count: int = Field(alias="dependentsCount")
    risk_tolerance: str = Field(alias="riskTolerance")
    investment_horizon_years: int = Field(alias="investmentHorizonYears")
    monthly_income: float = Field(alias="monthlyIncome")
    monthly_expenses: float = Field(alias="monthlyExpenses")
    current_savings: float = Field(alias="currentSavings")
    debts: list[DebtIn] = []
    existing_term_cover_amount: float = Field(alias="existingTermCoverAmount")
    personal_health_cover_amount: float = Field(alias="personalHealthCoverAmount")
    employer_health_cover_amount: float = Field(alias="employerHealthCoverAmount")


@router.post("/api/onboarding/submit")
def submit_onboarding(
    payload: OnboardingSubmission,
    user: User = Depends(get_or_create_demo_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    financial_profile = db.query(FinancialProfile).filter_by(userId=user.id).first()
    if financial_profile is None:
        financial_profile = FinancialProfile(userId=user.id)
        db.add(financial_profile)

    financial_profile.age = payload.age
    financial_profile.dependentsCount = payload.dependents_count
    financial_profile.monthlyIncome = payload.monthly_income
    financial_profile.monthlyExpenses = payload.monthly_expenses
    financial_profile.currentSavings = payload.current_savings
    financial_profile.riskTolerance = payload.risk_tolerance
    financial_profile.investmentHorizonYears = payload.investment_horizon_years
    financial_profile.consentGivenAt = now
    db.flush()

    db.query(ExistingDebt).filter_by(financialProfileId=financial_profile.id).delete()
    for debt in payload.debts:
        db.add(ExistingDebt(
            financialProfileId=financial_profile.id,
            label=debt.label,
            outstandingAmount=debt.outstanding_amount,
            interestRatePct=debt.interest_rate_pct,
            tenureMonths=debt.tenure_months,
        ))

    insurance_profile = db.query(InsuranceProfile).filter_by(userId=user.id).first()
    if insurance_profile is None:
        insurance_profile = InsuranceProfile(userId=user.id)
        db.add(insurance_profile)

    insurance_profile.existingTermCoverAmount = payload.existing_term_cover_amount
    insurance_profile.personalHealthCoverAmount = payload.personal_health_cover_amount
    insurance_profile.employerHealthCoverAmount = payload.employer_health_cover_amount
    insurance_profile.consentGivenAt = now

    db.commit()

    debts_for_engine = [
        {
            "id": f"pending-{i}",
            "outstanding_amount": debt.outstanding_amount,
            "interest_rate_pct": debt.interest_rate_pct,
            "tenure_months": debt.tenure_months,
        }
        for i, debt in enumerate(payload.debts)
    ]

    gap_analysis = compute_gap_analysis(
        monthly_income=payload.monthly_income,
        monthly_expenses=payload.monthly_expenses,
        current_savings=payload.current_savings,
        existing_term_cover_amount=payload.existing_term_cover_amount,
        personal_health_cover_amount=payload.personal_health_cover_amount,
        employer_health_cover_amount=payload.employer_health_cover_amount,
        debts=debts_for_engine,
    )

    allocation = compute_allocation(
        age=payload.age,
        risk_tolerance=payload.risk_tolerance,
        investment_horizon_years=payload.investment_horizon_years,
    )

    db.add(GapAnalysisResult(
        userId=user.id,
        emergencyFundTarget=gap_analysis["emergency_fund_target"],
        emergencyFundCurrent=gap_analysis["emergency_fund_current"],
        emergencyFundStatus=gap_analysis["emergency_fund_status"],
        debtPriorityOrder=gap_analysis["debt_priority_order"],
        termCoverGap=gap_analysis["term_cover_gap"],
        healthCoverGap=gap_analysis["health_cover_gap"],
        emergencyFundCoveragePct=gap_analysis["emergency_fund_coverage_pct"],
        termCoverAdequacyPct=gap_analysis["term_cover_adequacy_pct"],
        healthCoverAdequacyPct=gap_analysis["health_cover_adequacy_pct"],
        savingsRatePct=gap_analysis["savings_rate_pct"],
        debtToIncomePct=gap_analysis["debt_to_income_pct"],
    ))
    db.add(AllocationResult(
        userId=user.id,
        equityPct=allocation["equity_pct"],
        debtPct=allocation["debt_pct"],
        goldPct=allocation["gold_pct"],
    ))
    db.commit()

    return {"success": True}
```

- [ ] **Step 2: Register the router in `backend/app/main.py`**

Add near the top: `from app.routers import onboarding`
Add after the CORS middleware block: `app.include_router(onboarding.router)`

- [ ] **Step 3: Write `backend/tests/test_onboarding_router.py`** — mocked DB, no live Postgres required (matches this project's existing convention of unit-testing pure logic and reserving live-DB verification for the manual walkthrough in Task 16)

```python
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.demo_user import get_or_create_demo_user
from app.models import User

VALID_PAYLOAD = {
    "age": 30,
    "dependentsCount": 1,
    "riskTolerance": "moderate",
    "investmentHorizonYears": 10,
    "monthlyIncome": 50000,
    "monthlyExpenses": 40000,
    "currentSavings": 180000,
    "debts": [
        {"label": "Credit card", "outstandingAmount": 100000, "interestRatePct": 12, "tenureMonths": 12},
    ],
    "existingTermCoverAmount": 2000000,
    "personalHealthCoverAmount": 200000,
    "employerHealthCoverAmount": 100000,
}


def _override_dependencies():
    fake_db = MagicMock()
    fake_db.query.return_value.filter_by.return_value.first.return_value = None
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_or_create_demo_user] = lambda: User(id="user-1", email="demo-1@fin.local")
    return fake_db


def test_submit_onboarding_returns_success():
    fake_db = _override_dependencies()
    client = TestClient(app)

    response = client.post("/api/onboarding/submit", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert fake_db.commit.call_count == 2
    app.dependency_overrides.clear()


def test_submit_onboarding_rejects_missing_required_field():
    _override_dependencies()
    client = TestClient(app)

    bad_payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "monthlyIncome"}
    response = client.post("/api/onboarding/submit", json=bad_payload)

    assert response.status_code == 422
    app.dependency_overrides.clear()
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && pytest tests/test_onboarding_router.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/__init__.py backend/app/routers/onboarding.py backend/app/main.py backend/tests/test_onboarding_router.py
git commit -m "feat: port onboarding submit endpoint to FastAPI"
```

---

### Task 8: Dashboard data router (new endpoint — replaces server-side fetch in `src/app/dashboard/page.tsx`)

**Files:**
- Create: `backend/app/routers/dashboard.py`
- Modify: `backend/app/main.py` — register the router
- Test: `backend/tests/test_dashboard_router.py`

**Interfaces:**
- Consumes: `get_or_create_demo_user` (Task 6), `select_fund_examples` (Task 4), `select_insurance_examples` (Task 5), `DEMO_MODE` (Task 1)
- Produces: `router: APIRouter` mounted at `GET /api/dashboard`, returning `{demo_mode, kpis: {...}, allocation: {...}, fund_examples: {bucket: [...]}, insurance_examples: {plan_type: [...]}}` — consumed by `frontend/src/pages/Dashboard.jsx` (Task 15)

The 404 trigger is "no gap-analysis/allocation results exist yet for this user" (matches the actual `redirect("/onboarding")` condition in `dashboard/page.tsx`, which checks for missing results — not cookie presence, since `get_or_create_demo_user` always succeeds by creating a user if none exists).

- [ ] **Step 1: Write `backend/app/routers/dashboard.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import DEMO_MODE
from app.db import get_db
from app.demo_user import get_or_create_demo_user
from app.models import GapAnalysisResult, AllocationResult, FundReference, InsurancePlanReference, User
from app.services.allocation import select_fund_examples
from app.services.insurance_matching import select_insurance_examples

router = APIRouter()

BUCKETS = ["equity", "debt", "gold"]


@router.get("/api/dashboard")
def get_dashboard(
    user: User = Depends(get_or_create_demo_user),
    db: Session = Depends(get_db),
):
    gap_result = (
        db.query(GapAnalysisResult)
        .filter_by(userId=user.id)
        .order_by(GapAnalysisResult.computedAt.desc())
        .first()
    )
    allocation_result = (
        db.query(AllocationResult)
        .filter_by(userId=user.id)
        .order_by(AllocationResult.computedAt.desc())
        .first()
    )

    if gap_result is None or allocation_result is None:
        raise HTTPException(status_code=404, detail="No onboarding data yet")

    term_cover_gap = float(gap_result.termCoverGap)
    health_cover_gap = float(gap_result.healthCoverGap)

    fund_examples: dict[str, list[dict]] = {}
    insurance_examples: dict[str, list[dict]] = {}

    if DEMO_MODE:
        funds = [
            {
                "id": f.id, "scheme_name": f.schemeName, "amc_name": f.amcName,
                "category": f.category, "expense_ratio": float(f.expenseRatio),
                "latest_nav": float(f.latestNav), "external_url": f.externalUrl,
                "aum_cr": float(f.aumCr),
            }
            for f in db.query(FundReference).all()
        ]
        for bucket in BUCKETS:
            examples = select_fund_examples(bucket, funds)
            if examples:
                fund_examples[bucket] = examples

        plans = [
            {
                "id": p.id, "insurer_name": p.insurerName, "plan_name": p.planName,
                "plan_type": p.planType, "sum_assured_min": float(p.sumAssuredMin),
                "sum_assured_max": float(p.sumAssuredMax), "key_features": p.keyFeatures,
                "indicative_premium_note": p.indicativePremiumNote,
                "claim_settlement_ratio_pct": float(p.claimSettlementRatioPct),
                "avg_claim_settlement_days": p.avgClaimSettlementDays,
                "external_url": p.externalUrl,
            }
            for p in db.query(InsurancePlanReference).all()
        ]
        for plan_type, gap in (("term", term_cover_gap), ("health", health_cover_gap)):
            if gap > 0:
                examples = select_insurance_examples(plan_type, gap, plans)
                if examples:
                    insurance_examples[plan_type] = examples

    return {
        "demo_mode": DEMO_MODE,
        "kpis": {
            "emergency_fund_coverage_pct": float(gap_result.emergencyFundCoveragePct),
            "emergency_fund_status": gap_result.emergencyFundStatus,
            "emergency_fund_gap": max(0, float(gap_result.emergencyFundTarget) - float(gap_result.emergencyFundCurrent)),
            "term_cover_adequacy_pct": float(gap_result.termCoverAdequacyPct),
            "term_cover_gap": term_cover_gap,
            "health_cover_adequacy_pct": float(gap_result.healthCoverAdequacyPct),
            "health_cover_gap": health_cover_gap,
            "savings_rate_pct": float(gap_result.savingsRatePct),
            "debt_to_income_pct": float(gap_result.debtToIncomePct),
        },
        "allocation": {
            "equity_pct": float(allocation_result.equityPct),
            "debt_pct": float(allocation_result.debtPct),
            "gold_pct": float(allocation_result.goldPct),
        },
        "fund_examples": fund_examples,
        "insurance_examples": insurance_examples,
    }
```

- [ ] **Step 2: Register the router in `backend/app/main.py`**

Add near the top: `from app.routers import dashboard`
Add after the onboarding router include: `app.include_router(dashboard.router)`

- [ ] **Step 3: Write `backend/tests/test_dashboard_router.py`**

```python
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.demo_user import get_or_create_demo_user
from app.models import User


def _fake_gap_result():
    r = MagicMock()
    r.emergencyFundCoveragePct = 75
    r.emergencyFundStatus = "building"
    r.emergencyFundTarget = 240000
    r.emergencyFundCurrent = 180000
    r.termCoverAdequacyPct = 33.33
    r.termCoverGap = 4000000
    r.healthCoverAdequacyPct = 60
    r.healthCoverGap = 200000
    r.savingsRatePct = 20
    r.debtToIncomePct = 17.77
    return r


def _fake_allocation_result():
    r = MagicMock()
    r.equityPct = 70
    r.debtPct = 20
    r.goldPct = 10
    return r


def test_dashboard_returns_404_when_no_results_yet():
    fake_db = MagicMock()
    fake_db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = None
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_or_create_demo_user] = lambda: User(id="user-1", email="demo-1@fin.local")

    response = TestClient(app).get("/api/dashboard")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_dashboard_returns_kpis_and_allocation_when_results_exist():
    fake_db = MagicMock()
    query_mock = fake_db.query.return_value
    query_mock.filter_by.return_value.order_by.return_value.first.side_effect = [
        _fake_gap_result(), _fake_allocation_result(),
    ]
    query_mock.all.return_value = []

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_or_create_demo_user] = lambda: User(id="user-1", email="demo-1@fin.local")

    response = TestClient(app).get("/api/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["kpis"]["emergency_fund_coverage_pct"] == 75
    assert body["allocation"]["equity_pct"] == 70
    app.dependency_overrides.clear()
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && pytest tests/test_dashboard_router.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/dashboard.py backend/app/main.py backend/tests/test_dashboard_router.py
git commit -m "feat: add GET /api/dashboard endpoint"
```

---

### Task 9: Seed script (`prisma/seed.ts` → `backend/app/seed.py`)

**Files:**
- Create: `backend/app/seed.py`

**Interfaces:**
- Consumes: `app.db.SessionLocal` (Task 1), `FundReference`, `InsurancePlanReference` (Task 2)
- Produces: a runnable script (`python -m app.seed`) — no other task imports this one

- [ ] **Step 1: Write `backend/app/seed.py`** — same 18 funds / 4 insurance plans as `prisma/seed.ts`, values copied verbatim

```python
from datetime import date

from app.db import SessionLocal
from app.models import FundReference, InsurancePlanReference

NAV_DATE = date(2026, 9, 1)

FUNDS = [
    {"schemeCode": "HDFC-TOP100-G", "schemeName": "HDFC Top 100 Fund", "amcName": "HDFC Mutual Fund", "category": "equity_large_cap", "expenseRatio": 1.05, "aumCr": 28500, "latestNav": 987.32, "externalUrl": "https://www.hdfcfund.com/"},
    {"schemeCode": "ICICI-BLUECHIP-G", "schemeName": "ICICI Prudential Bluechip Fund", "amcName": "ICICI Prudential Mutual Fund", "category": "equity_large_cap", "expenseRatio": 0.98, "aumCr": 45200, "latestNav": 112.45, "externalUrl": "https://www.icicipruamc.com/"},
    {"schemeCode": "SBI-BLUECHIP-G", "schemeName": "SBI Bluechip Fund", "amcName": "SBI Mutual Fund", "category": "equity_large_cap", "expenseRatio": 1.12, "aumCr": 39800, "latestNav": 78.19, "externalUrl": "https://www.sbimf.com/"},
    {"schemeCode": "PPFAS-FLEXICAP-G", "schemeName": "Parag Parikh Flexi Cap Fund", "amcName": "PPFAS Mutual Fund", "category": "equity_diversified", "expenseRatio": 0.76, "aumCr": 82300, "latestNav": 84.61, "externalUrl": "https://amc.ppfas.com/"},
    {"schemeCode": "AXIS-FLEXICAP-G", "schemeName": "Axis Flexi Cap Fund", "amcName": "Axis Mutual Fund", "category": "equity_diversified", "expenseRatio": 1.02, "aumCr": 12400, "latestNav": 21.34, "externalUrl": "https://www.axismf.com/"},
    {"schemeCode": "MIRAE-LARGEMID-G", "schemeName": "Mirae Asset Large & Midcap Fund", "amcName": "Mirae Asset Mutual Fund", "category": "equity_diversified", "expenseRatio": 0.89, "aumCr": 34600, "latestNav": 132.87, "externalUrl": "https://www.miraeassetmf.co.in/"},
    {"schemeCode": "HDFC-SHORTTERM-G", "schemeName": "HDFC Short Term Debt Fund", "amcName": "HDFC Mutual Fund", "category": "debt_short_duration", "expenseRatio": 0.45, "aumCr": 15200, "latestNav": 29.87, "externalUrl": "https://www.hdfcfund.com/"},
    {"schemeCode": "ICICI-SHORTTERM-G", "schemeName": "ICICI Prudential Short Term Fund", "amcName": "ICICI Prudential Mutual Fund", "category": "debt_short_duration", "expenseRatio": 0.52, "aumCr": 21300, "latestNav": 54.32, "externalUrl": "https://www.icicipruamc.com/"},
    {"schemeCode": "AXIS-SHORTTERM-G", "schemeName": "Axis Short Term Fund", "amcName": "Axis Mutual Fund", "category": "debt_short_duration", "expenseRatio": 0.48, "aumCr": 8900, "latestNav": 27.11, "externalUrl": "https://www.axismf.com/"},
    {"schemeCode": "SBI-FD-1Y", "schemeName": "SBI Bank Fixed Deposit (1 Year)", "amcName": "State Bank of India", "category": "fixed_deposit", "expenseRatio": 0, "aumCr": 0, "latestNav": 1, "externalUrl": "https://sbi.co.in/"},
    {"schemeCode": "HDFCBANK-FD-1Y", "schemeName": "HDFC Bank Fixed Deposit (1 Year)", "amcName": "HDFC Bank", "category": "fixed_deposit", "expenseRatio": 0, "aumCr": 0, "latestNav": 1, "externalUrl": "https://www.hdfcbank.com/"},
    {"schemeCode": "ICICIBANK-FD-1Y", "schemeName": "ICICI Bank Fixed Deposit (1 Year)", "amcName": "ICICI Bank", "category": "fixed_deposit", "expenseRatio": 0, "aumCr": 0, "latestNav": 1, "externalUrl": "https://www.icicibank.com/"},
    {"schemeCode": "SBI-GOLDETF-G", "schemeName": "SBI Gold ETF", "amcName": "SBI Mutual Fund", "category": "gold_etf", "expenseRatio": 0.65, "aumCr": 3400, "latestNav": 61.24, "externalUrl": "https://www.sbimf.com/"},
    {"schemeCode": "HDFC-GOLDETF-G", "schemeName": "HDFC Gold ETF", "amcName": "HDFC Mutual Fund", "category": "gold_etf", "expenseRatio": 0.6, "aumCr": 2800, "latestNav": 60.87, "externalUrl": "https://www.hdfcfund.com/"},
    {"schemeCode": "NIPPON-GOLDBEES-G", "schemeName": "Nippon India ETF Gold BeES", "amcName": "Nippon India Mutual Fund", "category": "gold_etf", "expenseRatio": 0.55, "aumCr": 8100, "latestNav": 61.02, "externalUrl": "https://mf.nipponindiaim.com/"},
    {"schemeCode": "SGB-2023-24-S1", "schemeName": "Sovereign Gold Bond 2023-24 Series I", "amcName": "Reserve Bank of India", "category": "sovereign_gold_bond", "expenseRatio": 0, "aumCr": 0, "latestNav": 6062, "externalUrl": "https://www.rbi.org.in/"},
    {"schemeCode": "SGB-2023-24-S2", "schemeName": "Sovereign Gold Bond 2023-24 Series II", "amcName": "Reserve Bank of India", "category": "sovereign_gold_bond", "expenseRatio": 0, "aumCr": 0, "latestNav": 5923, "externalUrl": "https://www.rbi.org.in/"},
    {"schemeCode": "SGB-2022-23-S3", "schemeName": "Sovereign Gold Bond 2022-23 Series III", "amcName": "Reserve Bank of India", "category": "sovereign_gold_bond", "expenseRatio": 0, "aumCr": 0, "latestNav": 5741, "externalUrl": "https://www.rbi.org.in/"},
]

INSURANCE_PLANS = [
    {"insurerName": "HDFC Life", "planName": "HDFC Life Click 2 Protect Super", "planType": "term", "sumAssuredMin": 2500000, "sumAssuredMax": 20000000, "indicativePremiumNote": "Illustrative: ~₹12,000/yr for a 30-year-old, ₹1cr cover, 30-yr term", "claimSettlementRatioPct": 98.66, "avgClaimSettlementDays": 5, "keyFeatures": ["Level cover term plan", "Terminal illness benefit", "Optional critical illness rider"], "externalUrl": "https://www.hdfclife.com/", "sourceNote": "Illustrative figures for demo purposes — not sourced from a live insurer rate card."},
    {"insurerName": "ICICI Prudential Life", "planName": "ICICI Pru iProtect Smart", "planType": "term", "sumAssuredMin": 5000000, "sumAssuredMax": 50000000, "indicativePremiumNote": "Illustrative: ~₹13,500/yr for a 30-year-old, ₹1cr cover, 30-yr term", "claimSettlementRatioPct": 99.18, "avgClaimSettlementDays": 4, "keyFeatures": ["Life cover + optional health cover rider", "Special exit value option", "Accidental death benefit"], "externalUrl": "https://www.iciciprulife.com/", "sourceNote": "Illustrative figures for demo purposes — not sourced from a live insurer rate card."},
    {"insurerName": "Star Health", "planName": "Star Health Comprehensive Insurance Policy", "planType": "health", "sumAssuredMin": 500000, "sumAssuredMax": 2500000, "indicativePremiumNote": "Illustrative: ~₹9,000/yr for ₹5L cover, individual, age 30", "claimSettlementRatioPct": 92.3, "avgClaimSettlementDays": 12, "keyFeatures": ["Cashless hospitalization", "No room-rent capping", "Annual health check-up"], "externalUrl": "https://www.starhealth.in/", "sourceNote": "Illustrative figures for demo purposes — not sourced from a live insurer rate card."},
    {"insurerName": "HDFC ERGO", "planName": "HDFC ERGO Optima Secure", "planType": "health", "sumAssuredMin": 500000, "sumAssuredMax": 10000000, "indicativePremiumNote": "Illustrative: ~₹11,000/yr for ₹5L cover, individual, age 30", "claimSettlementRatioPct": 94.1, "avgClaimSettlementDays": 9, "keyFeatures": ["Unlimited restoration of sum insured", "Air ambulance cover", "No-claim bonus up to 50%"], "externalUrl": "https://www.hdfcergo.com/health-insurance", "sourceNote": "Illustrative figures for demo purposes — not sourced from a live insurer rate card."},
]


def main():
    db = SessionLocal()
    try:
        db.query(FundReference).delete()
        db.query(InsurancePlanReference).delete()

        for fund in FUNDS:
            db.add(FundReference(navDate=NAV_DATE, **fund))
        for plan in INSURANCE_PLANS:
            db.add(InsurancePlanReference(**plan))

        db.commit()
        print(f"Seeded {len(FUNDS)} funds and {len(INSURANCE_PLANS)} insurance plans.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it once the DB is reachable** (same office-Wi-Fi port-block caveat as `subsystem-notes.md` — switch networks if this hangs/times out)

Run: `cd backend && python -m app.seed`
Expected: `Seeded 18 funds and 4 insurance plans.`

- [ ] **Step 3: Commit**

```bash
git add backend/app/seed.py
git commit -m "feat: port reference-data seed script to Python"
```

---

### Task 10: Frontend scaffold — Vite + React (JS) + Tailwind, API client, format helper

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/index.css`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/lib/format.js`
- Test: `frontend/src/lib/format.test.js`

**Interfaces:**
- Produces: `apiClient.get(path)`, `apiClient.post(path, body)` (both `fetch` with `credentials: 'include'`, throwing on non-2xx) — used by Tasks 14-15. `formatInr(amount: number): string` — used by Tasks 13-15.

- [ ] **Step 1: Write `frontend/package.json`**

```json
{
  "name": "fin-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "@tailwindcss/vite": "^4.0.0",
    "tailwindcss": "^4.0.0",
    "vite": "^5.4.11",
    "vitest": "^2.1.8",
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.3",
    "jsdom": "^25.0.1"
  }
}
```

- [ ] **Step 2: Write `frontend/vite.config.js`**

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.js",
  },
});
```

- [ ] **Step 3: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Financial Planning Demo</title>
  </head>
  <body class="h-full antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Write `frontend/src/index.css`** — port of `src/app/globals.css` (drops the Geist web-font loading, which is a Next.js-specific mechanism with no Vite equivalent worth adding for a demo; falls back to the same Arial/Helvetica stack the original already declared as its base)

```css
@import "tailwindcss";

:root {
  --background: #ffffff;
  --foreground: #171717;
  --accent: #4338ca;
  --accent-contrast: #ffffff;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-accent: var(--accent);
  --color-accent-contrast: var(--accent-contrast);
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;
    --foreground: #ededed;
    --accent: #818cf8;
    --accent-contrast: #0a0a0a;
  }
}

body {
  background: var(--background);
  color: var(--foreground);
  font-family: Arial, Helvetica, sans-serif;
}
```

- [ ] **Step 4b: Write `frontend/src/setupTests.js`** — registers `@testing-library/jest-dom`'s matchers (e.g. `toBeInTheDocument()`), used by Task 15's `Dashboard.test.jsx`

```js
import "@testing-library/jest-dom";
```

- [ ] **Step 5: Write `frontend/src/main.jsx`**

```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
```

- [ ] **Step 6: Write `frontend/src/api/client.js`**

```js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

export const apiClient = {
  get: (path) => request(path, { method: "GET" }),
  post: (path, body) => request(path, { method: "POST", body: JSON.stringify(body) }),
};
```

- [ ] **Step 7: Write `frontend/src/lib/format.js`** — port of `src/lib/format.ts`

```js
const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export function formatInr(amount) {
  return inrFormatter.format(amount);
}
```

- [ ] **Step 8: Write the failing test `frontend/src/lib/format.test.js`**

```js
import { describe, expect, test } from "vitest";
import { formatInr } from "./format";

describe("formatInr", () => {
  test("formats a whole number as INR currency", () => {
    expect(formatInr(240000)).toBe("₹2,40,000");
  });

  test("formats zero", () => {
    expect(formatInr(0)).toBe("₹0");
  });
});
```

- [ ] **Step 9: Install dependencies and run the test**

Run: `cd frontend && npm install && npm test -- src/lib/format.test.js`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add frontend/package.json frontend/vite.config.js frontend/index.html frontend/src/index.css frontend/src/setupTests.js frontend/src/main.jsx frontend/src/api/client.js frontend/src/lib/format.js frontend/src/lib/format.test.js
git commit -m "feat: scaffold Vite/React frontend with API client and format helper"
```

---

### Task 11: App shell, DisclaimerBanner, Home page, routing

**Files:**
- Create: `frontend/src/components/DisclaimerBanner.jsx`
- Create: `frontend/src/pages/Home.jsx`
- Create: `frontend/src/App.jsx`

**Interfaces:**
- Produces: `<App />` — the route table (`/`, `/onboarding`, `/onboarding/profile`, `/dashboard`) wrapping every page in the sticky `DisclaimerBanner`, mirroring `src/app/layout.tsx`'s persistent-footer layout. Routes to `/onboarding/profile` and `/dashboard` are placeholders until Tasks 12/14/15 fill them in — reference this task's route table when adding those.

- [ ] **Step 1: Write `frontend/src/components/DisclaimerBanner.jsx`** — direct port of `src/components/DisclaimerBanner.tsx`

```jsx
export function DisclaimerBanner() {
  return (
    <footer className="sticky bottom-0 z-50 border-t border-black/10 bg-amber-50 px-4 py-3 text-center text-xs text-amber-900 dark:border-white/10 dark:bg-amber-950 dark:text-amber-100">
      This tool provides educational guidance only and is not personalized
      financial or insurance advice. Fund and insurance plan examples shown
      are illustrative only — this is a demo project, not a live service.
    </footer>
  );
}
```

- [ ] **Step 2: Write `frontend/src/pages/Home.jsx`** — direct port of `src/app/page.tsx`, `next/link` replaced with `react-router-dom`'s `Link`

```jsx
import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center justify-center gap-6 px-6 py-24 text-center sm:py-32">
      <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-4xl">
        Financial Planning Demo
      </h1>
      <p className="text-base leading-7 text-zinc-600 dark:text-zinc-400">
        A personal/portfolio demo project that walks through emergency fund
        coverage, debt prioritization, insurance gaps, and asset allocation
        based on the information you provide.
      </p>
      <Link
        to="/onboarding"
        className="mt-2 rounded-md bg-accent px-5 py-2.5 text-sm font-medium text-accent-contrast"
      >
        Start
      </Link>
    </div>
  );
}
```

- [ ] **Step 3: Write `frontend/src/App.jsx`** — port of `src/app/layout.tsx`'s persistent-footer shell, using `react-router-dom`'s `Routes` in place of the Next.js App Router

```jsx
import { Routes, Route } from "react-router-dom";
import { DisclaimerBanner } from "./components/DisclaimerBanner.jsx";
import Home from "./pages/Home.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import OnboardingWizard from "./pages/onboarding/OnboardingWizard.jsx";
import Dashboard from "./pages/Dashboard.jsx";

export default function App() {
  return (
    <div className="flex min-h-full flex-col">
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/onboarding/profile" element={<OnboardingWizard />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
      <DisclaimerBanner />
    </div>
  );
}
```

This imports `Onboarding.jsx`, `onboarding/OnboardingWizard.jsx`, and `Dashboard.jsx` before they exist — Tasks 12, 14, and 15 create them respectively. The app will not build until those land; that's expected mid-plan and matches how `src/app/dashboard/page.tsx` already imports sibling components that were built in the same batch of work historically.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/DisclaimerBanner.jsx frontend/src/pages/Home.jsx frontend/src/App.jsx
git commit -m "feat: add app shell, disclaimer banner, and home page"
```

---

### Task 12: Onboarding disclaimer gate (`src/app/onboarding/page.tsx` → `frontend/src/pages/Onboarding.jsx`)

**Files:**
- Create: `frontend/src/pages/Onboarding.jsx`

**Interfaces:**
- Consumes: none beyond `react-router-dom`
- Produces: route `/onboarding` — the two-part disclaimer checkbox gate, `Continue` navigates to `/onboarding/profile` (Task 14)

- [ ] **Step 1: Write `frontend/src/pages/Onboarding.jsx`** — direct port of `src/app/onboarding/page.tsx`; `useRouter().push` becomes `useNavigate()`, the custom checkbox SVG data-URI is preserved exactly

```jsx
import { useId, useState } from "react";
import { useNavigate } from "react-router-dom";

function Clause({ id, part, checked, onChange, children }) {
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer gap-4 border-t border-black/10 py-6 first:border-t-0 dark:border-white/10"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 size-4 shrink-0 cursor-pointer appearance-none rounded-[3px] border border-zinc-400 checked:border-accent checked:bg-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent dark:border-zinc-600"
        style={{
          backgroundImage: checked
            ? "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='none' stroke='white' stroke-width='2'%3E%3Cpath d='M3.5 8.5l3 3 6-7' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E\")"
            : undefined,
          backgroundSize: "12px 12px",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
        }}
      />
      <span className="text-sm leading-7 text-zinc-700 dark:text-zinc-300">
        <span className="mb-1 block font-mono text-xs text-zinc-400 dark:text-zinc-500">
          {part}
        </span>
        {children}
      </span>
    </label>
  );
}

export default function Onboarding() {
  const navigate = useNavigate();
  const idPrefix = useId();
  const [ackEducational, setAckEducational] = useState(false);
  const [ackDemo, setAckDemo] = useState(false);
  const bothAcknowledged = ackEducational && ackDemo;

  return (
    <div className="mx-auto max-w-xl px-6 pt-20 pb-32 sm:pt-28">
      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">
        fin — before you start
      </p>
      <h1 className="mt-3 max-w-[20ch] text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Two things to read before you enter any financial details
      </h1>
      <p className="mt-4 max-w-[58ch] text-sm leading-7 text-zinc-600 dark:text-zinc-400">
        Both apply to everything that follows. Check each one once you've read it.
      </p>

      <div className="mt-8">
        <Clause
          id={`${idPrefix}-educational`}
          part="Part A — educational scope"
          checked={ackEducational}
          onChange={setAckEducational}
        >
          This tool provides educational guidance based on information you
          provide. It is not personalized financial or insurance advice.
        </Clause>
        <Clause
          id={`${idPrefix}-demo`}
          part="Part B — project status"
          checked={ackDemo}
          onChange={setAckDemo}
        >
          This is a personal/portfolio demo project, not a live financial or
          insurance service. Any fund or insurance plan examples shown are
          for illustration and are not offers, recommendations, or
          solicitations to buy.
        </Clause>
      </div>

      <button
        type="button"
        disabled={!bothAcknowledged}
        onClick={() => navigate("/onboarding/profile")}
        className="mt-10 w-full rounded-md bg-accent px-4 py-3 text-sm font-medium text-accent-contrast transition-colors disabled:cursor-not-allowed disabled:bg-zinc-200 disabled:text-zinc-400 dark:disabled:bg-zinc-800 dark:disabled:text-zinc-600"
      >
        Continue
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Onboarding.jsx
git commit -m "feat: port onboarding disclaimer gate to React/JS"
```

---

### Task 13: Wizard validators and step components (`src/app/onboarding/profile/screens.tsx` → `frontend/src/pages/onboarding/screens.jsx`)

**Files:**
- Create: `frontend/src/pages/onboarding/screens.jsx`
- Test: `frontend/src/__tests__/screens.test.jsx`

**Interfaces:**
- Consumes: `formatInr` (Task 10)
- Produces: `initialWizardState`, `validateScreen2(state)`, `validateScreen3(state)`, `validateScreen4(state)`, `validateScreen5(state)` (each returns a `{field: errorMessage}` object), `ScreenPersonalBasics`, `ScreenIncomeSavings`, `ScreenDebts`, `ScreenInsuranceCover`, `ScreenReviewConsent` — all consumed by `OnboardingWizard.jsx` (Task 14)

- [ ] **Step 1: Write the failing tests in `frontend/src/__tests__/screens.test.jsx`** — covers the validators (the same logic the TS version relied on type-checking plus these behavioral checks for)

```jsx
import { describe, expect, test } from "vitest";
import {
  initialWizardState, validateScreen2, validateScreen3, validateScreen4, validateScreen5,
} from "../pages/onboarding/screens.jsx";

describe("validateScreen2", () => {
  test("rejects age outside 18-100", () => {
    const errors = validateScreen2({ ...initialWizardState, age: "15", investmentHorizonYears: "5" });
    expect(errors.age).toBeDefined();
  });

  test("accepts a valid age and horizon", () => {
    const errors = validateScreen2({ ...initialWizardState, age: "30", investmentHorizonYears: "10" });
    expect(errors.age).toBeUndefined();
    expect(errors.investmentHorizonYears).toBeUndefined();
  });

  test("rejects a negative dependents count", () => {
    const errors = validateScreen2({ ...initialWizardState, age: "30", investmentHorizonYears: "10", dependentsCount: "-1" });
    expect(errors.dependentsCount).toBeDefined();
  });
});

describe("validateScreen3", () => {
  test("rejects a missing monthly income", () => {
    const errors = validateScreen3({ ...initialWizardState, monthlyIncome: "", monthlyExpenses: "1000", currentSavings: "1000" });
    expect(errors.monthlyIncome).toBeDefined();
  });

  test("accepts valid non-negative amounts", () => {
    const errors = validateScreen3({ ...initialWizardState, monthlyIncome: "50000", monthlyExpenses: "40000", currentSavings: "180000" });
    expect(Object.keys(errors)).toHaveLength(0);
  });
});

describe("validateScreen4", () => {
  test("rejects a debt with no label", () => {
    const errors = validateScreen4({
      ...initialWizardState,
      debts: [{ key: "debt-1", label: "", outstandingAmount: "1000", interestRatePct: "10", tenureMonths: "12" }],
    });
    expect(errors["debt-1-label"]).toBeDefined();
  });

  test("accepts a fully filled debt row", () => {
    const errors = validateScreen4({
      ...initialWizardState,
      debts: [{ key: "debt-1", label: "Car loan", outstandingAmount: "1000", interestRatePct: "10", tenureMonths: "12" }],
    });
    expect(Object.keys(errors)).toHaveLength(0);
  });
});

describe("validateScreen5", () => {
  test("rejects a negative cover amount", () => {
    const errors = validateScreen5({ ...initialWizardState, existingTermCoverAmount: "-1" });
    expect(errors.existingTermCoverAmount).toBeDefined();
  });

  test("accepts zero cover amounts", () => {
    const errors = validateScreen5({ ...initialWizardState, existingTermCoverAmount: "0", personalHealthCoverAmount: "0", employerHealthCoverAmount: "0" });
    expect(Object.keys(errors)).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npm test -- src/__tests__/screens.test.jsx`
Expected: FAIL (module doesn't exist yet)

- [ ] **Step 3: Write `frontend/src/pages/onboarding/screens.jsx`** — direct port of `screens.tsx` with all TS type annotations/interfaces removed; JSX and validator logic unchanged

```jsx
import { formatInr } from "../../lib/format.js";

export const initialWizardState = {
  age: "",
  dependentsCount: "0",
  riskTolerance: "moderate",
  investmentHorizonYears: "",
  monthlyIncome: "",
  monthlyExpenses: "",
  currentSavings: "",
  debts: [],
  existingTermCoverAmount: "0",
  personalHealthCoverAmount: "0",
  employerHealthCoverAmount: "0",
  consentGiven: false,
};

function Field({ label, error, children }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{label}</span>
      <div className="mt-1.5">{children}</div>
      {error && <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </label>
  );
}

const inputClass =
  "w-full rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm text-zinc-900 outline-none focus:border-accent focus:ring-1 focus:ring-accent dark:border-zinc-700 dark:text-zinc-50";

export function validateScreen2(s) {
  const errors = {};
  const age = Number(s.age);
  if (!s.age || age < 18 || age > 100) errors.age = "Enter an age between 18 and 100.";
  if (Number(s.dependentsCount) < 0) errors.dependentsCount = "Cannot be negative.";
  const horizon = Number(s.investmentHorizonYears);
  if (!s.investmentHorizonYears || horizon < 1) errors.investmentHorizonYears = "Enter at least 1 year.";
  return errors;
}

export function validateScreen3(s) {
  const errors = {};
  if (!s.monthlyIncome || Number(s.monthlyIncome) < 0) errors.monthlyIncome = "Enter a non-negative amount.";
  if (!s.monthlyExpenses || Number(s.monthlyExpenses) < 0) errors.monthlyExpenses = "Enter a non-negative amount.";
  if (!s.currentSavings || Number(s.currentSavings) < 0) errors.currentSavings = "Enter a non-negative amount.";
  return errors;
}

export function validateScreen4(s) {
  const errors = {};
  s.debts.forEach((debt) => {
    if (!debt.label.trim()) errors[`${debt.key}-label`] = "Enter a label.";
    if (Number(debt.outstandingAmount) < 0) errors[`${debt.key}-amount`] = "Cannot be negative.";
    if (Number(debt.interestRatePct) < 0) errors[`${debt.key}-rate`] = "Cannot be negative.";
    if (Number(debt.tenureMonths) < 1) errors[`${debt.key}-tenure`] = "Enter at least 1 month.";
  });
  return errors;
}

export function validateScreen5(s) {
  const errors = {};
  if (Number(s.existingTermCoverAmount) < 0) errors.existingTermCoverAmount = "Cannot be negative.";
  if (Number(s.personalHealthCoverAmount) < 0) errors.personalHealthCoverAmount = "Cannot be negative.";
  if (Number(s.employerHealthCoverAmount) < 0) errors.employerHealthCoverAmount = "Cannot be negative.";
  return errors;
}

export function ScreenPersonalBasics({ state, errors, onChange }) {
  return (
    <div className="space-y-5">
      <Field label="Age" error={errors.age}>
        <input type="number" className={inputClass} value={state.age} onChange={(e) => onChange({ age: e.target.value })} />
      </Field>
      <Field label="Number of dependents" error={errors.dependentsCount}>
        <input type="number" className={inputClass} value={state.dependentsCount} onChange={(e) => onChange({ dependentsCount: e.target.value })} />
      </Field>
      <Field label="Risk tolerance">
        <div className="flex gap-4">
          {["conservative", "moderate", "aggressive"].map((option) => (
            <label key={option} className="flex items-center gap-2 text-sm capitalize">
              <input
                type="radio"
                name="riskTolerance"
                checked={state.riskTolerance === option}
                onChange={() => onChange({ riskTolerance: option })}
              />
              {option}
            </label>
          ))}
        </div>
      </Field>
      <Field label="Investment horizon (years)" error={errors.investmentHorizonYears}>
        <input type="number" className={inputClass} value={state.investmentHorizonYears} onChange={(e) => onChange({ investmentHorizonYears: e.target.value })} />
      </Field>
    </div>
  );
}

export function ScreenIncomeSavings({ state, errors, onChange }) {
  return (
    <div className="space-y-5">
      <Field label="Monthly income (₹)" error={errors.monthlyIncome}>
        <input type="number" className={inputClass} value={state.monthlyIncome} onChange={(e) => onChange({ monthlyIncome: e.target.value })} />
      </Field>
      <Field label="Monthly expenses (₹)" error={errors.monthlyExpenses}>
        <input type="number" className={inputClass} value={state.monthlyExpenses} onChange={(e) => onChange({ monthlyExpenses: e.target.value })} />
      </Field>
      <Field label="Current savings (₹)" error={errors.currentSavings}>
        <input type="number" className={inputClass} value={state.currentSavings} onChange={(e) => onChange({ currentSavings: e.target.value })} />
      </Field>
    </div>
  );
}

let debtKeyCounter = 0;
function newDebtRow() {
  debtKeyCounter += 1;
  return { key: `debt-${debtKeyCounter}`, label: "", outstandingAmount: "", interestRatePct: "", tenureMonths: "" };
}

export function ScreenDebts({ state, errors, onChange }) {
  const updateDebt = (key, patch) => {
    onChange({ debts: state.debts.map((d) => (d.key === key ? { ...d, ...patch } : d)) });
  };
  const removeDebt = (key) => {
    onChange({ debts: state.debts.filter((d) => d.key !== key) });
  };

  return (
    <div className="space-y-6">
      {state.debts.length === 0 && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">No debts added — that's valid.</p>
      )}
      {state.debts.map((debt) => (
        <div key={debt.key} className="space-y-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
          <Field label="Label" error={errors[`${debt.key}-label`]}>
            <input type="text" className={inputClass} value={debt.label} onChange={(e) => updateDebt(debt.key, { label: e.target.value })} placeholder="e.g. Car loan" />
          </Field>
          <Field label="Outstanding amount (₹)" error={errors[`${debt.key}-amount`]}>
            <input type="number" className={inputClass} value={debt.outstandingAmount} onChange={(e) => updateDebt(debt.key, { outstandingAmount: e.target.value })} />
          </Field>
          <Field label="Interest rate (%)" error={errors[`${debt.key}-rate`]}>
            <input type="number" className={inputClass} value={debt.interestRatePct} onChange={(e) => updateDebt(debt.key, { interestRatePct: e.target.value })} />
          </Field>
          <Field label="Tenure (months)" error={errors[`${debt.key}-tenure`]}>
            <input type="number" className={inputClass} value={debt.tenureMonths} onChange={(e) => updateDebt(debt.key, { tenureMonths: e.target.value })} />
          </Field>
          <button type="button" onClick={() => removeDebt(debt.key)} className="text-xs font-medium text-red-600 underline underline-offset-4 dark:text-red-400">
            Remove
          </button>
        </div>
      ))}
      <button type="button" onClick={() => onChange({ debts: [...state.debts, newDebtRow()] })} className="text-sm font-medium text-accent underline underline-offset-4">
        + Add a debt
      </button>
    </div>
  );
}

export function ScreenInsuranceCover({ state, errors, onChange }) {
  return (
    <div className="space-y-5">
      <Field label="Existing term cover amount (₹)" error={errors.existingTermCoverAmount}>
        <input type="number" className={inputClass} value={state.existingTermCoverAmount} onChange={(e) => onChange({ existingTermCoverAmount: e.target.value })} />
      </Field>
      <Field label="Personal health cover amount (₹)" error={errors.personalHealthCoverAmount}>
        <input type="number" className={inputClass} value={state.personalHealthCoverAmount} onChange={(e) => onChange({ personalHealthCoverAmount: e.target.value })} />
      </Field>
      <Field label="Employer health cover amount (₹)" error={errors.employerHealthCoverAmount}>
        <input type="number" className={inputClass} value={state.employerHealthCoverAmount} onChange={(e) => onChange({ employerHealthCoverAmount: e.target.value })} />
      </Field>
    </div>
  );
}

function SummaryRow({ label, value }) {
  return (
    <div className="flex justify-between border-t border-zinc-100 py-2 text-sm first:border-t-0 dark:border-zinc-800">
      <span className="text-zinc-500 dark:text-zinc-400">{label}</span>
      <span className="font-medium text-zinc-900 dark:text-zinc-50">{value}</span>
    </div>
  );
}

export function ScreenReviewConsent({ state, consentError, onChange }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">Personal basics</h3>
        <SummaryRow label="Age" value={state.age} />
        <SummaryRow label="Dependents" value={state.dependentsCount} />
        <SummaryRow label="Risk tolerance" value={state.riskTolerance} />
        <SummaryRow label="Investment horizon" value={`${state.investmentHorizonYears} years`} />
      </div>
      <div>
        <h3 className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">Income & savings</h3>
        <SummaryRow label="Monthly income" value={formatInr(Number(state.monthlyIncome) || 0)} />
        <SummaryRow label="Monthly expenses" value={formatInr(Number(state.monthlyExpenses) || 0)} />
        <SummaryRow label="Current savings" value={formatInr(Number(state.currentSavings) || 0)} />
      </div>
      <div>
        <h3 className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">Debts</h3>
        {state.debts.length === 0 ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">None</p>
        ) : (
          state.debts.map((d) => (
            <SummaryRow key={d.key} label={d.label || "(unlabeled)"} value={`${formatInr(Number(d.outstandingAmount) || 0)} @ ${d.interestRatePct}%`} />
          ))
        )}
      </div>
      <div>
        <h3 className="mb-2 font-mono text-xs text-zinc-400 dark:text-zinc-500">Insurance cover</h3>
        <SummaryRow label="Term cover" value={formatInr(Number(state.existingTermCoverAmount) || 0)} />
        <SummaryRow label="Personal health cover" value={formatInr(Number(state.personalHealthCoverAmount) || 0)} />
        <SummaryRow label="Employer health cover" value={formatInr(Number(state.employerHealthCoverAmount) || 0)} />
      </div>
      <label className="flex cursor-pointer gap-3 border-t border-zinc-200 pt-6 text-sm leading-6 text-zinc-700 dark:border-zinc-800 dark:text-zinc-300">
        <input type="checkbox" checked={state.consentGiven} onChange={(e) => onChange({ consentGiven: e.target.checked })} className="mt-0.5 size-4 shrink-0" />
        I consent to this data being used to generate my gap analysis and allocation results, per the DPDP notice.
      </label>
      {consentError && <p className="text-xs text-red-600 dark:text-red-400">{consentError}</p>}
    </div>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npm test -- src/__tests__/screens.test.jsx`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/onboarding/screens.jsx frontend/src/__tests__/screens.test.jsx
git commit -m "feat: port onboarding wizard screens and validators to React/JS"
```

---

### Task 14: Wizard shell page (`src/app/onboarding/profile/page.tsx` → `frontend/src/pages/onboarding/OnboardingWizard.jsx`)

**Files:**
- Create: `frontend/src/pages/onboarding/OnboardingWizard.jsx`

**Interfaces:**
- Consumes: `initialWizardState`, `validateScreen2..5`, `Screen*` components (Task 13), `apiClient.post` (Task 10)
- Produces: route `/onboarding/profile` — on successful submit, navigates to `/dashboard`

- [ ] **Step 1: Write `frontend/src/pages/onboarding/OnboardingWizard.jsx`** — direct port of `profile/page.tsx`; `fetch("/api/onboarding/submit")` becomes `apiClient.post("/api/onboarding/submit", ...)`, `useRouter().push` becomes `useNavigate()`

```jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  initialWizardState, validateScreen2, validateScreen3, validateScreen4, validateScreen5,
  ScreenPersonalBasics, ScreenIncomeSavings, ScreenDebts, ScreenInsuranceCover, ScreenReviewConsent,
} from "./screens.jsx";
import { apiClient } from "../../api/client.js";

const STEP_TITLES = ["Personal basics", "Income & savings", "Existing debts", "Insurance cover", "Review & consent"];

export default function OnboardingWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [state, setState] = useState(initialWizardState);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const onChange = (patch) => setState((s) => ({ ...s, ...patch }));

  const validators = [validateScreen2, validateScreen3, validateScreen4, validateScreen5, () => ({})];

  function goNext() {
    const stepErrors = validators[step](state);
    setErrors(stepErrors);
    if (Object.keys(stepErrors).length > 0) return;
    setStep((s) => Math.min(s + 1, STEP_TITLES.length - 1));
  }

  function goBack() {
    setErrors({});
    setStep((s) => Math.max(s - 1, 0));
  }

  async function submit() {
    if (!state.consentGiven) {
      setErrors({ consent: "Consent is required to continue." });
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      await apiClient.post("/api/onboarding/submit", {
        age: Number(state.age),
        dependentsCount: Number(state.dependentsCount),
        riskTolerance: state.riskTolerance,
        investmentHorizonYears: Number(state.investmentHorizonYears),
        monthlyIncome: Number(state.monthlyIncome),
        monthlyExpenses: Number(state.monthlyExpenses),
        currentSavings: Number(state.currentSavings),
        debts: state.debts.map((d) => ({
          label: d.label,
          outstandingAmount: Number(d.outstandingAmount),
          interestRatePct: Number(d.interestRatePct),
          tenureMonths: Number(d.tenureMonths),
        })),
        existingTermCoverAmount: Number(state.existingTermCoverAmount),
        personalHealthCoverAmount: Number(state.personalHealthCoverAmount),
        employerHealthCoverAmount: Number(state.employerHealthCoverAmount),
      });
      navigate("/dashboard");
    } catch {
      setSubmitError("Something went wrong submitting your profile. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl px-6 py-20 sm:py-28">
      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">
        fin — profile ({step + 1} of {STEP_TITLES.length})
      </p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        {STEP_TITLES[step]}
      </h1>

      <div className="mt-8">
        {step === 0 && <ScreenPersonalBasics state={state} errors={errors} onChange={onChange} />}
        {step === 1 && <ScreenIncomeSavings state={state} errors={errors} onChange={onChange} />}
        {step === 2 && <ScreenDebts state={state} errors={errors} onChange={onChange} />}
        {step === 3 && <ScreenInsuranceCover state={state} errors={errors} onChange={onChange} />}
        {step === 4 && <ScreenReviewConsent state={state} consentError={errors.consent} onChange={onChange} />}
      </div>

      {submitError && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{submitError}</p>}

      <div className="mt-10 flex gap-3">
        {step > 0 && (
          <button type="button" onClick={goBack} disabled={submitting} className="flex-1 rounded-md border border-zinc-300 px-4 py-3 text-sm font-medium text-zinc-700 dark:border-zinc-700 dark:text-zinc-300">
            Back
          </button>
        )}
        {step < STEP_TITLES.length - 1 ? (
          <button type="button" onClick={goNext} className="flex-1 rounded-md bg-accent px-4 py-3 text-sm font-medium text-accent-contrast">
            Next
          </button>
        ) : (
          <button type="button" onClick={submit} disabled={submitting} className="flex-1 rounded-md bg-accent px-4 py-3 text-sm font-medium text-accent-contrast disabled:opacity-60">
            {submitting ? "Submitting..." : "Submit"}
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/onboarding/OnboardingWizard.jsx
git commit -m "feat: port onboarding wizard shell page to React/JS"
```

---

### Task 15: Dashboard page and cards (`src/app/dashboard/*` → `frontend/src/pages/Dashboard.jsx` + components)

**Files:**
- Create: `frontend/src/components/KpiCard.jsx`
- Create: `frontend/src/components/FundCard.jsx`
- Create: `frontend/src/components/InsuranceCard.jsx`
- Create: `frontend/src/pages/Dashboard.jsx`
- Test: `frontend/src/__tests__/Dashboard.test.jsx`

**Interfaces:**
- Consumes: `formatInr` (Task 10), `apiClient.get` (Task 10), the `GET /api/dashboard` JSON shape from Task 8 (`kpis`, `allocation`, `fund_examples`, `insurance_examples`, `demo_mode`)
- Produces: route `/dashboard` — fetches on mount (no server-side rendering in a Vite SPA, unlike the original Server Component), redirects to `/onboarding` on a 404

- [ ] **Step 1: Write `frontend/src/components/KpiCard.jsx`** — direct port of `KpiCard.tsx`

```jsx
import { formatInr } from "../lib/format.js";

const RADIUS = 40;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function KpiCard({ label, pct, gapAmount, gapLabel, statusLabel }) {
  const clamped = Math.max(0, Math.min(100, pct));
  const offset = CIRCUMFERENCE * (1 - clamped / 100);

  return (
    <div className="rounded-lg border border-zinc-200 p-5 dark:border-zinc-800">
      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">{label}</p>
      <div className="mt-3 flex items-center gap-4">
        <svg width="96" height="96" viewBox="0 0 96 96" className="shrink-0 -rotate-90">
          <circle cx="48" cy="48" r={RADIUS} fill="none" stroke="currentColor" strokeWidth="8" className="text-zinc-200 dark:text-zinc-800" />
          <circle
            cx="48" cy="48" r={RADIUS} fill="none" stroke="currentColor" strokeWidth="8"
            strokeLinecap="round" strokeDasharray={CIRCUMFERENCE} strokeDashoffset={offset}
            className="text-accent"
          />
        </svg>
        <div>
          <p className="text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">{pct.toFixed(0)}%</p>
          {statusLabel && <p className="mt-0.5 text-xs capitalize text-zinc-500 dark:text-zinc-400">{statusLabel}</p>}
        </div>
      </div>
      <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">{gapLabel}: {formatInr(gapAmount)}</p>
    </div>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/FundCard.jsx`** — direct port of `FundCard.tsx`

```jsx
import { formatInr } from "../lib/format.js";

export function FundCard({ fund }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50">{fund.scheme_name}</p>
      <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{fund.amc_name}</p>
      <dl className="mt-3 space-y-1 text-xs text-zinc-600 dark:text-zinc-400">
        <div className="flex justify-between">
          <dt>Category</dt>
          <dd className="capitalize">{fund.category.replace(/_/g, " ")}</dd>
        </div>
        <div className="flex justify-between">
          <dt>Expense ratio</dt>
          <dd>{fund.expense_ratio.toFixed(2)}%</dd>
        </div>
        <div className="flex justify-between">
          <dt>Latest NAV</dt>
          <dd>{formatInr(fund.latest_nav)}</dd>
        </div>
      </dl>
      <a href={fund.external_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-xs font-medium text-accent underline underline-offset-4">
        View scheme details
      </a>
    </div>
  );
}
```

- [ ] **Step 3: Write `frontend/src/components/InsuranceCard.jsx`** — direct port of `InsuranceCard.tsx`, including `InsuranceComparisonTable`

```jsx
import { formatInr } from "../lib/format.js";

function features(plan) {
  return Array.isArray(plan.key_features) ? plan.key_features : [];
}

export function InsuranceCard({ plan }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50">{plan.plan_name}</p>
      <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{plan.insurer_name}</p>
      <p className="mt-3 text-xs text-zinc-600 dark:text-zinc-400">
        Sum assured: {formatInr(plan.sum_assured_min)} – {formatInr(plan.sum_assured_max)}
      </p>
      <ul className="mt-2 list-inside list-disc text-xs text-zinc-600 dark:text-zinc-400">
        {features(plan).slice(0, 3).map((feature) => <li key={feature}>{feature}</li>)}
      </ul>
      <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">{plan.indicative_premium_note}</p>
      <dl className="mt-2 space-y-1 text-xs text-zinc-600 dark:text-zinc-400">
        <div className="flex justify-between">
          <dt>Claim settlement ratio</dt>
          <dd>{plan.claim_settlement_ratio_pct.toFixed(1)}%</dd>
        </div>
        <div className="flex justify-between">
          <dt>Avg. settlement time</dt>
          <dd>{plan.avg_claim_settlement_days} days</dd>
        </div>
      </dl>
      <a href={plan.external_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-xs font-medium text-accent underline underline-offset-4">
        Show more details
      </a>
    </div>
  );
}

// Neutral comparison — every column is a plain fact, no ranking, no
// "best value" badge, no score, no sort implying one plan is better.
export function InsuranceComparisonTable({ plans }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-zinc-200 text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
            <th className="px-3 py-2 font-medium">Plan</th>
            <th className="px-3 py-2 font-medium">Sum assured</th>
            <th className="px-3 py-2 font-medium">Premium (indicative)</th>
            <th className="px-3 py-2 font-medium">Claim settlement ratio</th>
            <th className="px-3 py-2 font-medium">Avg. settlement time</th>
            <th className="px-3 py-2 font-medium">Link</th>
          </tr>
        </thead>
        <tbody>
          {plans.map((plan) => (
            <tr key={plan.id} className="border-b border-zinc-100 last:border-b-0 dark:border-zinc-900">
              <td className="px-3 py-2">
                <p className="font-medium text-zinc-900 dark:text-zinc-50">{plan.plan_name}</p>
                <p className="text-zinc-500 dark:text-zinc-400">{plan.insurer_name}</p>
              </td>
              <td className="px-3 py-2">{formatInr(plan.sum_assured_min)} – {formatInr(plan.sum_assured_max)}</td>
              <td className="px-3 py-2">{plan.indicative_premium_note}</td>
              <td className="px-3 py-2">{plan.claim_settlement_ratio_pct.toFixed(1)}%</td>
              <td className="px-3 py-2">{plan.avg_claim_settlement_days} days</td>
              <td className="px-3 py-2">
                <a href={plan.external_url} target="_blank" rel="noopener noreferrer" className="font-medium text-accent underline underline-offset-4">
                  Details
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Write `frontend/src/pages/Dashboard.jsx`** — port of `dashboard/page.tsx`; the server-side Prisma reads become a client-side `useEffect` fetch against `GET /api/dashboard`

```jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/client.js";
import { formatInr } from "../lib/format.js";
import { KpiCard } from "../components/KpiCard.jsx";
import { FundCard } from "../components/FundCard.jsx";
import { InsuranceCard, InsuranceComparisonTable } from "../components/InsuranceCard.jsx";

const BUCKETS = ["equity", "debt", "gold"];

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .get("/api/dashboard")
      .then(setData)
      .catch(() => navigate("/onboarding"))
      .finally(() => setLoading(false));
  }, [navigate]);

  if (loading || !data) return null;

  const { kpis, allocation, fund_examples: fundExamples, insurance_examples: insuranceExamples, demo_mode: demoMode } = data;

  return (
    <div className="mx-auto max-w-4xl px-6 py-16 sm:py-20">
      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">fin — dashboard</p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Your financial gap analysis
      </h1>

      <section className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard
          label="Emergency fund coverage"
          pct={kpis.emergency_fund_coverage_pct}
          gapAmount={kpis.emergency_fund_gap}
          gapLabel="Gap to target"
          statusLabel={kpis.emergency_fund_status}
        />
        <KpiCard label="Term cover adequacy" pct={kpis.term_cover_adequacy_pct} gapAmount={kpis.term_cover_gap} gapLabel="Cover gap" />
        <KpiCard label="Health cover adequacy" pct={kpis.health_cover_adequacy_pct} gapAmount={kpis.health_cover_gap} gapLabel="Cover gap" />
        <KpiCard label="Savings rate" pct={kpis.savings_rate_pct} gapAmount={0} gapLabel="—" />
        <KpiCard label="Debt-to-income" pct={kpis.debt_to_income_pct} gapAmount={0} gapLabel="—" />
      </section>

      <section className="mt-12">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Allocation snapshot</h2>
        <div className="mt-4 flex gap-6 text-sm">
          <p>Equity: <span className="font-medium">{allocation.equity_pct.toFixed(0)}%</span></p>
          <p>Debt: <span className="font-medium">{allocation.debt_pct.toFixed(0)}%</span></p>
          <p>Gold: <span className="font-medium">{allocation.gold_pct.toFixed(0)}%</span></p>
        </div>
      </section>

      {demoMode && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Fund examples</h2>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">Illustrative only — see disclaimer below.</p>
          <div className="mt-4 space-y-6">
            {BUCKETS.map((bucket) => {
              const examples = fundExamples[bucket];
              if (!examples || examples.length === 0) return null;
              return (
                <div key={bucket}>
                  <h3 className="mb-2 text-xs font-medium capitalize text-zinc-600 dark:text-zinc-400">{bucket}</h3>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    {examples.map((fund) => <FundCard key={fund.id} fund={fund} />)}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {demoMode && (kpis.term_cover_gap > 0 || kpis.health_cover_gap > 0) && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Insurance examples</h2>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">Illustrative only — see disclaimer below.</p>
          <div className="mt-4 space-y-6">
            {[["term", kpis.term_cover_gap], ["health", kpis.health_cover_gap]].map(([planType, gap]) => {
              if (gap <= 0) return null;
              const examples = insuranceExamples[planType];
              if (!examples || examples.length === 0) return null;
              return (
                <div key={planType}>
                  <h3 className="mb-2 text-xs font-medium capitalize text-zinc-600 dark:text-zinc-400">
                    {planType} cover — gap: {formatInr(gap)}
                  </h3>
                  {examples.length === 1 ? (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <InsuranceCard plan={examples[0]} />
                    </div>
                  ) : (
                    <InsuranceComparisonTable plans={examples} />
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Write `frontend/src/__tests__/Dashboard.test.jsx`**

```jsx
import { describe, expect, test, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "../pages/Dashboard.jsx";
import { apiClient } from "../api/client.js";

vi.mock("../api/client.js", () => ({ apiClient: { get: vi.fn() } }));

const SAMPLE_RESPONSE = {
  demo_mode: false,
  kpis: {
    emergency_fund_coverage_pct: 75, emergency_fund_status: "building", emergency_fund_gap: 60000,
    term_cover_adequacy_pct: 33.33, term_cover_gap: 4000000,
    health_cover_adequacy_pct: 60, health_cover_gap: 200000,
    savings_rate_pct: 20, debt_to_income_pct: 17.77,
  },
  allocation: { equity_pct: 70, debt_pct: 20, gold_pct: 10 },
  fund_examples: {},
  insurance_examples: {},
};

beforeEach(() => {
  vi.clearAllMocks();
});

test("renders KPI values once the dashboard data loads", async () => {
  apiClient.get.mockResolvedValue(SAMPLE_RESPONSE);

  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );

  await waitFor(() => expect(screen.getByText("75%")).toBeInTheDocument());
  expect(screen.getByText("70%")).toBeInTheDocument();
});
```

- [ ] **Step 6: Run the tests**

Run: `cd frontend && npm test -- src/__tests__/Dashboard.test.jsx`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/KpiCard.jsx frontend/src/components/FundCard.jsx frontend/src/components/InsuranceCard.jsx frontend/src/pages/Dashboard.jsx frontend/src/__tests__/Dashboard.test.jsx
git commit -m "feat: port dashboard page and cards to React/JS"
```

---

### Task 16: Manual parity verification and cutover

**Files:**
- Modify: `.gitignore` (if not already covering `backend/.env`, `backend/__pycache__/`, `frontend/node_modules/`, `frontend/dist/`)
- Delete (after verification passes): `src/`, `prisma/`, `next.config.ts`, `next-env.d.ts`, `tsconfig.json`, `eslint.config.mjs`, `vitest.config.ts` (or whichever TS-era config files exist at the repo root)
- Modify: `package.json` (remove Next.js/Prisma/TypeScript dependencies, or delete the file entirely if nothing else needs Node at the repo root)
- Modify: `.agents/context/stack-and-rules.md` (update tech stack section to FastAPI/SQLAlchemy/Vite+React)
- Modify: `.agents/projects/active-backlog.md` (mark the rewrite tasks done)

**Interfaces:** None — this task verifies the whole system end-to-end and retires the old stack. No new code.

- [ ] **Step 1: Start both servers**

Run: `cd backend && uvicorn app.main:app --reload --port 8000` (background/second terminal)
Run: `cd frontend && npm run dev`

- [ ] **Step 2: Run the full backend test suite**

Run: `cd backend && pytest -v`
Expected: all tests from Tasks 1, 3-8 pass (health check, gap-analysis, allocation, insurance-matching, demo-user, onboarding router, dashboard router)

- [ ] **Step 3: Run the full frontend test suite**

Run: `cd frontend && npm test`
Expected: all tests from Tasks 10, 13, 15 pass (format, screens validators, dashboard rendering)

- [ ] **Step 4: Manual walkthrough — same scope as the current backlog's end-to-end test item**

Open `http://localhost:5173/` in a browser and walk through:
1. Home → "Start" → lands on `/onboarding`
2. Both disclaimer checkboxes required before "Continue" enables
3. `/onboarding/profile` — all 5 wizard steps: enter data, confirm inline validation blocks "Next" on bad input (e.g. age 15, negative amounts), confirm "Back" preserves entered data
4. Review screen shows correctly ₹-formatted values matching what was entered
5. Submit → redirects to `/dashboard`
6. Dashboard shows 5 KPI ring meters with sensible percentages, allocation snapshot sums to 100%
7. If `DEMO_MODE=true` in `backend/.env`: fund examples and insurance examples/comparison table render with real-looking data
8. Set `backend/.env`'s `DEMO_MODE=false`, restart uvicorn, reload `/dashboard`: confirm fund/insurance sections are absent from the rendered page AND absent from the raw `GET /api/dashboard` JSON (check via browser devtools Network tab) — this is the compliance-critical check from `subsystem-notes.md`
9. Open devtools Application tab, confirm `fin_demo_user_id` cookie is set with `HttpOnly`

If any step fails, stop and fix before proceeding to cutover — don't retire the old stack on a broken replacement.

- [ ] **Step 5: Retire the Next.js/Prisma stack**

Once every check in Step 4 passes:

```bash
git rm -r src/ prisma/
git rm next.config.ts next-env.d.ts tsconfig.json 2>/dev/null || true
```

Edit `package.json` to remove `next`, `next-auth`, `@prisma/client`, `@prisma/adapter-pg`, `prisma`, `typescript`, `@types/*`, `tsx` and their associated scripts (`dev`, `build`, `start`, `prisma:generate`, `prisma:migrate`), or delete `package.json`/`package-lock.json` entirely if nothing else in the repo root needs Node.

- [ ] **Step 6: Update the second-brain files**

Follow this repo's `.claude/commands/second-brain-close.md` process: update `.agents/context/stack-and-rules.md`'s Tech Stack section to FastAPI + SQLAlchemy + Alembic + Vite/React (JS), update the File Map to point at `backend/app/` and `frontend/src/` paths, and add a `decisions/log.md` entry recording that the app was rewritten from Next.js/Prisma to FastAPI/React per this plan and its spec.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: retire Next.js/Prisma stack after Python/React rewrite parity verification"
```

---

## Self-Review Notes

- **Spec coverage:** Every spec section has a corresponding task — architecture (Tasks 1, 10), session/auth (Task 6), components (Tasks 1-9 backend, 10-15 frontend), data flow (Tasks 7-8, 14-15), error handling (Pydantic validation in Task 7, 404 in Task 8), testing (TDD steps throughout), migration/cutover (Task 16).
- **Placeholder scan:** No TBD/TODO; all code blocks are complete, runnable ports of the real TS source read from this repo, not invented.
- **Type/interface consistency:** Python service function names (`compute_gap_analysis`, `compute_allocation`, `select_fund_examples`, `select_insurance_examples`) and their dict-key return shapes are consistent between Tasks 3-5 (definition) and Tasks 7-8 (consumption). Frontend `apiClient.get/post` signature (Task 10) is used identically in Tasks 14-15. JSON field names returned by `GET /api/dashboard` (Task 8) match exactly what `Dashboard.jsx` destructures (Task 15).
- **Known deviations from the TS version, both intentional and noted inline:** (1) onboarding router uses submitted payload values directly for engine input instead of re-reading the committed DB row (Task 7, numerically identical); (2) demo-user cookie can always be set immediately since FastAPI has no Server-Component restriction (Task 6, removes a documented tech-debt item rather than reproducing it); (3) `GET /api/dashboard` is a new endpoint with no TS equivalent, required because a Vite SPA has no server-side rendering (Task 8, documented in the spec's Components section).

