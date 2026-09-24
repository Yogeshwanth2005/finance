"""The first-NAV pass: month-start snapshots from January 2013, resumable, saved per snapshot (spec section 5.3)."""

import asyncio
from datetime import date

import pytest

from lib import fund_store

from .fund_store_fakes import by_code, entry, make_store, snapshot
from .stored_fund_fixtures import stored, unresolved

JAN_1, FEB_1, MAR_1, APR_1, MAY_1 = (date(2013, month, 1) for month in range(1, 6))  # weekdays: Tue, Fri, Fri, Mon, Wed
NEWEST = date(2013, 5, 10)


@pytest.fixture(autouse=True)
def any_weekday_with_a_scheme_is_a_snapshot(monkeypatch):
    monkeypatch.setattr(fund_store, "FUND_CHECKPOINT_MIN_ROWS", 1)


async def pass_store(*funds, days=None):
    store, amfi, repo, clock = make_store(seeded=funds)
    amfi.days = days if days is not None else {}
    await store.load()
    return store, amfi, repo, clock


def fund(code, **overrides):
    return unresolved(code, nav=20.0, nav_date=NEWEST, **overrides)


def calls(amfi):
    return [start for start, end in amfi.range_calls]


async def test_each_fund_gets_its_first_nav_from_the_first_snapshot_it_is_on_and_the_pass_stops_when_none_is_left():
    store, amfi, repo, _ = await pass_store(
        fund("A"), fund("B"),
        days={JAN_1: snapshot(JAN_1, "A", nav=10.0), FEB_1: snapshot(FEB_1, "A", nav=11.0), MAR_1: snapshot(MAR_1, "A", "B", nav=12.0)},
    )
    await store.resolve_first_navs()
    rows = by_code(store)
    assert (rows["A"].first_nav, rows["A"].first_nav_date, rows["A"].first_nav_source) == (10.0, JAN_1, "checkpoint")
    assert (rows["B"].first_nav, rows["B"].first_nav_date, rows["B"].first_nav_source) == (12.0, MAR_1, "checkpoint")
    assert calls(amfi) == [JAN_1, FEB_1, MAR_1]  # oldest to newest, and April and May were never fetched
    assert repo.first_nav_saves == [["A"], ["B"]]  # saved after each snapshot that resolved something
    assert store.max_pending is False


async def test_a_resolved_fund_gets_its_max_return_from_its_first_nav():
    store, *_ = await pass_store(fund("A"), days={JAN_1: snapshot(JAN_1, "A", nav=10.0)})
    await store.resolve_first_navs()
    row = by_code(store)["A"]
    assert (row.returns["max"], row.max_is_annualised) == (100.0, False)  # 10 to 20 in four months: absolute


async def test_a_saturday_and_a_sunday_are_never_downloaded_and_the_next_weekday_is_used():
    june_3 = date(2013, 6, 3)  # June 1 is a Saturday and June 2 a Sunday
    anchor = stored("R", nav_date=date(2013, 6, 20), first_nav_date=date(2013, 5, 15))  # resume from May
    store, amfi, _, _ = await pass_store(
        anchor, unresolved("A", nav_date=date(2013, 6, 20)),
        days={date(2013, 6, 1): snapshot(date(2013, 6, 1), "A"), date(2013, 6, 2): snapshot(date(2013, 6, 2), "A"), june_3: snapshot(june_3, "A")},
    )
    await store.resolve_first_navs()
    assert by_code(store)["A"].first_nav_date == june_3
    assert date(2013, 6, 1) not in calls(amfi) and date(2013, 6, 2) not in calls(amfi)


async def test_a_weekday_with_too_few_schemes_is_a_holiday_and_the_next_day_is_used(monkeypatch):
    monkeypatch.setattr(fund_store, "FUND_CHECKPOINT_MIN_ROWS", 2)
    jan_2 = date(2013, 1, 2)
    store, amfi, *_ = await pass_store(
        unresolved("A", nav_date=date(2013, 1, 20)), unresolved("B", nav_date=date(2013, 1, 20)),
        days={JAN_1: snapshot(JAN_1, "A"), jan_2: snapshot(jan_2, "A", "B")},
    )
    await store.resolve_first_navs()
    assert calls(amfi) == [JAN_1, jan_2]
    assert by_code(store)["A"].first_nav_date == jan_2 and by_code(store)["B"].first_nav_date == jan_2


async def test_a_snapshot_looks_at_no_day_after_the_newest_nav_date():
    store, amfi, *_ = await pass_store(unresolved("A", nav_date=date(2013, 1, 2)), days={})
    await store.resolve_first_navs()
    assert calls(amfi) == [JAN_1, date(2013, 1, 2)]  # the 3rd and later do not exist yet


async def test_the_pass_resumes_from_the_month_of_the_latest_saved_snapshot():
    anchor = stored("R", nav_date=NEWEST, first_nav_date=MAR_1, first_nav_source="checkpoint")
    store, amfi, *_ = await pass_store(anchor, fund("A"), days={APR_1: snapshot(APR_1, "A")})
    await store.resolve_first_navs()
    assert min(calls(amfi)) >= MAR_1
    assert by_code(store)["A"].first_nav_date == APR_1


