"""_analysis() reports the glide-path split for the profile's age, risk tolerance and investment horizon."""

import pytest

from lib.allocation import compute_allocation
from models.profile import ProfileInput
from routers.profile import _analysis

from .profiles import payload


def allocation(**overrides):
    return _analysis(ProfileInput(**payload(**overrides))).allocation


def split(result):
    return (result.equity_pct, result.debt_pct, result.gold_pct)


def test_moderate_long_horizon_is_hundred_minus_age_with_a_flat_gold_sleeve():
    assert split(allocation(age=30, risk_tolerance="moderate", investment_horizon_years=10)) == (70, 20, 10)


def test_aggressive_scales_equity_up():
    assert split(allocation(age=30, risk_tolerance="aggressive", investment_horizon_years=10)) == (84, 6, 10)


def test_conservative_scales_equity_down():
    assert split(allocation(age=30, risk_tolerance="conservative", investment_horizon_years=10)) == (56, 34, 10)


def test_a_three_year_horizon_moves_twenty_points_from_equity_to_debt():
    assert split(allocation(age=30, risk_tolerance="moderate", investment_horizon_years=3)) == (50, 40, 10)


def test_a_four_year_horizon_is_not_shifted():
    assert split(allocation(age=30, risk_tolerance="moderate", investment_horizon_years=4)) == (70, 20, 10)


def test_gold_is_capped_by_what_equity_leaves():
    assert split(allocation(age=20, risk_tolerance="aggressive", investment_horizon_years=10)) == (96, 0, 4)


def test_oldest_conservative_short_horizon_holds_no_equity():
    assert split(allocation(age=75, risk_tolerance="conservative", investment_horizon_years=2)) == (0, 90, 10)


def test_a_profile_saved_before_the_fields_existed_gets_the_moderate_ten_year_split():
    assert split(_analysis(ProfileInput(**payload(age=35))).allocation) == (65, 25, 10)


@pytest.mark.parametrize("risk", ["conservative", "moderate", "aggressive"])
@pytest.mark.parametrize("years", [1, 3, 4, 10, 60])
def test_matches_compute_allocation_and_always_sums_to_100_for_every_valid_age(risk, years):
    for age in range(18, 76):
        got = allocation(age=age, risk_tolerance=risk, investment_horizon_years=years)
        expected = compute_allocation(age=age, risk_tolerance=risk, investment_horizon_years=years)
        assert got.equity_pct == round(expected["equity_pct"], 1), (age, risk, years)
        assert got.debt_pct == round(expected["debt_pct"], 1), (age, risk, years)
        assert got.gold_pct == round(expected["gold_pct"], 1), (age, risk, years)
        assert got.equity_pct + got.debt_pct + got.gold_pct == pytest.approx(100), (age, risk, years)
