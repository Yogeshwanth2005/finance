from lib.finance_config import INSURANCE_EXAMPLES_PER_GAP_TYPE


# Closest sum-assured match to the computed gap — never "largest" or
# "cheapest" — to avoid the selection itself acting as a ranking signal
# (see .agents/context/subsystem-notes.md).
def select_insurance_examples(plan_type: str, gap_amount: float, plans: list[dict], count: int | None = None) -> list[dict]:
    if count is None:
        count = INSURANCE_EXAMPLES_PER_GAP_TYPE
    matching = [p for p in plans if p["plan_type"] == plan_type]
    matching.sort(key=lambda p: abs(p["sum_assured_max"] - gap_amount))
    return matching[:count]
