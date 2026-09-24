"""FundStore: warm-up, refresh, expiry, single-flight and the top / search queries (spec section 5.3)."""

import asyncio
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from lib.funds import CatalogEntry, FundStore

END = date(2026, 9, 23)


def entry(code, name=None, house="Alpha Mutual Fund", segment="large"):
    return CatalogEntry(code, name or f"Fund {code}", house, segment, 10.0, END)


def growth(annual_pct=12.0, years=4):
    days = round(years * 365.25)
    return [(END - timedelta(days=offset), 100 * (1 + annual_pct / 100) ** (-offset / 365.25)) for offset in range(days, -1, -1)]


class Clock:
    def __init__(self):
        self.now = datetime(2026, 9, 24, 9, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, **kwargs):
        self.now += timedelta(**kwargs)


def make_store(entries, rates=None):
    """A store wired to fakes; toggle fakes.catalog_fails, or add codes to fakes.failing or fakes.glitchy, to break things."""
    fakes = SimpleNamespace(entries=entries, rates=rates or {}, catalog_fails=False, failing=set(), glitchy=set(), catalog_calls=0, history_calls=[], closed=False)
    clock = Clock()

    async def fetch_catalog():
        fakes.catalog_calls += 1
        await asyncio.sleep(0)
        if fakes.catalog_fails:
            raise RuntimeError("amfi down")
        return fakes.entries

    async def fetch_history(code):
        fakes.history_calls.append(code)
        await asyncio.sleep(0)
        if code in fakes.failing:
            raise RuntimeError("mfapi down")
        history = growth(fakes.rates.get(code, 12.0))
        if code in fakes.glitchy:
            history[len(history) // 2:] = [(d, nav * 0.5) for d, nav in history[len(history) // 2:]]
        return history

    async def close():
        fakes.closed = True

    return FundStore(fetch_catalog, fetch_history, close=close, now=clock), fakes, clock


def names(rows):
    return [row.name for row in rows]


async def test_a_new_store_is_warming_and_empty():
    store, _, _ = make_store([entry("1")])
    assert store.status == "warming"
    assert store.as_of is None
    assert store.top("3y") == {"nifty": [], "large": [], "mid": [], "small": []}


async def test_refresh_loads_funds_ranked_by_the_window_and_reports_ready():
    store, _, _ = make_store([entry("1", "A"), entry("2", "B"), entry("3", "C")], rates={"1": 10.0, "2": 14.0, "3": 12.0})
    await store.refresh()
    assert store.status == "ready"
    assert store.as_of == END
    assert store.failed_count == 0
    assert names(store.top("3y")["large"]) == ["B", "C", "A"]


async def test_funds_that_fail_or_glitch_are_left_out_and_counted():
    store, fakes, _ = make_store([entry("1"), entry("2"), entry("3")])
    fakes.failing.add("2")
    fakes.glitchy.add("3")
    await store.refresh()
    assert names(store.top("3y")["large"]) == ["Fund 1"]
    assert store.failed_count == 2
    assert store.status == "ready"


async def test_top_is_capped_at_ten_per_segment_but_search_is_not():
    store, _, _ = make_store([entry(str(i), house="Alpha Mutual Fund") for i in range(12)] + [entry("m1", segment="mid")])
    await store.refresh()
    assert len(store.top("3y")["large"]) == 10
    assert len(store.top("3y")["mid"]) == 1
    _, groups = store.search("alpha", "3y")
    assert len(groups["large"]) == 12


async def test_search_matches_fund_house_names_only_and_groups_by_segment():
    store, _, _ = make_store(
        [entry("1", "Alpha Large", "Alpha Mutual Fund"), entry("2", "Alpha Mid", "Alpha Mutual Fund", "mid"), entry("3", "Beta Large", "Beta Mutual Fund")]
    )
    await store.refresh()
    houses, groups = store.search("alpha", "3y")
    assert houses == ["Alpha Mutual Fund"]
    assert names(groups["large"]) == ["Alpha Large"] and names(groups["mid"]) == ["Alpha Mid"]
    assert groups["small"] == [] and groups["nifty"] == []
    assert store.search("Large", "3y")[0] == []  # a scheme name is not a fund house


async def test_search_is_case_insensitive_and_ignores_surrounding_spaces():
    store, _, _ = make_store([entry("1", house="HDFC Mutual Fund")])
    await store.refresh()
    assert store.search("  hdfc ", "3y")[0] == ["HDFC Mutual Fund"]
    assert store.search("MUTUAL", "3y")[0] == ["HDFC Mutual Fund"]


@pytest.mark.parametrize("query", ["", "   ", "(", ".*", "%", "[a-z]", "hdfc%", "\\"])
async def test_blank_or_pattern_like_queries_match_nothing_and_never_raise(query):
    store, _, _ = make_store([entry("1", house="HDFC Mutual Fund")])
    await store.refresh()
    houses, groups = store.search(query, "3y")
    assert houses == [] and all(rows == [] for rows in groups.values())


async def test_a_catalog_failure_with_no_data_is_unavailable():
    store, fakes, _ = make_store([entry("1")])
    fakes.catalog_fails = True
    await store.refresh()
    assert store.status == "unavailable"


async def test_an_empty_catalog_counts_as_a_failure():
    store, _, _ = make_store([])
    await store.refresh()
    assert store.status == "unavailable"


async def test_every_history_fetch_failing_counts_as_a_failure():
    store, fakes, _ = make_store([entry("1"), entry("2")])
    fakes.failing.update({"1", "2"})
    await store.refresh()
    assert store.status == "unavailable"
    assert store.as_of is None


async def test_a_failed_refresh_keeps_the_last_good_data_and_marks_it_stale():
    store, fakes, _ = make_store([entry("1", "A")])
    await store.refresh()
    fakes.catalog_fails = True
    await store.refresh()
    assert store.status == "stale"
    assert names(store.top("3y")["large"]) == ["A"]
    assert store.as_of == END


async def test_data_older_than_the_ttl_is_stale_and_ensure_fresh_reloads_it():
    store, fakes, clock = make_store([entry("1")])
    await store.refresh()
    clock.advance(hours=25)
    assert store.status == "stale"
    store.ensure_fresh()
    await store._task
    assert fakes.catalog_calls == 2
    assert store.status == "ready"


async def test_ensure_fresh_leaves_fresh_data_alone():
    store, fakes, clock = make_store([entry("1")])
    await store.refresh()
    clock.advance(hours=23)
    store.ensure_fresh()
    await asyncio.sleep(0.01)
    assert fakes.catalog_calls == 1


async def test_a_failed_refresh_is_not_retried_for_five_minutes():
    store, fakes, clock = make_store([entry("1")])
    fakes.catalog_fails = True
    await store.refresh()
    clock.advance(minutes=4)
    store.ensure_fresh()
    await asyncio.sleep(0.01)
    assert fakes.catalog_calls == 1
    clock.advance(minutes=2)
    store.ensure_fresh()
    await asyncio.sleep(0.01)
    assert fakes.catalog_calls == 2


async def test_concurrent_refreshes_share_one_fetch():
    store, fakes, _ = make_store([entry("1"), entry("2"), entry("3")])
    await asyncio.gather(store.refresh(), store.refresh(), store.refresh())
    assert fakes.catalog_calls == 1
    assert sorted(fakes.history_calls) == ["1", "2", "3"]


async def test_repeated_ensure_fresh_calls_start_one_refresh():
    store, fakes, _ = make_store([entry("1")])
    for _ in range(3):
        store.ensure_fresh()
    await asyncio.sleep(0.05)
    assert fakes.catalog_calls == 1
    assert store.status == "ready"


async def test_aclose_cancels_a_running_refresh_and_closes_the_client():
    store, fakes, _ = make_store([entry("1")])

    async def hang():
        await asyncio.Event().wait()

    store._fetch_catalog = hang
    store.start()
    await asyncio.sleep(0)
    await store.aclose()
    assert fakes.closed is True
    assert store._task.done()
