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
