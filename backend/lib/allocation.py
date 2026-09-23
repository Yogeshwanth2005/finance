from lib.finance_config import (
    BASE_EQUITY_AGE_CONSTANT, RISK_TOLERANCE_MULTIPLIERS,
    SHORT_HORIZON_THRESHOLD, SHORT_HORIZON_SHIFT, GOLD_ALLOCATION_PCT,
    FUND_EXAMPLES_PER_CATEGORY,
)

# Section 5.2's example: equity_pct -> "large-cap index fund or diversified
# equity mutual fund category" implies each bucket spans 2 category values,
# not 1 - mirrored here explicitly since the plan never spells the mapping
# out as a table.
BUCKET_CATEGORIES = {
    "equity": ["equity_large_cap", "equity_diversified"],
    "debt": ["debt_short_duration", "fixed_deposit"],
    "gold": ["gold_etf", "sovereign_gold_bond"],
}


# No v1 source for the base equity formula or the gold sleeve (see
# decisions/log.md): base equity is the standard "constant minus age"
# glide path, and gold is a flat diversification sleeve capped by
# whatever equity leaves behind, so the three buckets always sum to 100.
def compute_allocation(age: int, risk_tolerance: str, investment_horizon_years: int) -> dict:
    base_equity_pct = BASE_EQUITY_AGE_CONSTANT - age
    equity_pct = base_equity_pct * RISK_TOLERANCE_MULTIPLIERS[risk_tolerance]

    if investment_horizon_years <= SHORT_HORIZON_THRESHOLD:
        equity_pct -= SHORT_HORIZON_SHIFT

    equity_pct = min(100, max(0, equity_pct))

    gold_pct = min(GOLD_ALLOCATION_PCT, 100 - equity_pct)
    debt_pct = 100 - equity_pct - gold_pct

    return {"equity_pct": equity_pct, "debt_pct": debt_pct, "gold_pct": gold_pct}


def select_fund_examples(bucket: str, funds: list[dict], count: int | None = None) -> list[dict]:
    if count is None:
        count = FUND_EXAMPLES_PER_CATEGORY
    categories = BUCKET_CATEGORIES[bucket]
    matching = [f for f in funds if f["category"] in categories]
    matching.sort(key=lambda f: f["aum_cr"], reverse=True)
    return matching[:count]
