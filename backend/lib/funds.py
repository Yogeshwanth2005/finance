"""Fund catalog (AMFI's NAVAll.txt), AMFI's dated NAV reports and the return maths behind /api/funds (spec section 5.1)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

from lib.finance_config import (
    AMFI_FETCH_TIMEOUT_SECONDS, AMFI_HISTORY_URL, AMFI_NAV_URL, FUND_ACTIVE_NAV_MAX_AGE_DAYS, FUND_END_RANGE_DAYS, FUND_GLITCH_MOVE_PCT,
    FUND_WINDOW_LOOKBACK_DAYS, FUND_WINDOW_START_TOLERANCE_DAYS,
)

SEGMENTS = ("nifty", "large", "mid", "small")
WINDOWS = ("1y", "3y", "5y", "max")
WINDOW_YEARS = {"1y": 1, "3y": 3, "5y": 5}  # the windows that come from the dated files; "max" needs the fund's first NAV

_MONTHS = {name: number for number, name in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), start=1)}
_CATEGORY_LINE = re.compile(r"Schemes?\s*\(.*\)\s*$")
# "Nifty 50" (the trailing \b keeps "Nifty 500" out) or SBI-style "Nifty Index Fund", which also tracks the Nifty 50
_NIFTY_50 = re.compile(r"\bnifty\s*50\b|\bnifty\s+index\b", re.IGNORECASE)
_NIFTY_VARIANT = re.compile(r"next|equal|value|quality|alpha|momentum|low\s*vol|dividend", re.IGNORECASE)


@dataclass(frozen=True)
class CatalogEntry:
    scheme_code: str
    name: str
    fund_house: str
    segment: str | None  # nifty, large, mid or small; None for every other category
    nav: float
    nav_date: date
    category: str = ""  # AMFI's own sub-category label, e.g. "Large Cap Fund"


def _parse_amfi_date(text: str) -> date | None:
    """AMFI dates look like 23-Sep-2026. Month names are looked up, not strptime'd, so the server locale cannot break parsing."""
    parts = text.strip().split("-")
    if len(parts) != 3 or parts[1] not in _MONTHS:
        return None
    try:
        return date(int(parts[2]), _MONTHS[parts[1]], int(parts[0]))
    except ValueError:
        return None


def _format_amfi_day(day: date) -> str:
    """The 05-Mar-2026 form AMFI's dated report asks for, again without the locale."""
    return f"{day.day:02d}-{tuple(_MONTHS)[day.month - 1]}-{day.year}"


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


def _category_label(header: str) -> str:
    """AMFI's own label for a category line: the text inside the outermost parentheses, after the first " - " when there is one.

    "Open Ended Schemes(Equity Scheme - Large Cap Fund)" gives "Large Cap Fund"; "Close Ended Schemes(ELSS)" gives "ELSS".
    U+FFFD, which AMFI's file has where a name should hold an apostrophe, becomes one.
    """
    start, end = header.find("("), header.rfind(")")
    inner = header[start + 1:end] if 0 <= start < end else header
    return inner.split(" - ", 1)[-1].replace("\N{REPLACEMENT CHARACTER}", "'").strip()


def parse_navall(text: str) -> list[CatalogEntry]:
    """AMFI's NAVAll.txt: a category header line, a fund-house line, then rows of code;isin;isin;name;plan;option;nav;date.

    Keeps every Direct + Growth scheme, whatever its category, whose NAV is within FUND_ACTIVE_NAV_MAX_AGE_DAYS of the newest
    NAV in the file (the file's own clock, not the wall clock, so a stale download is not misread as everything dead).
    `segment` is one of the four equity segments, or None.
    """
    entries: list[CatalogEntry] = []
    newest: date | None = None
    category = ""  # the category line above the current rows, kept whole for the segment rules
    label = ""
    fund_house = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("Scheme Code"):
            continue
        if ";" not in line:
            if _CATEGORY_LINE.search(line):
                category = line
                label = _category_label(line)
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
        try:
            nav = float(parts[6])
        except ValueError:  # "N.A." while a scheme has no NAV yet
            continue
        entries.append(CatalogEntry(parts[0], parts[3].strip(), fund_house, _segment(category, parts[3]), nav, nav_date, label))
    if newest is None:
        return []
    return [entry for entry in entries if (newest - entry.nav_date).days <= FUND_ACTIVE_NAV_MAX_AGE_DAYS]


# --- dated NAV reports ----------------------------------------------------------------------------------------------

DAYS_PER_YEAR = 365.25
History = list[tuple[date, float]]  # (NAV date, NAV), ascending by date


def parse_nav_report(text: str) -> dict[str, History]:
    """AMFI's dated NAV report: a header line, then category lines, fund-house lines and rows of code;name;plan;option;isin;isin;nav;date.

    Keeps only the rows (a positive NAV on a parseable date), ascending by date per scheme. A response without the header line is
    not the report (AMFI answers bad parameters with an HTML page) and raises ValueError.
    """
    lines = text.splitlines()
    first = next((line.strip().lstrip("\N{ZERO WIDTH NO-BREAK SPACE}") for line in lines if line.strip()), "")
    if not first.startswith("Scheme Code;"):
        raise ValueError("not an AMFI NAV report")
    report: dict[str, History] = {}
    for raw in lines:
        parts = raw.strip().split(";")
        if len(parts) != 8 or not parts[0].isdigit():
            continue
        nav_date = _parse_amfi_date(parts[7])
        if nav_date is None:
            continue
        try:
            nav = float(parts[6])
        except ValueError:  # "N.A."
            continue
        if nav > 0:
            report.setdefault(parts[0], []).append((nav_date, nav))
    for points in report.values():
        points.sort()
    return report


