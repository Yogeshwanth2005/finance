"""_analysis() carries the equity split and the goal check next to the untouched glide-path allocation (spec section 6)."""

import pytest

from models.profile import ProfileInput
from routers.profile import _analysis

from .profiles import payload


def analysis(**overrides):
    return _analysis(ProfileInput(**payload(**overrides)))


def test_equity_split_is_reported_and_adds_back_to_the_equity_slice():
    result = analysis(age=30, risk_tolerance="moderate", investment_horizon_years=10)
    split = result.equity_split
    assert (split.large_pct, split.mid_pct, split.small_pct) == (42.0, 17.5, 10.5)
    assert split.large_pct + split.mid_pct + split.small_pct == pytest.approx(result.allocation.equity_pct)


def test_the_glide_path_allocation_is_unchanged():
    result = analysis(age=30, risk_tolerance="moderate", investment_horizon_years=10)
    assert (result.allocation.equity_pct, result.allocation.debt_pct, result.allocation.gold_pct) == (70, 20, 10)


def test_goal_check_reports_target_expected_return_and_crash_line():
    goal = analysis(age=30, risk_tolerance="moderate", investment_horizon_years=10).goal_check
    assert (goal.target_pct, goal.expected_return_pct, goal.crash_loss_pct) == (10, 10.6, 25.8)
    assert goal.beats_target is True


def test_a_short_horizon_below_target_suppresses_the_equity_suggestion():
    goal = analysis(age=50, risk_tolerance="moderate", investment_horizon_years=3).goal_check
    assert goal.beats_target is False
    assert goal.suggestion_suppressed is True
    assert goal.min_equity_pct is None


def test_zero_equity_profile_still_produces_a_goal_check():
    # age 75, conservative, 2-year horizon: (100 - 75) x 0.8 - 20 = 0 equity
    result = analysis(age=75, risk_tolerance="conservative", investment_horizon_years=2)
    assert result.allocation.equity_pct == 0
    assert (result.equity_split.large_pct, result.equity_split.mid_pct, result.equity_split.small_pct) == (0.0, 0.0, 0.0)
    assert result.goal_check.crash_loss_pct == 0.0
    assert result.goal_check.suggestion_suppressed is True


def test_formula_notes_state_the_new_assumptions():
    notes = " ".join(analysis().formula_notes)
    assert "Goal" in notes
    assert "March-2020" in notes
    assert "large / mid / small" in notes
