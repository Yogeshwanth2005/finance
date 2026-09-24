"""The fund store (spec section 5.3): stored rows served from memory, refreshed from AMFI's dated NAV reports at most once a day.

Boot loads the rows MongoDB holds, so a server that just woke up answers at once. A refresh downloads five AMFI files and
replaces every row atomically. A separate background pass works out each fund's first NAV, which the Max window needs.
The repository and both fetchers are injected, so tests need neither a network nor MongoDB.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

import httpx

from lib.finance_config import FUND_CACHE_TTL_HOURS, FUND_REFRESH_RETRY_MINUTES, FUND_TOP_N
from lib.fund_repo import StoredFund
from lib.funds import (
    SEGMENTS, WINDOW_YEARS, CatalogEntry, History, compute_max_return, compute_window_returns, fetch_amfi_catalog, fetch_nav_range,
    fetch_plan,
)

logger = logging.getLogger(__name__)

CatalogFetcher = Callable[[], Awaitable[list[CatalogEntry]]]
RangeFetcher = Callable[[date, date], Awaitable[dict[str, History]]]

SEGMENT_TITLES = {"nifty": "Nifty 50 index", "large": "Large cap", "mid": "Mid cap", "small": "Small cap"}


class FundRepo(Protocol):
    async def load_all(self) -> list[StoredFund]: ...
    async def upsert_many(self, funds: list[StoredFund]) -> None: ...
    async def set_first_nav(self, funds: list[StoredFund]) -> None: ...
    async def delete_missing(self, keep_codes: set[str]) -> None: ...


@dataclass(frozen=True)
class FundSection:
    """One block of a search result: a segment ("large") or an AMFI category ("cat-flexi-cap-fund")."""

    key: str
    title: str
    funds: list[StoredFund]


def _rank_key(window: str):
    if window == "max":  # a fund a year or older is ranked above a newer one, whose absolute return is not comparable
        return lambda fund: (not fund.max_is_annualised, -fund.returns["max"], fund.name)
    return lambda fund: (-fund.returns[window], fund.name)


def rank_funds(funds: list[StoredFund], window: str) -> list[StoredFund]:
    """The funds that have a value for the window, best first, ties by name."""
    return sorted((fund for fund in funds if fund.returns.get(window) is not None), key=_rank_key(window))


def _ranked_then_rest(funds: list[StoredFund], window: str) -> list[StoredFund]:
    """A search result never hides a fund: ranked ones first, then the ones without a value for the window by name."""
    rest = sorted((fund for fund in funds if fund.returns.get(window) is None), key=lambda fund: fund.name)
    return rank_funds(funds, window) + rest


def _category_key(category: str) -> str:
    return "cat-" + (re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-") or "other")


def _running(task: asyncio.Task | None) -> bool:
    return task is not None and not task.done()


class FundStore:
    def __init__(
        self,
        repo: FundRepo,
        fetch_catalog: CatalogFetcher,
        fetch_range: RangeFetcher,
        *,
        close: Callable[[], Awaitable[None]] | None = None,
        now: Callable[[], datetime] | None = None,
    ):
        self._repo = repo
        self._fetch_catalog = fetch_catalog
        self._fetch_range = fetch_range
        self._close = close
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._rows: dict[str, StoredFund] = {}
        self._as_of: date | None = None
        self._newest_computed_at: datetime | None = None
        self._booting = False
        self._boot_task: asyncio.Task | None = None
        self._refresh_lock = asyncio.Lock()
        self._refresh_task: asyncio.Task | None = None
        self._last_refresh_attempt: datetime | None = None
        self._last_refresh_failed = False

    # --- state ------------------------------------------------------------------------------------------------------

    @property
    def funds(self) -> list[StoredFund]:
        return list(self._rows.values())

    @property
    def as_of(self) -> date | None:
        """The newest NAV date across the stored rows."""
        return self._as_of

    @property
    def max_pending(self) -> bool:
        """True while some fund's first NAV is not known yet, so its Max return is still missing."""
        return any(fund.first_nav is None for fund in self._rows.values())

    @property
    def status(self) -> str:
        if not self._rows:
            return "unavailable" if self._last_refresh_failed else "warming"
        return "stale" if self._last_refresh_failed or self._expired(self._now()) else "ready"

    def _expired(self, now: datetime) -> bool:
        return self._newest_computed_at is None or now - self._newest_computed_at > timedelta(hours=FUND_CACHE_TTL_HOURS)

    def _set_rows(self, rows: dict[str, StoredFund]) -> None:
        self._rows = rows
        self._as_of = max((fund.nav_date for fund in rows.values()), default=None)
        self._newest_computed_at = max((fund.computed_at for fund in rows.values()), default=None)

    # --- boot and triggers --------------------------------------------------------------------------------------------

    async def load(self) -> None:
        """Read the stored rows into memory."""
        stored = await self._repo.load_all()
        if stored:
            self._set_rows({fund.scheme_code: fund for fund in stored})

    def start(self) -> None:
        """Begin in the background: load the stored rows so requests are answered at once, then start whatever job is due. Needs a running loop."""
        self._booting = True
        self._boot_task = asyncio.get_running_loop().create_task(self._boot())

    async def _boot(self) -> None:
        try:
            await self.load()
        except Exception:
            logger.exception("stored fund rows could not be loaded")
        finally:
            self._booting = False
        self.ensure_fresh()

    def ensure_fresh(self) -> None:
        """Called on every fund request and once after boot: start a background refresh if one is due. Never blocks."""
        if self._booting:  # deciding from an empty store while the stored rows are still loading would refresh needlessly
            return
        if self._refresh_due(self._now()):
            self._refresh_task = asyncio.get_running_loop().create_task(self.refresh())

    def _refresh_due(self, now: datetime) -> bool:
        if self._refresh_lock.locked() or _running(self._refresh_task):
            return False
        if self._last_refresh_attempt is not None and now - self._last_refresh_attempt < timedelta(minutes=FUND_REFRESH_RETRY_MINUTES):
            return False
        return not self._rows or self._expired(now)

    async def aclose(self) -> None:
        for task in (self._boot_task, self._refresh_task):
            if _running(task):
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        if self._close is not None:
            await self._close()

    # --- refresh ----------------------------------------------------------------------------------------------------

    async def refresh(self) -> None:
        """Rebuild every row from AMFI. Single-flight: a call made while one runs returns at once. Atomic: any failure keeps the old rows."""
        if self._refresh_lock.locked():
            return
        async with self._refresh_lock:
            self._last_refresh_attempt = self._now()
            try:
                rows = await self._build_rows()
            except Exception:
                logger.exception("fund refresh failed")
                self._last_refresh_failed = True
                return
            self._set_rows(rows)
            self._last_refresh_failed = False
            await self._repo.upsert_many(list(rows.values()))
            await self._repo.delete_missing(set(rows))

    async def _build_rows(self) -> dict[str, StoredFund]:
        catalog = await self._fetch_catalog()
        if not catalog:
            raise RuntimeError("AMFI's catalog came back empty")
        newest = max(entry.nav_date for entry in catalog)
        downloads: dict[str, dict[str, History]] = {}
        for key, (start, end) in fetch_plan(newest).items():
            downloads[key] = await self._fetch_range(start, end)
        return self._compute_rows(catalog, newest, downloads)

    def _compute_rows(self, catalog: list[CatalogEntry], newest: date, downloads: dict[str, dict[str, History]]) -> dict[str, StoredFund]:
        """Synchronous on purpose: it reads the rows as they are now, so a first NAV the background pass just found is carried over."""
        now = self._now()
        had_rows = bool(self._rows)
        end_points = downloads["end"]
        rows: dict[str, StoredFund] = {}
        for entry in catalog:
            code = entry.scheme_code
            latest = (entry.nav_date, entry.nav)
            windows = compute_window_returns(
                latest, end_points.get(code, []), {window: downloads[window].get(code, []) for window in WINDOW_YEARS}, newest
            )
            previous = self._rows.get(code)
            if previous is not None:
                first_nav, first_date, source = previous.first_nav, previous.first_nav_date, previous.first_nav_source
            elif had_rows:  # a scheme launched since the last refresh: the earliest NAV we can see is its first
                earliest = end_points[code][0] if end_points.get(code) else (entry.nav_date, entry.nav)
                first_date, first_nav, source = earliest[0], earliest[1], "first_seen"
            else:  # the very first fill: stamping every scheme "first seen today" would make every Max return wrong
                first_nav, first_date, source = None, None, None
            max_return, annualised = compute_max_return((first_date, first_nav) if first_nav is not None else None, latest)
            rows[code] = StoredFund(
                scheme_code=code, name=entry.name, fund_house=entry.fund_house, category=entry.category, segment=entry.segment,
                nav=entry.nav, nav_date=entry.nav_date, returns={**windows, "max": max_return}, max_is_annualised=annualised,
                computed_at=now, first_nav=first_nav, first_nav_date=first_date, first_nav_source=source,
            )
        return rows

    # --- queries ----------------------------------------------------------------------------------------------------

    def top(self, window: str) -> dict[str, list[StoredFund]]:
        """The best FUND_TOP_N funds of each equity segment for the window; a fund without a value for it is left out."""
        return {segment: rank_funds([fund for fund in self._rows.values() if fund.segment == segment], window)[:FUND_TOP_N] for segment in SEGMENTS}

    def search(self, query: str, window: str) -> tuple[list[str], list[FundSection]]:
        """Every fund of every fund house whose name contains `query` (a case-insensitive plain substring), as ordered sections.

        Funds of the four equity segments come first, in the order of SEGMENTS, each under its segment's title; every other
        fund goes under its AMFI category, A to Z. Inside a section the funds with a value for the window come first.
        """
        needle = query.strip().lower()
        houses = {fund.fund_house for fund in self._rows.values() if needle and needle in fund.fund_house.lower()}
        matched = [fund for fund in self._rows.values() if fund.fund_house in houses]
        sections = []
        for segment in SEGMENTS:
            funds = [fund for fund in matched if fund.segment == segment]
            if funds:
                sections.append(FundSection(segment, SEGMENT_TITLES[segment], _ranked_then_rest(funds, window)))
        by_category: dict[str, list[StoredFund]] = {}
        for fund in matched:
            if fund.segment is None:
                by_category.setdefault(fund.category or "Other funds", []).append(fund)
        for category in sorted(by_category, key=str.casefold):
            sections.append(FundSection(_category_key(category), category, _ranked_then_rest(by_category[category], window)))
        return sorted(houses), sections


def build_default_store(repo: FundRepo) -> FundStore:
    client = httpx.AsyncClient(follow_redirects=True)  # NAVAll.txt answers with a redirect
    return FundStore(
        repo,
        fetch_catalog=lambda: fetch_amfi_catalog(client),
        fetch_range=lambda start, end: fetch_nav_range(client, start, end),
        close=client.aclose,
    )
