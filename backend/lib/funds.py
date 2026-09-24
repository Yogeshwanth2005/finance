"""Fund catalog (AMFI), return maths (mfapi NAV history) and the in-memory cache behind /api/funds (spec section 5)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from lib.finance_config import FUND_ACTIVE_NAV_MAX_AGE_DAYS

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
