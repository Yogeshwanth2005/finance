"""Edge cases of the household analysis, called directly on _analysis() (no server, no MongoDB).

Expected values are worked out from the rules in routers/profile.py, not copied from a run:
term need = 15 x combined earned income + liabilities; health need = 10L + 2L/dependent + city add-on (tier 1/2/3 = 5/3/2),
capped at 25L; emergency fund = 6 x monthly expenses; the protection score caps each ratio at 1 (50/25/25 weights).
"""

import pytest
from pydantic import ValidationError

from models.profile import ProfileInput
from routers.profile import _analysis

from .profiles import payload


def analyse(**overrides):
    return _analysis(ProfileInput(**payload(**overrides)))


def test_zero_liabilities_leaves_term_need_at_fifteen_times_income():
    a = analyse(home_loan=0, other_loans=0, other_debts=0, monthly_emi=0)
    assert a.total_liabilities == 0
    assert a.recommended_term_cover_crore == 4.95  # 15 x (24L + 9L)
    assert a.term_gap_crore == 4.45  # less the 50L already held
    assert a.annual_emi == 0
    assert a.annual_surplus_before_protection == 2_580_000  # 36L - 10.2L expenses


def test_zero_liabilities_ratios_use_the_zero_denominator_convention():
    # Cover-to-liabilities has no meaningful value without liabilities; the spec says zero denominators return 0.
    k = analyse(home_loan=0, other_loans=0, other_debts=0, monthly_emi=0).kpis
    assert k.cover_to_liabilities_ratio == 0
    assert k.liabilities_to_income_multiple == 0
    assert k.debt_to_income_pct == 0
    assert k.savings_rate_pct == 71.7  # 25.8L / 36L


def test_single_filer_ignores_a_stray_spouse_income():
    profile = ProfileInput(**payload(marital_status="single", spouse_income=900_000, spouse_full_name="Ghost", spouse_age=40))
    assert (profile.spouse_income, profile.spouse_full_name, profile.spouse_age) == (0, "", 0)
    a = _analysis(profile)
    assert a.annual_household_income == 2_700_000  # 24L salary + 3L bonus, no spouse
    assert a.recommended_term_cover_crore == pytest.approx(4.295, abs=0.01)  # 15 x 24L + 69.5L liabilities


def test_single_filer_is_analysed_exactly_like_a_married_household_with_no_spouse_income():
    single = analyse(marital_status="single", spouse_income=900_000)
    married_alone = analyse(marital_status="married", spouse_income=0)
    assert single.model_dump() == married_alone.model_dump()


@pytest.mark.parametrize("tier, need", [("tier_1", 15), ("tier_2", 13), ("tier_3", 12)])
def test_no_dependents_health_need_is_the_ten_lakh_base_plus_the_city_add_on(tier, need):
    a = analyse(dependents=0, city_tier=tier)
    assert a.recommended_health_cover_lakh == need
    assert a.health_gap_lakh == need - 5  # 5L already held


@pytest.mark.parametrize("dependents, need", [(4, 23), (5, 25), (6, 25), (12, 25)])
def test_large_family_health_need_is_capped_at_25_lakh(dependents, need):
    # tier 1: 10 + 2 x dependents + 5 reaches 25 at five dependents; 12 dependents would be 39 uncapped.
    a = analyse(dependents=dependents, city_tier="tier_1")
    assert a.recommended_health_cover_lakh == need
    assert a.health_gap_lakh == need - 5


def test_over_insured_household_has_no_gaps():
    a = analyse(existing_term_cover_crore=10, current_health_cover_lakh=50, emergency_savings=1_020_000)
    assert a.term_gap_crore == 0
    assert a.health_gap_lakh == 0
    assert a.emergency_gap == 0
    assert a.emergency_months == 12


def test_over_insured_adequacy_percentages_are_not_capped_but_the_score_is():
    a = analyse(existing_term_cover_crore=10, current_health_cover_lakh=50, emergency_savings=1_020_000)
    assert a.kpis.term_cover_adequacy_pct == 177.1  # 10 Cr / 5.645 Cr
    assert a.kpis.health_cover_adequacy_pct == 238.1  # 50L / 21L
    assert a.kpis.emergency_coverage_pct == 200
    assert a.protection_score == 100
    assert a.score_label == "Strong foundation"


def test_over_insured_household_budgets_only_the_health_premium():
    a = analyse(existing_term_cover_crore=10, current_health_cover_lakh=50, emergency_savings=1_020_000)
    assert a.annual_insurance_budget == 34_000  # 22,000 + 4,000 x 3 dependents; no term premium without a term gap
    assert a.investable_surplus == 1_850_000  # 18.84L surplus - 34,000


def test_deficit_household_keeps_the_negative_cash_flow_visible():
    a = analyse(monthly_expenses=250_000, monthly_emi=80_000)
    assert a.annual_surplus_before_protection == -360_000  # 36L - 30L expenses - 9.6L EMI
    assert a.kpis.savings_rate_pct == -10
    assert a.kpis.debt_to_income_pct == 26.7  # 80k / 3L a month


def test_deficit_household_has_no_investable_surplus():
    a = analyse(monthly_expenses=250_000, monthly_emi=80_000)
    assert a.investable_surplus == 0
    assert a.annual_insurance_budget > a.annual_surplus_before_protection  # protection is unaffordable before investing


def test_deficit_household_emergency_fund_is_measured_against_its_higher_expenses():
    a = analyse(monthly_expenses=250_000, monthly_emi=80_000)
    assert a.emergency_goal == 1_500_000
    assert a.emergency_gap == 1_200_000
    assert a.emergency_months == 1.2
    assert a.protection_score == 15
    assert a.score_label == "Protection gap"


@pytest.mark.parametrize(
    "field, value",
    [
        ("annual_income", 0),
        ("monthly_expenses", 0),
        ("age", 17),
        ("age", 76),
        ("dependents", 13),
        ("monthly_emi", -1),
    ],
)
def test_degenerate_inputs_are_rejected_before_any_division(field, value):
    with pytest.raises(ValidationError, match=field):
        ProfileInput(**payload(**{field: value}))
