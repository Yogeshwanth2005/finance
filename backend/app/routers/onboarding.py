from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from supabase import Client

from app.db import get_supabase
from app.demo_user import get_or_create_demo_user
from app.models import User
from app.mapping import get_table_name
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
    debts: List[DebtIn] = []
    existing_term_cover_amount: float = Field(alias="existingTermCoverAmount")
    personal_health_cover_amount: float = Field(alias="personalHealthCoverAmount")
    employer_health_cover_amount: float = Field(alias="employerHealthCoverAmount")


@router.post("/api/onboarding/submit")
def submit_onboarding(
    payload: OnboardingSubmission,
    user: User = Depends(get_or_create_demo_user),
    supabase: Client = Depends(get_supabase),
):
    now = datetime.now(timezone.utc).isoformat()

    # 1. Handle Financial Profile (Upsert)
    financial_profile_table = get_table_name("FinancialProfile")
    profile_data = {
        "userId": user.id,
        "age": payload.age,
        "dependentsCount": payload.dependents_count,
        "monthlyIncome": payload.monthly_income,
        "monthlyExpenses": payload.monthly_expenses,
        "currentSavings": payload.current_savings,
        "riskTolerance": payload.risk_tolerance,
        "investmentHorizonYears": payload.investment_horizon_years,
        "consentGivenAt": now,
        "updatedAt": now,
    }

    # Upsert based on userId unique constraint
    profile_res = supabase.table(financial_profile_table).upsert(profile_data, on_conflict="userId").execute()
    financial_profile = profile_res.data[0] if profile_res.data else None

    if not financial_profile:
        raise HTTPException(status_code=500, detail="Failed to save financial profile")

    # 2. Handle Existing Debts (Delete and Re-insert)
    debt_table = get_table_name("ExistingDebt")
    supabase.table(debt_table).delete().eq("financialProfileId", financial_profile["id"]).execute()

    debts_to_insert = [
        {
            "financialProfileId": financial_profile["id"],
            "label": debt.label,
            "outstandingAmount": debt.outstanding_amount,
            "interestRatePct": debt.interest_rate_pct,
            "tenureMonths": debt.tenure_months,
        }
        for debt in payload.debts
    ]
    if debts_to_insert:
        supabase.table(debt_table).insert(debts_to_insert).execute()

    # 3. Handle Insurance Profile (Upsert)
    insurance_profile_table = get_table_name("InsuranceProfile")
    insurance_data = {
        "userId": user.id,
        "existingTermCoverAmount": payload.existing_term_cover_amount,
        "personalHealthCoverAmount": payload.personal_health_cover_amount,
        "employerHealthCoverAmount": payload.employer_health_cover_amount,
        "consentGivenAt": now,
        "updatedAt": now,
    }
    supabase.table(insurance_profile_table).upsert(insurance_data, on_conflict="userId").execute()

    # 4. Compute Results
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

    # 5. Store Results
    gap_table = get_table_name("GapAnalysisResult")
    supabase.table(gap_table).insert({
        "userId": user.id,
        "emergencyFundTarget": gap_analysis["emergency_fund_target"],
        "emergencyFundCurrent": gap_analysis["emergency_fund_current"],
        "emergencyFundStatus": gap_analysis["emergency_fund_status"],
        "debtPriorityOrder": gap_analysis["debt_priority_order"],
        "termCoverGap": gap_analysis["term_cover_gap"],
        "healthCoverGap": gap_analysis["health_cover_gap"],
        "emergencyFundCoveragePct": gap_analysis["emergency_fund_coverage_pct"],
        "termCoverAdequacyPct": gap_analysis["term_cover_adequacy_pct"],
        "healthCoverAdequacyPct": gap_analysis["health_cover_adequacy_pct"],
        "savingsRatePct": gap_analysis["savings_rate_pct"],
        "debtToIncomePct": gap_analysis["debt_to_income_pct"],
        "computedAt": now,
    }).execute()

    alloc_table = get_table_name("AllocationResult")
    supabase.table(alloc_table).insert({
        "userId": user.id,
        "equityPct": allocation["equity_pct"],
        "debtPct": allocation["debt_pct"],
        "goldPct": allocation["gold_pct"],
        "computedAt": now,
    }).execute()

    return {"success": True}
