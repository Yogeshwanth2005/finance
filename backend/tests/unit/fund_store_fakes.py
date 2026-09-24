"""Fakes for the FundStore tests: a dict-backed repo, a clock, and an AMFI stand-in serving a catalog and dated ranges."""

import asyncio
from dataclasses import replace
from datetime import date, datetime, timedelta

from lib.fund_store import FundStore
from lib.funds import CatalogEntry

from .stored_fund_fixtures import END, NOW


def steady(annual_pct=12.0, years=6, end=END):
    """One NAV a day compounding at exactly annual_pct a year and worth 100 on `end`."""
    days = round(years * 365.25)
    return [(end - timedelta(days=offset), 100 * (1 + annual_pct / 100) ** (-offset / 365.25)) for offset in range(days, -1, -1)]


def entry(code, name=None, house="Alpha Mutual Fund", segment="large", category="Large Cap Fund"):
    return CatalogEntry(code, name or f"Fund {code}", house, segment, 100.0, END, category)


class Clock:
    def __init__(self):
        self.now: datetime = NOW

    def __call__(self):
        return self.now

    def advance(self, **kwargs):
        self.now += timedelta(**kwargs)


class FakeRepo:
    """Stands in for MongoFundRepo and keeps its rules: an upsert never overwrites a stored row's first NAV fields."""

    def __init__(self, funds=()):
        self.rows = {fund.scheme_code: fund for fund in funds}
        self.upserts = []  # scheme codes of each upsert_many call
        self.first_nav_saves = []  # scheme codes of each set_first_nav call
        self.deleted_keeping = []  # the keep set of each delete_missing call

    async def load_all(self):
        return list(self.rows.values())

    async def upsert_many(self, funds):
        self.upserts.append([fund.scheme_code for fund in funds])
        for fund in funds:
            stored = self.rows.get(fund.scheme_code)
            if stored is not None:
                fund = replace(fund, first_nav=stored.first_nav, first_nav_date=stored.first_nav_date, first_nav_source=stored.first_nav_source)
            self.rows[fund.scheme_code] = fund

    async def set_first_nav(self, funds):
        self.first_nav_saves.append([fund.scheme_code for fund in funds])
        for fund in funds:
            stored = self.rows.get(fund.scheme_code)
            if stored is None or stored.first_nav is None:
                self.rows[fund.scheme_code] = fund

    async def delete_missing(self, keep_codes):
        self.deleted_keeping.append(set(keep_codes))
        self.rows = {code: fund for code, fund in self.rows.items() if code in keep_codes}


class FakeAmfi:
    """A catalog plus dated ranges cut from full NAV histories. Set the switches to break it; set `days` to script single-day reports."""

    def __init__(self, entries, histories):
        self.entries = entries
        self.histories = histories
        self.catalog_fails = False
        self.range_fails_after = None  # the number of range downloads that succeed before every later one raises
        self.failing_days = set()  # single-day downloads that raise
        self.days = None  # {date: report}: when set, a single-day download is answered from it
        self.gate = None  # an asyncio.Event: multi-day downloads wait for it
        self.catalog_calls = 0
        self.range_calls = []

    async def fetch_catalog(self):
        self.catalog_calls += 1
        await asyncio.sleep(0)
        if self.catalog_fails:
            raise RuntimeError("amfi is down")
        return self.entries

    async def fetch_range(self, start, end):
        self.range_calls.append((start, end))
        await asyncio.sleep(0)
        if self.gate is not None and start != end:
            await self.gate.wait()
        if start == end and start in self.failing_days:
            raise RuntimeError("amfi dropped the download")
        if self.range_fails_after is not None and len(self.range_calls) > self.range_fails_after:
            raise RuntimeError("amfi dropped the download")
        if start == end and self.days is not None:
            return self.days.get(start, {})
        cut = {code: [point for point in history if start <= point[0] <= end] for code, history in self.histories.items()}
        return {code: points for code, points in cut.items() if points}


def make_store(entries=(), *, rates=None, seeded=()):
    """A store wired to fakes. Returns (store, amfi, repo, clock); `rates` maps a scheme code to its annual growth percent (default 12)."""
    histories = {item.scheme_code: steady((rates or {}).get(item.scheme_code, 12.0)) for item in entries}
    amfi = FakeAmfi(list(entries), histories)
    repo = FakeRepo(seeded)
    clock = Clock()
    store = FundStore(repo, amfi.fetch_catalog, amfi.fetch_range, now=clock)
    return store, amfi, repo, clock


def by_code(store):
    return {fund.scheme_code: fund for fund in store.funds}


def snapshot(day, *codes, nav=10.0):
    """A single-day report holding the given schemes."""
    return {code: [(day, nav)] for code in codes}
