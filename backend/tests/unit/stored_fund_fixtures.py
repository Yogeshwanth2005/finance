"""A StoredFund builder for the fund tests: every field has a plausible default, override what a test cares about."""

from datetime import date, datetime, timezone

from lib.fund_repo import StoredFund

END = date(2026, 9, 23)  # the newest NAV date of every fixture fund
NOW = datetime(2026, 9, 24, 9, 0, tzinfo=timezone.utc)  # the clock the store tests start at
UNKNOWN_MAX = {"1y": None, "3y": None, "5y": None, "max": None}


def stored(code="1", **overrides) -> StoredFund:
    fields = {
        "scheme_code": code,
        "name": f"Fund {code}",
        "fund_house": "Alpha Mutual Fund",
        "category": "Large Cap Fund",
        "segment": "large",
        "nav": 100.0,
        "nav_date": END,
        "returns": {"1y": 12.0, "3y": 12.0, "5y": 12.0, "max": 12.0},
        "max_is_annualised": True,
        "computed_at": NOW,
        "first_nav": 10.0,
        "first_nav_date": date(2013, 1, 1),
        "first_nav_source": "checkpoint",
    }
    fields.update(overrides)
    return StoredFund(**fields)


def unresolved(code="1", **overrides) -> StoredFund:
    """A fund whose first NAV is not known yet, so it has no Max return."""
    return stored(code, returns=dict(UNKNOWN_MAX), max_is_annualised=None, first_nav=None, first_nav_date=None, first_nav_source=None, **overrides)