async def test_a_first_seen_row_does_not_move_the_resume_month():
    seen = stored("S", nav_date=NEWEST, first_nav_date=date(2013, 4, 20), first_nav_source="first_seen")
    store, amfi, *_ = await pass_store(seen, fund("A"))
    await store.resolve_first_navs()
    assert calls(amfi)[0] == JAN_1


async def test_a_fund_on_no_snapshot_falls_back_to_its_own_newest_nav_after_the_last_one():
    store, _, repo, _ = await pass_store(fund("A"), days={JAN_1: snapshot(JAN_1, "Z")})  # snapshots that do not hold A
    await store.resolve_first_navs()
    row = by_code(store)["A"]
    assert (row.first_nav, row.first_nav_date, row.first_nav_source) == (20.0, NEWEST, "first_seen")
    assert row.returns["max"] is None
    assert repo.first_nav_saves[-1] == ["A"]
    assert store.max_pending is False


async def test_three_snapshots_failing_in_a_row_stop_the_pass_without_the_fallback():
    store, amfi, repo, _ = await pass_store(fund("A"))
    amfi.failing_days = {JAN_1, FEB_1, MAR_1}
    await store.resolve_first_navs()
    assert calls(amfi) == [JAN_1, FEB_1, MAR_1]
    assert by_code(store)["A"].first_nav is None and store.max_pending is True
    assert repo.first_nav_saves == []


async def test_one_failed_snapshot_is_skipped_and_the_count_starts_again():
    store, amfi, *_ = await pass_store(fund("A"), days={FEB_1: snapshot(FEB_1, "A")})
    amfi.failing_days = {JAN_1}
    await store.resolve_first_navs()
    assert by_code(store)["A"].first_nav_date == FEB_1


async def test_a_pass_that_stopped_is_not_retried_for_five_minutes():
    store, amfi, _, clock = await pass_store(fund("A"))
    amfi.failing_days = {JAN_1, FEB_1, MAR_1, APR_1, MAY_1}
    store.ensure_fresh()
    await store._first_nav_task
    assert len(amfi.range_calls) == 3
    clock.advance(minutes=4)
    store.ensure_fresh()
    await asyncio.sleep(0.01)
    assert len(amfi.range_calls) == 3
    clock.advance(minutes=2)
    store.ensure_fresh()
    await store._first_nav_task
    assert len(amfi.range_calls) == 6


async def test_two_passes_at_once_share_one_run():
    store, amfi, *_ = await pass_store(fund("A"), days={JAN_1: snapshot(JAN_1, "A")})
    await asyncio.gather(store.resolve_first_navs(), store.resolve_first_navs())
    assert calls(amfi) == [JAN_1]


async def test_repeated_ensure_fresh_calls_while_the_pass_runs_start_no_second_pass():
    store, _, *_ = await pass_store(fund("A"), days={JAN_1: snapshot(JAN_1, "A")})
    release = asyncio.Event()
    fetch = store._fetch_range

    async def held(start, end):
        await release.wait()
        return await fetch(start, end)

    store._fetch_range = held
    store.ensure_fresh()
    running = store._first_nav_task
    store.ensure_fresh()  # back to back: the first task has not started, so the retry gate cannot be what stops these
    store.ensure_fresh()
    assert store._first_nav_task is running
    release.set()
    await running


async def test_nothing_is_downloaded_when_every_first_nav_is_known():
    store, amfi, *_ = await pass_store(stored("1"))
    await store.resolve_first_navs()
    assert amfi.range_calls == []


async def test_a_refresh_running_beside_the_pass_keeps_the_first_navs_the_pass_finds():
    store, amfi, repo, _ = make_store([entry("A")], seeded=[unresolved("A")])
    amfi.days = {JAN_1: snapshot(JAN_1, "A", nav=10.0)}
    amfi.gate = asyncio.Event()  # holds the refresh's multi-day downloads
    await store.load()
    refreshing = asyncio.create_task(store.refresh())
    await asyncio.sleep(0)
    await store.resolve_first_navs()
    amfi.gate.set()
    await refreshing
    row = by_code(store)["A"]
    assert (row.first_nav, row.first_nav_date, row.first_nav_source) == (10.0, JAN_1, "checkpoint")
    assert row.returns["max"] is not None
    assert repo.rows["A"].first_nav == 10.0


async def test_a_refresh_starts_the_pass_when_it_leaves_funds_without_a_first_nav():
    store, amfi, *_ = make_store([entry("A")])
    amfi.days = {JAN_1: snapshot(JAN_1, "A", nav=10.0)}
    store.ensure_fresh()
    await store._refresh_task
    await store._first_nav_task
    row = by_code(store)["A"]
    assert (row.first_nav, row.first_nav_date) == (10.0, JAN_1)
    assert store.max_pending is False
