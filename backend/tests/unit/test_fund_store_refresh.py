"""FundStore boot, refresh, status and background triggers (spec section 5.3)."""

import asyncio
from datetime import date, timedelta

import pytest

from lib.finance_config import FUND_END_RANGE_DAYS
from lib.fund_store import FundStore, build_default_store
from lib.funds import fetch_plan

from .fund_store_fakes import FakeRepo, by_code, entry, make_store, steady
from .stored_fund_fixtures import END, NOW, stored


async def test_a_new_store_is_warming_and_empty():
    store, *_ = make_store([entry("1")])
    assert store.status == "warming"
    assert store.as_of is None and store.funds == [] and store.max_pending is False


async def test_the_first_fill_computes_1y_3y_and_5y_and_leaves_max_unknown():
    store, *_ = make_store([entry("1"), entry("2")], rates={"1": 10.0, "2": 14.0})
    await store.refresh()
    rows = by_code(store)
    assert store.status == "ready" and store.as_of == END
    for window in ("1y", "3y", "5y"):
        assert rows["1"].returns[window] == pytest.approx(10.0, abs=0.05), window
        assert rows["2"].returns[window] == pytest.approx(14.0, abs=0.05), window
    for row in rows.values():  # stamping every scheme "first seen today" would make every Max wrong, so none is stamped
        assert (row.returns["max"], row.max_is_annualised, row.first_nav, row.first_nav_date, row.first_nav_source) == (None, None, None, None, None)
    assert store.max_pending is True


async def test_every_category_is_kept_with_amfis_label_and_the_catalogs_identity():
    store, *_ = make_store([entry("1", "Alpha Bluechip", "Alpha Mutual Fund"), entry("2", "Alpha Liquid", segment=None, category="Liquid Fund")])
    await store.refresh()
    rows = by_code(store)
    assert (rows["1"].name, rows["1"].fund_house, rows["1"].segment, rows["1"].category) == ("Alpha Bluechip", "Alpha Mutual Fund", "large", "Large Cap Fund")
    assert (rows["2"].segment, rows["2"].category) == (None, "Liquid Fund")
    assert (rows["1"].nav, rows["1"].nav_date, rows["1"].computed_at) == (100.0, END, NOW)


async def test_a_refresh_downloads_the_catalog_once_and_the_four_planned_ranges_in_order():
    store, amfi, *_ = make_store([entry("1")])
    await store.refresh()
    assert amfi.catalog_calls == 1
    assert amfi.range_calls == list(fetch_plan(END).values())


async def test_a_refresh_saves_all_rows_in_one_bulk_write():
    store, _, repo, _ = make_store([entry("1"), entry("2")])
    await store.refresh()
    assert repo.upserts == [["1", "2"]]
    assert repo.deleted_keeping == [{"1", "2"}]


async def test_an_existing_rows_first_nav_is_kept_and_its_max_return_uses_it():
    store, _, repo, _ = make_store([entry("1")], seeded=[stored("1", first_nav=10.0, first_nav_date=date(2013, 1, 1))])
    await store.load()
    await store.refresh()
    row = by_code(store)["1"]
    assert (row.first_nav, row.first_nav_date, row.first_nav_source) == (10.0, date(2013, 1, 1), "checkpoint")
    years = (END - date(2013, 1, 1)).days / 365.25
    assert row.returns["max"] == pytest.approx((10 ** (1 / years) - 1) * 100, abs=0.01)
    assert row.max_is_annualised is True
    assert repo.rows["1"].first_nav == 10.0


async def test_a_scheme_new_to_an_existing_store_gets_its_first_nav_from_the_end_range():
    store, *_ = make_store([entry("1"), entry("2")], seeded=[stored("1")])
    await store.load()
    await store.refresh()
    earliest = END - timedelta(days=FUND_END_RANGE_DAYS)
    new = by_code(store)["2"]
    assert (new.first_nav_date, new.first_nav_source) == (earliest, "first_seen")
    assert new.first_nav == pytest.approx(dict(steady())[earliest])
    assert new.max_is_annualised is False  # a week old: an absolute return


async def test_a_new_scheme_with_no_nav_in_the_end_range_falls_back_to_its_catalog_nav():
    store, amfi, *_ = make_store([entry("1"), entry("2")], seeded=[stored("1")])
    del amfi.histories["2"]
    await store.load()
    await store.refresh()
    new = by_code(store)["2"]
    assert (new.first_nav, new.first_nav_date, new.first_nav_source) == (100.0, END, "first_seen")
    assert new.returns["max"] is None  # no time has passed since its first NAV


async def test_a_failed_download_keeps_every_previous_row_and_marks_the_store_stale():
    store, amfi, repo, _ = make_store([entry("1")], seeded=[stored("1")])
    await store.load()
    before = by_code(store)
    amfi.range_fails_after = 2  # the third of the four downloads raises
    await store.refresh()
    assert by_code(store) == before
    assert store.status == "stale"
    assert repo.upserts == [] and repo.deleted_keeping == []


