"""Fund catalog (AMFI), return maths (mfapi NAV history) and the in-memory cache behind /api/funds (spec section 5)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from bisect import bisect_right
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

from lib.finance_config import (
    AMFI_NAV_URL, FUND_ACTIVE_NAV_MAX_AGE_DAYS, FUND_CACHE_TTL_HOURS, FUND_FETCH_CONCURRENCY, FUND_GLITCH_MOVE_PCT,
    FUND_REFRESH_RETRY_MINUTES, FUND_TOP_N, FUND_WINDOW_START_TOLERANCE_DAYS, MFAPI_SCHEME_URL,
)
from models.funds import FundRow

SEGMENTS = ("nifty", "large", "mid", "small")

_MONTHS = {name: number for number, name in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), start=1)}
_CATEGORY_LINE = re.compile(r"Schemes?\(.*\)$")
# "Nifty 50" (the trailing \b keeps "Nifty 500" out) or SBI-style "Nifty Index Fund", which also tracks the Nifty 50
_NIFTY_50 = re.compile(r"\bnifty\s*50\b|\bnifty\s+index\b", re.IGNORECASE)
_NIFTY_VARIANT = re.compile(r"next|equal|value|quality|alpha|momentum|low\s*vol|dividend", re.IGNORECASE)


@dataclass(frozen=True)
class CatalogEntry:
    scheme_code: str
    name: str
    fund_house: str
    segment: str
    nav: float
    nav_date: date


def _parse_amfi_date(text: str) -> date | None:
    """AMFI dates look like 23-Sep-2026. Month names are looked up, not strptime'd, so the server locale cannot break parsing."""
    parts = text.strip().split("-")
    if len(parts) != 3 or parts[1] not in _MONTHS:
        return None
    try:
        return date(int(parts[2]), _MONTHS[parts[1]], int(parts[0]))
    except ValueError:
        return None


def _is_growth(option: str) -> bool:
    """Fund houses label the growth option differently: Growth, GROWTH OPTION, Direct Growth, and ICICI Prudential's Cumulative."""
    lowered = option.lower()
    return "growth" in lowered or "cumulative" in lowered


def _segment(category: str, name: str) -> str | None:
    if "Large & Mid" in category:
        return None
    if "Large Cap Fund" in category:
        return "large"
    if "Mid Cap Fund" in category:
        return "mid"
    if "Small Cap Fund" in category:
        return "small"
    if "Index Funds" in category:
        match = _NIFTY_50.search(name)
        # variant words are only looked for after "Nifty": scheme names start with the fund house, which may contain one
        if match and not _NIFTY_VARIANT.search(name[match.start():]):
            return "nifty"
    return None


def parse_navall(text: str) -> list[CatalogEntry]:
    """AMFI's NAVAll.txt: a category header line, a fund-house line, then rows of code;isin;isin;name;plan;option;nav;date.

    Keeps Direct + Growth schemes of the four segments whose NAV is within FUND_ACTIVE_NAV_MAX_AGE_DAYS of the newest
    NAV in the file (the file's own clock, not the wall clock, so a stale download is not misread as everything dead).
    """
    entries: list[CatalogEntry] = []
    newest: date | None = None
    category = ""
    fund_house = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("Scheme Code"):
            continue
        if ";" not in line:
            if _CATEGORY_LINE.search(line):
                category = line
            else:
                fund_house = line
            continue
        parts = line.split(";")
        if len(parts) < 8 or not parts[0].isdigit():
            continue
        nav_date = _parse_amfi_date(parts[7])
        if nav_date is None:
            continue
        if newest is None or nav_date > newest:
            newest = nav_date
        if "direct" not in parts[4].lower() or not _is_growth(parts[5]):
            continue
        segment = _segment(category, parts[3])
        if segment is None:
            continue
        try:
            nav = float(parts[6])
        except ValueError:  # "N.A." while a scheme has no NAV yet
            continue
        entries.append(CatalogEntry(parts[0], parts[3].strip(), fund_house, segment, nav, nav_date))
    if newest is None:
        return []
    return [entry for entry in entries if (newest - entry.nav_date).days <= FUND_ACTIVE_NAV_MAX_AGE_DAYS]


# --- returns (spec section 5.2) -------------------------------------------------------------------------------------

DAYS_PER_YEAR = 365.25
History = list[tuple[date, float]]  # (NAV date, NAV)


@dataclass(frozen=True)
class ReturnSummary:
    returns: dict[str, float | None]
    max_is_annualised: bool
    start_date: date
    nav: float
    nav_date: date


