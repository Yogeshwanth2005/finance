"""Return maths and ranking for one fund's NAV history (spec section 5.2)."""

import random
from datetime import date, timedelta

import pytest

from lib.funds import CatalogEntry, build_row, clean_history, rank_rows, summarise_history
from models.funds import FundRow

END = date(2026, 9, 23)


def steady(years, annual_pct=12.0, end=END):
    """One NAV a day compounding at exactly annual_pct a year, ending on `end`."""
    days = round(years * 365.25)
    return [(end - timedelta(days=offset), 100 * (1 + annual_pct / 100) ** (-offset / 365.25)) for offset in range(days, -1, -1)]


def test_steady_growth_reports_the_same_annualised_rate_in_every_window():
    summary = summarise_history(steady(7))
    for window in ("1y", "3y", "5y", "max"):
        assert summary.returns[window] == pytest.approx(12.0, abs=0.05), window
    assert summary.max_is_annualised is True


def test_a_fund_shorter_than_a_window_has_no_return_for_it():
    summary = summarise_history(steady(2.5))
    assert summary.returns["1y"] == pytest.approx(12.0, abs=0.05)
    assert summary.returns["3y"] is None and summary.returns["5y"] is None
    assert summary.returns["max"] == pytest.approx(12.0, abs=0.05)


def test_a_fund_under_a_year_old_reports_its_absolute_return_as_max():
    history = [(END - timedelta(days=200 - i), 100 + i * 0.05) for i in range(201)]
    summary = summarise_history(history)
    assert summary.max_is_annualised is False
    assert summary.returns["max"] == pytest.approx(10.0, abs=0.01)  # 100 -> 110 over 200 days, not annualised
    assert summary.returns["1y"] is None


@pytest.mark.parametrize("days_after_window_start, has_3y", [(5, True), (7, True), (9, False)])
def test_a_fund_launched_just_after_a_windows_start_still_gets_that_window(days_after_window_start, has_3y):
    window_start = END - timedelta(days=round(3 * 365.25))
    first = window_start + timedelta(days=days_after_window_start)
    history = [(first + timedelta(days=i), 100 * 1.0003**i) for i in range((END - first).days + 1)]
    assert (summarise_history(history).returns["3y"] is not None) is has_3y


def test_a_non_positive_nav_is_dropped_and_the_rest_of_the_series_is_used():
    history = steady(4)
    middle = len(history) // 2
    history[middle] = (history[middle][0], 0.0)
    assert summarise_history(history).returns["3y"] == pytest.approx(12.0, abs=0.05)


def test_a_glitch_move_between_two_navs_drops_the_fund():
    history = steady(4)
    middle = len(history) // 2
    history[middle:] = [(d, nav * 0.5) for d, nav in history[middle:]]  # a 50% one-day fall
    assert summarise_history(history) is None


def test_a_large_fall_below_the_glitch_threshold_is_kept():
    history = steady(4)
    middle = len(history) // 2
    history[middle:] = [(d, nav * 0.7) for d, nav in history[middle:]]  # a 30% one-day fall
    assert summarise_history(history) is not None


def test_unsorted_input_and_duplicate_dates_give_the_same_answer_as_clean_input():
    clean = steady(4)
    shuffled = clean + clean[:50]
    random.Random(7).shuffle(shuffled)
    assert summarise_history(shuffled) == summarise_history(clean)


@pytest.mark.parametrize("history", [[], [(END, 100.0)], [(END, 0.0), (END - timedelta(days=1), 0.0)], [(END, 100.0), (END, 101.0)]])
def test_a_history_too_short_or_empty_is_unusable(history):
    assert summarise_history(history) is None


def test_clean_history_returns_ascending_unique_positive_points():
    points = clean_history([(END, 101.0), (END - timedelta(days=1), 100.0), (END - timedelta(days=1), 100.0), (END - timedelta(days=2), -5.0)])
    assert points == [(END - timedelta(days=1), 100.0), (END, 101.0)]


def test_build_row_carries_catalog_identity_and_latest_nav():
    entry = CatalogEntry("100001", "Alpha Bluechip Fund", "Alpha Mutual Fund", "large", 1.0, END)
    row = build_row(entry, steady(4))
    assert (row.scheme_code, row.name, row.fund_house, row.segment) == ("100001", "Alpha Bluechip Fund", "Alpha Mutual Fund", "large")
    assert row.nav_date == END
    assert row.start_date == END - timedelta(days=round(4 * 365.25))
    assert build_row(entry, []) is None


def row(name, annualised=True, **returns):
    values = {"1y": None, "3y": None, "5y": None, "max": None, **returns}
    return FundRow(
        scheme_code=name, name=name, fund_house="Alpha Mutual Fund", segment="large", nav=10.0,
        nav_date=END, start_date=END - timedelta(days=4000), returns=values, max_is_annualised=annualised,
    )


def test_rank_orders_best_first_and_breaks_ties_by_name():
    rows = [row("B", **{"3y": 10.0}), row("A", **{"3y": 10.0}), row("C", **{"3y": 12.5})]
    assert [r.name for r in rank_rows(rows, "3y")] == ["C", "A", "B"]


def test_rank_leaves_out_funds_without_that_window():
    rows = [row("Old", **{"3y": 9.0, "5y": 8.0}), row("New", **{"3y": 20.0})]
    assert [r.name for r in rank_rows(rows, "5y")] == ["Old"]


def test_max_ranks_full_year_funds_above_newer_funds_even_when_the_newer_absolute_return_is_bigger():
    rows = [row("NewHot", annualised=False, max=30.0), row("Steady", max=11.0), row("Better", max=13.0)]
    assert [r.name for r in rank_rows(rows, "max")] == ["Better", "Steady", "NewHot"]


def test_rank_of_nothing_is_empty():
    assert rank_rows([], "3y") == []
