"""Returns computed from AMFI's dated reports: the fetch plan, the 1y / 3y / 5y windows and the Max return (spec section 5.1)."""

from datetime import date, timedelta

import pytest

from lib.funds import compute_max_return, compute_window_returns, fetch_plan, window_targets

END = date(2026, 9, 23)
PLAN = fetch_plan(END)
TARGETS = window_targets(END)


def series(annual_pct=12.0, first=None, last=END):
    """One NAV a day from `first` to `last`, compounding at exactly annual_pct a year and worth 100 on END."""
    first = first or END - timedelta(days=2000)
    return [(first + timedelta(days=i), 100 * (1 + annual_pct / 100) ** (((first + timedelta(days=i)) - END).days / 365.25)) for i in range((last - first).days + 1)]


def returns_for(history, latest=None, newest=END):
    """Cut the history the way AMFI's ranges would, then compute."""
    def within(key):
        start, end = PLAN[key]
        return [point for point in history if start <= point[0] <= end]

    return compute_window_returns(latest or history[-1], within("end"), {window: within(window) for window in ("1y", "3y", "5y")}, newest)


def test_the_fetch_plan_is_an_end_range_and_a_range_around_each_windows_start():
    plan = fetch_plan(date(2026, 9, 23))
    assert plan == {
        "end": (date(2026, 9, 16), date(2026, 9, 23)),
        "1y": (date(2025, 9, 19), date(2025, 9, 30)),
        "3y": (date(2023, 9, 19), date(2023, 9, 30)),
        "5y": (date(2021, 9, 19), date(2021, 9, 30)),
    }


def test_window_targets_are_the_same_date_for_every_fund():
    assert window_targets(date(2026, 9, 23)) == {"1y": date(2025, 9, 23), "3y": date(2023, 9, 23), "5y": date(2021, 9, 23)}


def test_steady_growth_gives_the_same_annualised_rate_in_every_window():
    result = returns_for(series(12.0))
    for window in ("1y", "3y", "5y"):
        assert result[window] == pytest.approx(12.0, abs=0.05), window


def test_a_fund_younger_than_a_window_has_no_return_for_it():
    result = returns_for(series(12.0, first=END - timedelta(days=800)))
    assert result["1y"] == pytest.approx(12.0, abs=0.05)
    assert result["3y"] is None and result["5y"] is None


@pytest.mark.parametrize("days_after_start, has_3y", [(5, True), (7, True), (9, False)])
def test_a_fund_launched_just_after_a_windows_start_still_gets_that_window(days_after_start, has_3y):
    history = series(12.0, first=TARGETS["3y"] + timedelta(days=days_after_start))
    result = returns_for(history)
    assert (result["3y"] is not None) is has_3y
    if has_3y:
        assert result["3y"] == pytest.approx(12.0, abs=0.05)  # annualised over the days it actually has


def test_a_holiday_on_the_target_day_falls_back_to_the_last_earlier_nav():
    history = [point for point in series(12.0) if point[0] != TARGETS["3y"]]
    assert returns_for(history)["3y"] == pytest.approx(12.0, abs=0.05)


def test_a_window_whose_range_holds_no_nav_for_the_fund_is_none_and_the_others_are_unaffected():
    start, end = PLAN["5y"]
    history = [point for point in series(12.0) if not start <= point[0] <= end]
    result = returns_for(history)
    assert result["5y"] is None
    assert result["1y"] == pytest.approx(12.0, abs=0.05) and result["3y"] == pytest.approx(12.0, abs=0.05)


def test_a_glitch_in_the_end_range_voids_every_window():
    history = series(12.0)
    history[-3:] = [(day, nav * 0.5) for day, nav in history[-3:]]  # a 50% fall between two prints inside the end range
    assert returns_for(history) == {"1y": None, "3y": None, "5y": None}


def test_a_glitch_in_one_windows_range_voids_only_that_window():
    jump_day = TARGETS["3y"] + timedelta(days=1)
    history = [(day, nav * 0.5 if day >= jump_day else nav) for day, nav in series(12.0)]
    result = returns_for(history)
    assert result["3y"] is None
    assert result["1y"] == pytest.approx(12.0, abs=0.05)  # its base and the latest NAV are both after the jump


def test_a_fall_below_the_glitch_threshold_is_kept():
    jump_day = TARGETS["3y"] + timedelta(days=1)
    history = [(day, nav * 0.7 if day >= jump_day else nav) for day, nav in series(12.0)]  # a 30% fall
    assert returns_for(history)["3y"] is not None


def test_a_fund_whose_newest_nav_is_a_few_days_old_is_annualised_by_the_days_it_covers():
    history = series(12.0, last=END - timedelta(days=3))
    assert returns_for(history)["1y"] == pytest.approx(12.0, abs=0.05)


def test_a_non_positive_latest_nav_gives_no_returns_and_never_raises():
    assert compute_window_returns((END, 0.0), [], {}, END) == {"1y": None, "3y": None, "5y": None}
    assert compute_window_returns((END, -1.0), [], {}, END) == {"1y": None, "3y": None, "5y": None}


def test_no_points_at_all_gives_no_returns():
    assert compute_window_returns((END, 100.0), [], {}, END) == {"1y": None, "3y": None, "5y": None}


def test_max_is_annualised_from_a_year_on():
    first = date(2016, 9, 23)
    value, annualised = compute_max_return((first, 100.0), (END, 200.0))
    years = (END - first).days / 365.25
    assert value == pytest.approx((2 ** (1 / years) - 1) * 100, abs=0.01)
    assert annualised is True


def test_max_of_a_fund_under_a_year_old_is_its_absolute_return():
    assert compute_max_return((END - timedelta(days=200), 100.0), (END, 110.0)) == (10.0, False)


@pytest.mark.parametrize("days, annualised", [(365, False), (366, True)])
def test_a_year_of_history_is_where_max_starts_to_be_annualised(days, annualised):
    assert compute_max_return((END - timedelta(days=days), 100.0), (END, 110.0))[1] is annualised


def test_max_is_unknown_without_a_first_nav_or_when_no_time_has_passed():
    assert compute_max_return(None, (END, 110.0)) == (None, None)
    assert compute_max_return((END, 100.0), (END, 100.0)) == (None, None)
    assert compute_max_return((END - timedelta(days=100), 0.0), (END, 100.0)) == (None, None)
