from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from lib.auth import get_current_user
from lib.db import db
from models.profile import (
    FamilyProfile,
    FinancialAnalysis,
    Plan,
    ProfileInput,
    ProfileKpis,
    ProfileResponse,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _plans() -> list[Plan]:
    return [
        Plan(
            id="term-1",
            category="term",
            name="Click 2 Protect Super",
            provider="HDFC Life",
            csr="99.2%",
            annual_premium_from=18500,
            cover_label="Illustrative term cover",
            highlights=["Flexible payout options", "Income replacement focus", "Optional riders"],
            fit="Best for income replacement and long-term family protection",
        ),
        Plan(
            id="term-2",
            category="term",
            name="iProtect Smart",
            provider="ICICI Prudential",
            csr="98.3%",
            annual_premium_from=17200,
            cover_label="Illustrative term cover",
            highlights=["Multiple claim payout choices", "Terminal illness benefit", "Digital servicing"],
            fit="A lower-premium option to compare with your protection gap",
        ),
        Plan(
            id="health-1",
            category="health",
            name="Optima Secure",
            provider="HDFC ERGO",
            csr="98.6%",
            annual_premium_from=26500,
            cover_label="Illustrative family floater",
            highlights=["Restore benefit", "No room-rent cap", "Super top-up compatible"],
            fit="Strong floater baseline for growing families",
        ),
        Plan(
            id="health-2",
            category="health",
            name="Care Supreme",
            provider="Care Health",
            csr="96.6%",
            annual_premium_from=22800,
            cover_label="Illustrative family floater",
            highlights=["Unlimited recharge", "Wellness benefits", "Wide hospital network"],
            fit="Value-led cover when the emergency fund is still being built",
        ),
    ]


def _analysis(input_data: ProfileInput) -> FinancialAnalysis:
    annual_income = input_data.annual_income + input_data.spouse_income + input_data.annual_bonus
    annual_expenses = input_data.monthly_expenses * 12
    annual_emi = input_data.monthly_emi * 12
    liabilities = input_data.home_loan + input_data.other_loans + input_data.other_debts

    term_need_rupees = ((input_data.annual_income + input_data.spouse_income) * 15) + liabilities
    existing_term_rupees = input_data.existing_term_cover_crore * 10_000_000
    term_gap_rupees = max(0, term_need_rupees - existing_term_rupees)
    term_need_crore = round(term_need_rupees / 10_000_000, 2)
    term_gap_crore = round(term_gap_rupees / 10_000_000, 2)

    city_add_on = {"tier_1": 5, "tier_2": 3, "tier_3": 2}[input_data.city_tier]
    health_need_lakh = min(25, max(10, 10 + (input_data.dependents * 2) + city_add_on))
    health_gap_lakh = round(max(0, health_need_lakh - input_data.current_health_cover_lakh), 1)

    emergency_goal = round(input_data.monthly_expenses * 6, 2)
    emergency_gap = round(max(0, emergency_goal - input_data.emergency_savings), 2)
    emergency_months = round(input_data.emergency_savings / input_data.monthly_expenses, 1)

    monthly_household_income = annual_income / 12
    emergency_coverage_pct = (input_data.emergency_savings / emergency_goal * 100) if emergency_goal else 0
    term_cover_adequacy_pct = (existing_term_rupees / term_need_rupees * 100) if term_need_rupees else 0
    health_cover_adequacy_pct = (input_data.current_health_cover_lakh / health_need_lakh * 100) if health_need_lakh else 0
    savings_rate_pct = ((annual_income - annual_expenses - annual_emi) / annual_income * 100) if annual_income else 0
    debt_to_income_pct = (input_data.monthly_emi / monthly_household_income * 100) if monthly_household_income else 0
    cover_to_liabilities_ratio = (existing_term_rupees / liabilities) if liabilities else 0
    liabilities_to_income_multiple = (liabilities / annual_income) if annual_income else 0

    term_premium = term_gap_crore * 17_500
    health_premium = 22_000 + (input_data.dependents * 4_000)
    annual_insurance_budget = round(term_premium + health_premium, 2)
    before_protection = annual_income - annual_expenses - annual_emi
    investable_surplus = round(max(0, before_protection - annual_insurance_budget), 2)

    term_ratio = 1 if term_need_rupees == 0 else min(existing_term_rupees / term_need_rupees, 1)
    health_ratio = 1 if health_need_lakh == 0 else min(input_data.current_health_cover_lakh / health_need_lakh, 1)
    emergency_ratio = min(input_data.emergency_savings / emergency_goal, 1) if emergency_goal else 1
    protection_score = round((term_ratio * 50) + (health_ratio * 25) + (emergency_ratio * 25))
    score_label = "Strong foundation" if protection_score >= 75 else "Needs attention" if protection_score >= 45 else "Protection gap"

    return FinancialAnalysis(
        annual_household_income=round(annual_income, 2),
        annual_expenses=round(annual_expenses, 2),
        annual_emi=round(annual_emi, 2),
        total_liabilities=round(liabilities, 2),
        annual_surplus_before_protection=round(before_protection, 2),
        annual_insurance_budget=annual_insurance_budget,
        investable_surplus=investable_surplus,
        recommended_term_cover_crore=term_need_crore,
        term_gap_crore=term_gap_crore,
        recommended_health_cover_lakh=health_need_lakh,
        health_gap_lakh=health_gap_lakh,
        emergency_goal=emergency_goal,
        emergency_gap=emergency_gap,
        emergency_months=emergency_months,
        kpis=ProfileKpis(
            emergency_coverage_pct=round(emergency_coverage_pct, 1),
            runway_months=emergency_months,
            term_cover_adequacy_pct=round(term_cover_adequacy_pct, 1),
            health_cover_adequacy_pct=round(health_cover_adequacy_pct, 1),
            savings_rate_pct=round(savings_rate_pct, 1),
            debt_to_income_pct=round(debt_to_income_pct, 1),
            cover_to_liabilities_ratio=round(cover_to_liabilities_ratio, 2),
            liabilities_to_income_multiple=round(liabilities_to_income_multiple, 2),
        ),
        protection_score=protection_score,
        score_label=score_label,
        formula_notes=[
            "Term cover = 15× combined earned income + total liabilities − existing term cover.",
            f"Health baseline = 10L + family-size and city adjustment, capped at 25L (Tier {input_data.city_tier[-1]}).",
            "Emergency fund target = 6× monthly household expenses before investing surplus.",
            "Savings rate = (household income − annual expenses − annual EMI) ÷ household income.",
            "Debt-to-income = monthly EMI ÷ monthly household income; any 40–50% reference is illustrative, not advice.",
        ],
        disclaimer="Educational estimates only. They are not financial, tax, medical, or insurance advice. Verify policy terms, exclusions, underwriting, claim experience, and premiums with a licensed advisor before buying.",
    )


def _response(document: dict) -> ProfileResponse:
    profile = FamilyProfile(**document["profile"])
    analysis = _analysis(ProfileInput(**document["profile"]))
    return ProfileResponse(profile=profile, analysis=analysis, plans=_plans())


@router.post("", response_model=ProfileResponse)
async def save_profile(input_data: ProfileInput, user: dict = Depends(get_current_user)) -> ProfileResponse:
    profile = FamilyProfile(id=user["id"], **input_data.model_dump())
    document = {"_id": user["id"], "owner_id": user["id"], "profile": profile.model_dump()}
    await db.profiles.replace_one({"_id": user["id"]}, document, upsert=True)
    await db.users.update_one({"_id": user["id"]}, {"$set": {"profile_complete": True}})
    return _response(document)


@router.get("", response_model=ProfileResponse)
async def get_profile(user: dict = Depends(get_current_user)) -> ProfileResponse:
    document = await db.profiles.find_one({"_id": user["id"]})
    if not document:
        raise HTTPException(status_code=404, detail="No family profile saved yet")
    return _response(document)


@router.get("/current", response_model=ProfileResponse | None)
async def get_current_profile(user: dict = Depends(get_current_user)) -> ProfileResponse | None:
    document = await db.profiles.find_one({"_id": user["id"]})
    return _response(document) if document else None