from typing import Dict, Any, List
from app.config import DEMO_MODE

def compute_asset_allocation(profile: Dict[str, Any], reference_funds: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministic asset allocation engine (Section 5.1-5.2).
    Rule: 100 - Age (Base Equity), scaled by risk tolerance.
    """
    age = profile.get("age", 30)
    risk_tolerance = profile.get("risk_tolerance", "moderate") # conservative, moderate, aggressive

    # Base Equity: 100 - Age
    base_equity = max(0, min(100, 100 - age))

    # Risk Scaling
    multipliers = {"conservative": 0.8, "moderate": 1.0, "aggressive": 1.2}
    equity_pct = max(0, min(100, base_equity * multipliers.get(risk_tolerance, 1.0)))

    # Gold is a flat 10% diversification sleeve
    gold_pct = 10.0
    # Debt gets the remainder
    debt_pct = max(0, 100 - equity_pct - gold_pct)

    # Re-adjust equity if gold+debt > 100
    if equity_pct + debt_pct + gold_pct > 100:
        equity_pct = 100 - debt_pct - gold_pct

    # Fund selection: Sorted by AUM descending per category
    recommended = []
    categories = {
        "equity": "Large Cap / Index",
        "debt": "Short Term Debt / Liquid",
        "gold": "Gold ETF / SGB"
    }

    for key, cat_name in categories.items():
        # Filter funds by category and sort by AUM
        matches = [f for f in reference_funds if f.get("category") == cat_name]
        sorted_matches = sorted(matches, key=lambda x: x.get("aumCr", 0), reverse=True)
        if sorted_matches:
            recommended.append(sorted_matches[0])

    return {
        "equity_pct": round(equity_pct, 2),
        "debt_pct": round(debt_pct, 2),
        "gold_pct": round(gold_pct, 2),
        "recommended_funds": recommended
    }
