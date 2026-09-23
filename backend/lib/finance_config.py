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
