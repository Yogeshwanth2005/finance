"""Tunable constants for the allocation, gap-analysis and insurance-matching modules (restored from dddc580^ app/config.py)."""

EMERGENCY_FUND_MULTIPLIER = 6
INCOME_REPLACEMENT_MULTIPLIER = 10
HEALTH_COVER_BASELINE = 500_000
HIGH_INTEREST_DEBT_THRESHOLD = 12  # defined but never referenced by any module, in the original as well

BASE_EQUITY_AGE_CONSTANT = 100
RISK_TOLERANCE_MULTIPLIERS = {
    "conservative": 0.8,
    "moderate": 1.0,
    "aggressive": 1.2,
}
SHORT_HORIZON_THRESHOLD = 3
SHORT_HORIZON_SHIFT = 20
GOLD_ALLOCATION_PCT = 10

FUND_EXAMPLES_PER_CATEGORY = 3
INSURANCE_EXAMPLES_PER_GAP_TYPE = 2

# Fund explorer + inflation-goal check (docs/superpowers/specs/2026-09-24-fund-explorer-and-goal-check-design.md).
# Nothing below is a sourced figure: each value is an assumption or a one-off measurement (spec section 9), kept here so it can be edited.
GROWTH_SHARE_BASE_PCT = 40  # mid + small share of the equity slice at a 1.0 risk multiplier
MID_SHARE_OF_GROWTH = 0.625  # mid gets 5/8 of that growth slice, small the other 3/8

INFLATION_PCT = 6
RETURN_MARGIN_PCT = {"conservative": 3, "moderate": 4, "aggressive": 5}  # extra over inflation that counts as success
EXPECTED_RETURN_PCT = {"large": 11, "mid": 13, "small": 14, "debt": 7, "gold": 8}  # assumed long-run returns, not measured ones
STRESS_FALL_PCT = {"large": 37, "mid": 36, "small": 38, "debt": 0, "gold": 0}  # Jan-Apr 2020 median fall; debt and gold assumed flat

AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
FUND_ACTIVE_NAV_MAX_AGE_DAYS = 7  # a scheme is live when its NAV is within this many days of the newest NAV in the file
FUND_TOP_N = 10  # funds per segment on the dashboard's top lists
FUND_GLITCH_MOVE_PCT = 35  # a move this big between two consecutive NAVs is a data glitch, not a price move
FUND_WINDOW_START_TOLERANCE_DAYS = 7  # a fund launched this soon after a window's start still gets that window
FUND_CACHE_TTL_HOURS = 24
FUND_FETCH_CONCURRENCY = 6  # simultaneous mfapi calls
FUND_REFRESH_RETRY_MINUTES = 5  # after a failed refresh, wait this long before trying again
