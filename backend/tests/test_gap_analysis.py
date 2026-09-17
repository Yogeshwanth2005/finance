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
