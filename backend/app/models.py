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