# --- returns from the dated reports (spec section 5.1) ---------------------------------------------------------------


def window_targets(newest: date) -> dict[str, date]:
    """T_N for each window: the one date, the same for every fund, that a 1, 3 or 5 year return starts from."""
    return {window: newest - timedelta(days=round(years * DAYS_PER_YEAR)) for window, years in WINDOW_YEARS.items()}


def fetch_plan(newest: date) -> dict[str, tuple[date, date]]:
    """The four date ranges a refresh downloads: "end" (the newest NAVs) and, per window, a range around the window's start."""
    plan = {"end": (newest - timedelta(days=FUND_END_RANGE_DAYS), newest)}
    for window, target in window_targets(newest).items():
        plan[window] = (target - timedelta(days=FUND_WINDOW_LOOKBACK_DAYS), target + timedelta(days=FUND_WINDOW_START_TOLERANCE_DAYS))
    return plan


def _has_glitch(points: History) -> bool:
    """True when two consecutive NAVs differ by more than FUND_GLITCH_MOVE_PCT (a diversified fund does not move that much between prints)."""
    navs = [nav for _, nav in sorted(dict(points).items())]
    return any(before <= 0 or abs(after / before - 1) * 100 > FUND_GLITCH_MOVE_PCT for before, after in zip(navs, navs[1:]))


def _base_point(points: History, target: date) -> tuple[date, float] | None:
    """The last NAV on or before `target`; failing that, the first one within FUND_WINDOW_START_TOLERANCE_DAYS after it."""
    before = [point for point in points if point[0] <= target]
    if before:
        return max(before)
    limit = target + timedelta(days=FUND_WINDOW_START_TOLERANCE_DAYS)
    after = [point for point in points if target < point[0] <= limit]
    return min(after) if after else None


def _annualised_pct(start_nav: float, end_nav: float, elapsed_years: float) -> float:
    return ((end_nav / start_nav) ** (1 / elapsed_years) - 1) * 100


def compute_window_returns(
    latest: tuple[date, float], end_points: History, window_points: dict[str, History], newest: date
) -> dict[str, float | None]:
    """A fund's annualised 1y / 3y / 5y returns from the dated reports; None for a window it cannot support.

    `latest` is the fund's newest NAV from the catalog and `newest` the newest NAV date across the catalog. A glitch in the
    end range voids every window, one in a window's own range voids that window. The exponent uses the actual days between
    the base NAV and `latest`, so a fund whose newest NAV is a few days old is still annualised correctly.
    """
    latest_date, latest_nav = latest
    returns: dict[str, float | None] = {window: None for window in WINDOW_YEARS}
    if latest_nav <= 0 or _has_glitch([*end_points, latest]):
        return returns
    for window, target in window_targets(newest).items():
        points = window_points.get(window, [])
        base = None if _has_glitch(points) else _base_point(points, target)
        if base is None:
            continue
        elapsed_years = (latest_date - base[0]).days / DAYS_PER_YEAR
        if elapsed_years > 0:
            returns[window] = round(_annualised_pct(base[1], latest_nav, elapsed_years), 2)
    return returns


def compute_max_return(first: tuple[date, float] | None, latest: tuple[date, float]) -> tuple[float | None, bool | None]:
    """The return since the fund's first NAV, and whether it is annualised: annualised from a year on, absolute before that.

    (None, None) while the first NAV is unknown or no time has passed since it.
    """
    if first is None or first[1] <= 0:
        return None, None
    elapsed_years = (latest[0] - first[0]).days / DAYS_PER_YEAR
    if elapsed_years <= 0:
        return None, None
    if elapsed_years >= 1:
        return round(_annualised_pct(first[1], latest[1], elapsed_years), 2), True
    return round((latest[1] / first[1] - 1) * 100, 2), False


# --- live sources ---------------------------------------------------------------------------------------------------

_HEADERS = {"User-Agent": "SurakshaCFO-demo/1.0 (educational project)"}


async def fetch_amfi_catalog(client: httpx.AsyncClient) -> list[CatalogEntry]:
    response = await client.get(AMFI_NAV_URL, headers=_HEADERS, timeout=60)
    response.raise_for_status()
    return parse_navall(response.text)


async def _get_report(client: httpx.AsyncClient, start: date, end: date) -> dict[str, History]:
    params = {"frmdt": _format_amfi_day(start), "todt": _format_amfi_day(end)}
    response = await client.get(AMFI_HISTORY_URL, params=params, headers=_HEADERS, timeout=AMFI_FETCH_TIMEOUT_SECONDS)
    response.raise_for_status()
    return parse_nav_report(response.text)


async def fetch_nav_range(client: httpx.AsyncClient, start: date, end: date) -> dict[str, History]:
    """Every scheme's NAVs from AMFI's dated report for start..end. One retry: a range is 1 to 7 MB and a download can drop."""
    try:
        return await _get_report(client, start, end)
    except (httpx.HTTPError, ValueError):
        return await _get_report(client, start, end)