def clean_history(history: History) -> History | None:
    """Ascending by date, one NAV per date, non-positive NAVs dropped.

    None when fewer than two NAVs remain, or when two consecutive NAVs differ by more than FUND_GLITCH_MOVE_PCT:
    a diversified fund does not move that much between two prints, so the series is untrustworthy.
    """
    points = sorted({nav_date: nav for nav_date, nav in history if nav > 0}.items())
    if len(points) < 2:
        return None
    for (_, previous), (_, current) in zip(points, points[1:]):
        if abs(current / previous - 1) * 100 > FUND_GLITCH_MOVE_PCT:
            return None
    return points


def _annualised_pct(start_nav: float, end_nav: float, elapsed_years: float) -> float:
    return ((end_nav / start_nav) ** (1 / elapsed_years) - 1) * 100


def _window_return(points: History, years: int) -> float | None:
    """Annualised return over the last `years`, from the last NAV on or before the window's start. None if the fund is younger."""
    end_date, end_nav = points[-1]
    start = end_date - timedelta(days=round(years * DAYS_PER_YEAR))
    dates = [nav_date for nav_date, _ in points]
    index = bisect_right(dates, start) - 1
    if index < 0:
        if (dates[0] - start).days > FUND_WINDOW_START_TOLERANCE_DAYS:
            return None
        index = 0
    elapsed_years = (end_date - dates[index]).days / DAYS_PER_YEAR
    if elapsed_years <= 0:
        return None
    return _annualised_pct(points[index][1], end_nav, elapsed_years)


def summarise_history(history: History) -> ReturnSummary | None:
    points = clean_history(history)
    if points is None:
        return None
    start_date, start_nav = points[0]
    end_date, end_nav = points[-1]
    elapsed_years = (end_date - start_date).days / DAYS_PER_YEAR
    if elapsed_years <= 0:
        return None
    annualised = elapsed_years >= 1
    max_return = _annualised_pct(start_nav, end_nav, elapsed_years) if annualised else (end_nav / start_nav - 1) * 100
    raw = {"1y": _window_return(points, 1), "3y": _window_return(points, 3), "5y": _window_return(points, 5), "max": max_return}
    return ReturnSummary(
        returns={window: None if value is None else round(value, 2) for window, value in raw.items()},
        max_is_annualised=annualised,
        start_date=start_date,
        nav=end_nav,
        nav_date=end_date,
    )


def build_row(entry: CatalogEntry, history: History) -> FundRow | None:
    summary = summarise_history(history)
    if summary is None:
        return None
    return FundRow(
        scheme_code=entry.scheme_code,
        name=entry.name,
        fund_house=entry.fund_house,
        segment=entry.segment,
        nav=summary.nav,
        nav_date=summary.nav_date,
        start_date=summary.start_date,
        returns=summary.returns,
        max_is_annualised=summary.max_is_annualised,
    )


def rank_rows(rows: list[FundRow], window: str) -> list[FundRow]:
    """Best return first, ties by name. Funds without that window are left out. For "max", annualised funds rank above absolute ones."""
    ranked = [row for row in rows if row.returns.get(window) is not None]
    if window == "max":
        ranked.sort(key=lambda row: (not row.max_is_annualised, -row.returns["max"], row.name))
    else:
        ranked.sort(key=lambda row: (-row.returns[window], row.name))
    return ranked


# --- cache (spec section 5.3) ---------------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

CatalogFetcher = Callable[[], Awaitable[list[CatalogEntry]]]
HistoryFetcher = Callable[[str], Awaitable[History]]


