"""compute_equity_split divides the equity slice into large / mid / small cap by risk tolerance (spec section 6.1)."""

import pytest

from lib.allocation import compute_allocation, compute_equity_split

RISKS = ["conservative", "moderate", "aggressive"]


def parts(result):
    return (result["large_pct"], result["mid_pct"], result["small_pct"])


def test_moderate_splits_the_equity_slice_60_25_15():
    assert parts(compute_equity_split("moderate", 70)) == (42.0, 17.5, 10.5)


def test_conservative_holds_more_large_cap():
    assert parts(compute_equity_split("conservative", 56)) == (38.1, 11.2, 6.7)


def test_aggressive_holds_more_mid_and_small_cap():
    assert parts(compute_equity_split("aggressive", 84)) == (43.7, 25.2, 15.1)


def test_no_equity_means_no_cap_split():
    assert parts(compute_equity_split("moderate", 0)) == (0.0, 0.0, 0.0)


@pytest.mark.parametrize("risk", RISKS)
@pytest.mark.parametrize("years", [1, 3, 4, 10, 60])
def test_always_sums_to_the_equity_slice_and_never_goes_negative(risk, years):
    for age in range(18, 76):
        equity = compute_allocation(age, risk, years)["equity_pct"]
        result = parts(compute_equity_split(risk, equity))
        assert sum(result) == pytest.approx(equity, abs=1e-9), (age, risk, years)
        assert min(result) >= 0, (age, risk, years)


@pytest.mark.parametrize("risk", RISKS)
def test_large_is_the_biggest_slice_and_small_never_exceeds_mid(risk):
    large, mid, small = parts(compute_equity_split(risk, 70))
    assert large > mid >= small


def test_a_higher_risk_tolerance_moves_weight_out_of_large_cap():
    large_pcts = [compute_equity_split(risk, 70)["large_pct"] for risk in RISKS]
    assert large_pcts == sorted(large_pcts, reverse=True)