async def test_a_catalog_failure_with_no_rows_is_unavailable():
    store, amfi, *_ = make_store([entry("1")])
    amfi.catalog_fails = True
    await store.refresh()
    assert store.status == "unavailable"


async def test_an_empty_catalog_is_a_failure_and_never_deletes_anything():
    store, _, repo, _ = make_store([], seeded=[stored("1")])
    await store.load()
    await store.refresh()
    assert store.status == "stale"
    assert list(by_code(store)) == ["1"] and list(repo.rows) == ["1"]
    assert repo.deleted_keeping == []


async def test_an_empty_catalog_with_no_rows_is_unavailable():
    store, *_ = make_store([])
    await store.refresh()
    assert store.status == "unavailable"


async def test_a_delisted_scheme_is_removed_from_memory_and_from_the_repo():
    store, _, repo, _ = make_store([entry("1")], seeded=[stored("1"), stored("2")])
    await store.load()
    await store.refresh()
    assert list(by_code(store)) == ["1"] and list(repo.rows) == ["1"]
    assert repo.deleted_keeping == [{"1"}]


async def test_rows_older_than_a_day_are_stale_and_ensure_fresh_refreshes_them():
    store, amfi, _, clock = make_store([entry("1")])
    await store.refresh()
    clock.advance(hours=25)
    assert store.status == "stale"
    store.ensure_fresh()
    await store._refresh_task
    assert amfi.catalog_calls == 2
    assert store.status == "ready"


async def test_ensure_fresh_leaves_rows_under_a_day_old_alone():
    store, amfi, _, clock = make_store([entry("1")])
    await store.refresh()
    clock.advance(hours=23)
    store.ensure_fresh()
    await asyncio.sleep(0.01)
    assert amfi.catalog_calls == 1


async def test_a_failed_refresh_is_not_retried_for_five_minutes():
    store, amfi, _, clock = make_store([entry("1")])
    amfi.catalog_fails = True
    await store.refresh()
    clock.advance(minutes=4)
    store.ensure_fresh()
    await asyncio.sleep(0.01)
    assert amfi.catalog_calls == 1
    clock.advance(minutes=2)
    store.ensure_fresh()
    await asyncio.sleep(0.01)
    assert amfi.catalog_calls == 2


async def test_concurrent_refreshes_share_one_download_set():
    store, amfi, *_ = make_store([entry("1"), entry("2")])
    await asyncio.gather(store.refresh(), store.refresh(), store.refresh())
    assert amfi.catalog_calls == 1 and len(amfi.range_calls) == 4


async def test_repeated_ensure_fresh_calls_start_one_refresh():
    store, amfi, *_ = make_store([entry("1")])
    store.ensure_fresh()
    first = store._refresh_task
    store.ensure_fresh()
    store.ensure_fresh()
    assert store._refresh_task is first  # a second task would leave the first one running where aclose cannot cancel it
    await asyncio.sleep(0.05)
    assert amfi.catalog_calls == 1
    assert store.status == "ready"


async def test_boot_serves_the_stored_rows_at_once_and_downloads_nothing_while_they_are_fresh():
    store, amfi, *_ = make_store([entry("1")], seeded=[stored("1")])
    store.start()
    await store._boot_task
    assert store.status == "ready" and list(by_code(store)) == ["1"]
    assert amfi.catalog_calls == 0 and amfi.range_calls == []


async def test_boot_serves_rows_over_a_day_old_as_stale_while_it_refreshes_them():
    store, amfi, *_ = make_store([entry("1")], seeded=[stored("1", computed_at=NOW - timedelta(hours=30))])
    store.start()
    await store._boot_task
    assert store.status == "stale" and list(by_code(store)) == ["1"]
    await store._refresh_task
    assert store.status == "ready" and amfi.catalog_calls == 1


async def test_boot_with_nothing_stored_runs_the_first_fill():
    store, amfi, *_ = make_store([entry("1")])
    store.start()
    await store._boot_task
    await store._refresh_task
    assert store.status == "ready" and amfi.catalog_calls == 1


async def test_a_request_while_the_stored_rows_are_still_loading_does_not_start_a_refresh():
    store, amfi, repo, _ = make_store([entry("1")], seeded=[stored("1")])
    release = asyncio.Event()
    load_all = repo.load_all

    async def slow_load_all():
        await release.wait()
        return await load_all()

    repo.load_all = slow_load_all
    store.start()
    await asyncio.sleep(0)
    store.ensure_fresh()
    assert store._refresh_task is None
    release.set()
    await store._boot_task
    assert amfi.catalog_calls == 0


async def test_aclose_cancels_a_running_refresh_and_closes_the_client():
    store, *_ = make_store([entry("1")])
    closed = []

    async def close():
        closed.append(True)

    async def hang():
        await asyncio.Event().wait()

    store._close = close
    store._fetch_catalog = hang
    store.ensure_fresh()
    await asyncio.sleep(0)
    await store.aclose()
    assert closed == [True] and store._refresh_task.done()


async def test_the_default_store_starts_warming_and_closes_its_http_client():
    store = build_default_store(FakeRepo())
    assert isinstance(store, FundStore)
    assert store.status == "warming"
    await store.aclose()