class FundStore:
    """In-process fund cache, rebuilt from AMFI + mfapi at startup and again once it is FUND_CACHE_TTL_HOURS old.

    Nothing is persisted: Render's free tier sleeps and wipes memory, and a cold start simply warms the cache again.
    The fetchers are injected so tests need no network.
    """

    def __init__(
        self,
        fetch_catalog: CatalogFetcher,
        fetch_history: HistoryFetcher,
        *,
        close: Callable[[], Awaitable[None]] | None = None,
        now: Callable[[], datetime] | None = None,
    ):
        self._fetch_catalog = fetch_catalog
        self._fetch_history = fetch_history
        self._close = close
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._rows: list[FundRow] = []
        self._loaded_at: datetime | None = None
        self._last_attempt: datetime | None = None
        self._last_failed = False
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self.as_of: date | None = None
        self.failed_count = 0  # catalog funds left out of the last load: fetch failed, or the history was unusable

    @property
    def status(self) -> str:
        if not self._rows:
            return "unavailable" if self._last_failed else "warming"
        expired = self._now() - self._loaded_at > timedelta(hours=FUND_CACHE_TTL_HOURS)
        return "stale" if self._last_failed or expired else "ready"

    def start(self) -> None:
        """Begin a background refresh. Needs a running event loop."""
        self._task = asyncio.get_running_loop().create_task(self.refresh())

    def ensure_fresh(self) -> None:
        """Called on each request: start a background refresh when data is missing or expired and none is running."""
        if self._lock.locked() or (self._task is not None and not self._task.done()):
            return
        now = self._now()
        if self._last_attempt is not None and now - self._last_attempt < timedelta(minutes=FUND_REFRESH_RETRY_MINUTES):
            return
        if self._loaded_at is not None and not self._last_failed and now - self._loaded_at <= timedelta(hours=FUND_CACHE_TTL_HOURS):
            return
        self.start()

    async def refresh(self) -> None:
        """Rebuild the cache. Single-flight: a call made while another is running returns at once. A failure keeps the old data."""
        if self._lock.locked():
            return
        async with self._lock:
            self._last_attempt = self._now()
            try:
                catalog = await self._fetch_catalog()
            except Exception:
                logger.exception("fund catalog fetch failed")
                catalog = []
            if not catalog:
                self._last_failed = True
                return

            semaphore = asyncio.Semaphore(FUND_FETCH_CONCURRENCY)

            async def load(entry: CatalogEntry) -> FundRow | None:
                async with semaphore:
                    try:
                        history = await self._fetch_history(entry.scheme_code)
                    except Exception:
                        logger.warning("NAV history fetch failed for scheme %s", entry.scheme_code)
                        return None
                try:
                    return build_row(entry, history)
                except Exception:  # one unusable history must leave that fund out, never abort the whole refresh
                    logger.warning("NAV history unusable for scheme %s", entry.scheme_code)
                    return None

            results = await asyncio.gather(*(load(entry) for entry in catalog))
            rows = [row for row in results if row is not None]
            if not rows:
                self._last_failed = True
                return
            self._rows = rows
            self.failed_count = len(results) - len(rows)
            self.as_of = max(row.nav_date for row in rows)
            self._loaded_at = self._now()
            self._last_failed = False

    def top(self, window: str) -> dict[str, list[FundRow]]:
        return {segment: rank_rows([row for row in self._rows if row.segment == segment], window)[:FUND_TOP_N] for segment in SEGMENTS}

    def search(self, query: str, window: str) -> tuple[list[str], dict[str, list[FundRow]]]:
        """Funds of every fund house whose name contains `query` (case-insensitive plain substring), grouped by segment, uncapped."""
        needle = query.strip().lower()
        houses = sorted({row.fund_house for row in self._rows if needle and needle in row.fund_house.lower()})
        matched = [row for row in self._rows if row.fund_house in houses]
        return houses, {segment: rank_rows([row for row in matched if row.segment == segment], window) for segment in SEGMENTS}

    async def aclose(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._close is not None:
            await self._close()


# --- live sources (spec sections 5.1, 5.2) --------------------------------------------------------------------------

_HEADERS = {"User-Agent": "SurakshaCFO-demo/1.0 (educational project)"}


async def fetch_amfi_catalog(client: httpx.AsyncClient) -> list[CatalogEntry]:
    response = await client.get(AMFI_NAV_URL, headers=_HEADERS, timeout=60)
    response.raise_for_status()
    return parse_navall(response.text)


async def _get_history(client: httpx.AsyncClient, scheme_code: str) -> History:
    response = await client.get(MFAPI_SCHEME_URL.format(code=scheme_code), headers=_HEADERS, timeout=60)
    response.raise_for_status()
    return [(datetime.strptime(item["date"], "%d-%m-%Y").date(), float(item["nav"])) for item in response.json()["data"]]


async def fetch_mfapi_history(client: httpx.AsyncClient, scheme_code: str) -> History:
    """NAV history from mfapi.in (dd-mm-yyyy dates, newest first). The mirror is free and sometimes slow, so one retry."""
    try:
        return await _get_history(client, scheme_code)
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return await _get_history(client, scheme_code)


def build_default_store() -> FundStore:
    client = httpx.AsyncClient(follow_redirects=True)
    return FundStore(
        fetch_catalog=lambda: fetch_amfi_catalog(client),
        fetch_history=lambda scheme_code: fetch_mfapi_history(client, scheme_code),
        close=client.aclose,
    )
