from lib.finance_config import (
    BASE_EQUITY_AGE_CONSTANT, RISK_TOLERANCE_MULTIPLIERS,
    SHORT_HORIZON_THRESHOLD, SHORT_HORIZON_SHIFT, GOLD_ALLOCATION_PCT,
    FUND_EXAMPLES_PER_CATEGORY, GROWTH_SHARE_BASE_PCT, MID_SHARE_OF_GROWTH,
    INFLATION_PCT, RETURN_MARGIN_PCT, EXPECTED_RETURN_PCT, STRESS_FALL_PCT,
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


def _equity_shares(risk_tolerance: str) -> tuple[float, float, float]:
    """Large / mid / small share of the equity slice, in percent. A higher risk tolerance moves weight from large into mid and small."""
    growth_share = min(100.0, GROWTH_SHARE_BASE_PCT * RISK_TOLERANCE_MULTIPLIERS[risk_tolerance])
    mid_share = growth_share * MID_SHARE_OF_GROWTH
    return 100.0 - growth_share, mid_share, growth_share - mid_share


# No source for these shares (see the spec, section 6.1): a rule of thumb keyed off the risk multiplier already in finance_config.
def compute_equity_split(risk_tolerance: str, equity_pct: float) -> dict:
    large_share, mid_share, _ = _equity_shares(risk_tolerance)
    large_pct = round(equity_pct * large_share / 100, 1)
    mid_pct = round(equity_pct * mid_share / 100, 1)
    # small takes the remainder so the three always add back up to the equity slice
    small_pct = round(equity_pct - large_pct - mid_pct, 1)
    return {"large_pct": large_pct, "mid_pct": mid_pct, "small_pct": small_pct}


def _weighted(per_bucket: dict[str, float], buckets: dict[str, float]) -> float:
    return sum(buckets[name] * per_bucket[name] for name in buckets) / 100


def _equity_blend(per_bucket: dict[str, float], risk_tolerance: str) -> float:
    large_share, mid_share, small_share = _equity_shares(risk_tolerance)
    return (large_share * per_bucket["large"] + mid_share * per_bucket["mid"] + small_share * per_bucket["small"]) / 100


# Spec section 6.2. Returns are assumptions from finance_config, never measured past returns: a strong recent run
# (gold, small cap) would otherwise steer every profile into the same corner.
def compute_goal_check(risk_tolerance: str, investment_horizon_years: int, allocation: dict, split: dict) -> dict:
    buckets = {
        "large": split["large_pct"], "mid": split["mid_pct"], "small": split["small_pct"],
        "debt": allocation["debt_pct"], "gold": allocation["gold_pct"],
    }
    margin = RETURN_MARGIN_PCT[risk_tolerance]
    target = INFLATION_PCT + margin
    expected = _weighted(EXPECTED_RETURN_PCT, buckets)
    beats_target = expected >= target

    reachable: bool | None = True if beats_target else None
    suggestion_suppressed = False
    min_equity_pct = None
    crash_loss_at_min_equity_pct = None
    if not beats_target:
        if investment_horizon_years <= SHORT_HORIZON_THRESHOLD:
            # a short horizon is exactly when a fall cannot be waited out: report the return, never push equity up
            suggestion_suppressed = True
        else:
            gold = allocation["gold_pct"]
            spread = _equity_blend(EXPECTED_RETURN_PCT, risk_tolerance) - EXPECTED_RETURN_PCT["debt"]
            # expected return is linear in equity when gold and the cap shares are held fixed and debt takes the rest
            needed = (100 * target - gold * EXPECTED_RETURN_PCT["gold"] - (100 - gold) * EXPECTED_RETURN_PCT["debt"]) / spread if spread > 0 else None
            if needed is None or needed > 100 - gold:
                reachable = False
            else:
                reachable = True
                min_equity_pct = round(needed, 1)
                crash_loss_at_min_equity_pct = round(
                    (needed * _equity_blend(STRESS_FALL_PCT, risk_tolerance) + (100 - gold - needed) * STRESS_FALL_PCT["debt"] + gold * STRESS_FALL_PCT["gold"]) / 100, 1
                )

    return {
        "inflation_pct": INFLATION_PCT,
        "margin_pct": margin,
        "target_pct": target,
        "expected_return_pct": round(expected, 1),
        "beats_target": beats_target,
        "reachable": reachable,
        "suggestion_suppressed": suggestion_suppressed,
        "min_equity_pct": min_equity_pct,
        "crash_loss_pct": round(_weighted(STRESS_FALL_PCT, buckets), 1),
        "crash_loss_at_min_equity_pct": crash_loss_at_min_equity_pct,
    }
