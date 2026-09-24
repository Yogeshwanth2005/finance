"""compute_goal_check compares the mix's expected return with inflation plus a risk-scaled margin and reports the crash cost (spec sections 6.2, 6.3)."""

import pytest

from lib.allocation import compute_allocation, compute_equity_split, compute_goal_check

RISKS = ["conservative", "moderate", "aggressive"]


def check(age, risk, years=10):
    allocation = compute_allocation(age, risk, years)
    split = compute_equity_split(risk, allocation["equity_pct"])
    return compute_goal_check(risk, years, allocation, split)


@pytest.mark.parametrize(
    "age, risk, expected, target, crash",
    [
        (30, "conservative", 9.8, 9, 20.7),
        (30, "moderate", 10.6, 10, 25.8),
        (30, "aggressive", 11.4, 11, 31.0),
    ],
)
def test_a_thirty_year_old_beats_the_target_at_every_risk_level(age, risk, expected, target, crash):
    goal = check(age, risk)
    assert (goal["expected_return_pct"], goal["target_pct"], goal["crash_loss_pct"]) == (expected, target, crash)
    assert goal["beats_target"] is True
    assert goal["reachable"] is True
    assert goal["min_equity_pct"] is None and goal["crash_loss_at_min_equity_pct"] is None
    assert goal["suggestion_suppressed"] is False


def test_target_is_inflation_plus_the_risk_scaled_margin():
    goals = {risk: check(30, risk) for risk in RISKS}
    assert [(g["inflation_pct"], g["margin_pct"], g["target_pct"]) for g in goals.values()] == [(6, 3, 9), (6, 4, 10), (6, 5, 11)]


def test_a_fifty_year_old_moderate_falls_short_and_is_told_how_much_equity_would_reach_the_goal():
    goal = check(50, "moderate")
    assert goal["expected_return_pct"] == 9.6
    assert goal["beats_target"] is False
    assert goal["reachable"] is True
    assert goal["min_equity_pct"] == 58.6
    assert goal["crash_loss_pct"] == 18.4
    assert goal["crash_loss_at_min_equity_pct"] == 21.6


@pytest.mark.parametrize("risk", RISKS)
def test_the_suggested_equity_share_lands_on_the_target_when_plugged_back_in(risk):
    checked = 0
    for age in range(40, 76):
        goal = check(age, risk)
        if goal["beats_target"] or not goal["reachable"]:
            continue
        equity = goal["min_equity_pct"]
        gold = compute_allocation(age, risk, 10)["gold_pct"]
        allocation = {"equity_pct": equity, "debt_pct": 100 - gold - equity, "gold_pct": gold}
        plugged = compute_goal_check(risk, 10, allocation, compute_equity_split(risk, equity))
        assert plugged["expected_return_pct"] >= goal["target_pct"] - 0.06, (age, risk)
        checked += 1
    assert checked > 0


def test_a_short_horizon_below_target_reports_the_return_but_never_suggests_more_equity():
    goal = check(50, "moderate", years=3)
    assert goal["beats_target"] is False
    assert goal["suggestion_suppressed"] is True
    assert goal["reachable"] is None
    assert goal["min_equity_pct"] is None and goal["crash_loss_at_min_equity_pct"] is None


def test_an_all_debt_and_gold_mix_still_gets_a_suggestion_on_a_long_horizon():
    allocation = {"equity_pct": 0, "debt_pct": 90, "gold_pct": 10}
    split = {"large_pct": 0.0, "mid_pct": 0.0, "small_pct": 0.0}
    goal = compute_goal_check("conservative", 10, allocation, split)
    assert goal["beats_target"] is False
    assert goal["min_equity_pct"] == 39.9
    assert goal["crash_loss_pct"] == 0.0


def test_a_goal_no_mix_can_reach_is_reported_as_unreachable(monkeypatch):
    monkeypatch.setattr("lib.allocation.EXPECTED_RETURN_PCT", {"large": 8, "mid": 8, "small": 8, "debt": 7, "gold": 8})
    goal = check(50, "moderate")
    assert goal["beats_target"] is False
    assert goal["reachable"] is False
    assert goal["min_equity_pct"] is None


def test_equity_that_does_not_out_earn_debt_is_unreachable_not_a_division_error(monkeypatch):
    monkeypatch.setattr("lib.allocation.EXPECTED_RETURN_PCT", {"large": 7, "mid": 7, "small": 7, "debt": 7, "gold": 8})
    goal = check(50, "moderate")
    assert goal["reachable"] is False
    assert goal["min_equity_pct"] is None
