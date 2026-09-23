from lib.finance_config import (
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
