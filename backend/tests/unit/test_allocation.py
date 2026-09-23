import pytest
from lib.allocation import compute_allocation, select_fund_examples


def test_moderate_long_horizon():
    result = compute_allocation(age=30, risk_tolerance="moderate", investment_horizon_years=10)
    assert result["equity_pct"] == 70
    assert result["gold_pct"] == 10
    assert result["debt_pct"] == 20


def test_aggressive_scales_equity_up():
    result = compute_allocation(age=30, risk_tolerance="aggressive", investment_horizon_years=10)
    assert result["equity_pct"] == 84
    assert result["gold_pct"] == 10
    assert result["debt_pct"] == 6


def test_conservative_scales_equity_down():
    result = compute_allocation(age=30, risk_tolerance="conservative", investment_horizon_years=10)
    assert result["equity_pct"] == 56
    assert result["gold_pct"] == 10
    assert result["debt_pct"] == 34


def test_short_horizon_shifts_equity_to_debt():
    result = compute_allocation(age=30, risk_tolerance="moderate", investment_horizon_years=2)
    assert result["equity_pct"] == 50
    assert result["gold_pct"] == 10
    assert result["debt_pct"] == 40


def test_gold_capped_by_remaining_after_equity():
    result = compute_allocation(age=20, risk_tolerance="aggressive", investment_horizon_years=10)
    assert result["equity_pct"] == 96
    assert result["gold_pct"] == 4
    assert result["debt_pct"] == 0


def test_equity_clamped_to_100():
    result = compute_allocation(age=5, risk_tolerance="aggressive", investment_horizon_years=10)
    assert result["equity_pct"] == 100
    assert result["gold_pct"] == 0
    assert result["debt_pct"] == 0


def test_equity_clamped_to_0():
    result = compute_allocation(age=90, risk_tolerance="conservative", investment_horizon_years=2)
    assert result["equity_pct"] == 0
    assert result["gold_pct"] == 10
    assert result["debt_pct"] == 90


def test_buckets_always_sum_to_100():
    result = compute_allocation(age=45, risk_tolerance="moderate", investment_horizon_years=1)
    assert result["equity_pct"] + result["debt_pct"] + result["gold_pct"] == 100


ALL_FUNDS = [
    {"id": "e1", "category": "equity_large_cap", "aum_cr": 5000},
    {"id": "e2", "category": "equity_diversified", "aum_cr": 12000},
    {"id": "e3", "category": "equity_large_cap", "aum_cr": 8000},
    {"id": "d1", "category": "debt_short_duration", "aum_cr": 3000},
    {"id": "d2", "category": "fixed_deposit", "aum_cr": 9000},
    {"id": "g1", "category": "gold_etf", "aum_cr": 2000},
    {"id": "g2", "category": "sovereign_gold_bond", "aum_cr": 1000},
]


def test_equity_bucket_maps_both_categories_sorted_by_aum_desc():
    result = select_fund_examples("equity", ALL_FUNDS, count=2)
    assert [f["id"] for f in result] == ["e2", "e3"]


def test_debt_bucket_maps_debt_and_fixed_deposit():
    result = select_fund_examples("debt", ALL_FUNDS, count=3)
    assert [f["id"] for f in result] == ["d2", "d1"]


def test_gold_bucket_maps_gold_etf_and_sgb():
    result = select_fund_examples("gold", ALL_FUNDS, count=3)
    assert [f["id"] for f in result] == ["g1", "g2"]


def test_defaults_count_to_config_value():
    many_equity_funds = [{"id": f"e{i}", "category": "equity_large_cap", "aum_cr": i} for i in range(5)]
    assert len(select_fund_examples("equity", many_equity_funds)) == 3
