from typing import Dict, Any, List

def match_insurance_plans(profile: Dict[str, Any], reference_plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deterministic insurance reference matcher (Section 6.2).
    Matches plans based on coverage proximity and lapping rules.
    """
    target_health = profile.get("target_health_cover", 500000)
    target_term = profile.get("target_term_cover", 10000000)

    matches = []
    for plan in reference_plans:
        # Logic: Plan must provide at least 80% of the target cover to be considered a match
        # and not exceed 200% (too expensive/over-insured)
        plan_cover = plan.get("cover_amount", 0)

        # If it's a health plan
        if plan.get("type") == "health":
            if target_health * 0.8 <= plan_cover <= target_health * 2.0:
                matches.append(plan)
        # If it's a term plan
        elif plan.get("type") == "term":
            if target_term * 0.8 <= plan_cover <= target_term * 2.0:
                matches.append(plan)

    # Sort matches by claim settlement ratio (CSR) descending
    return sorted(matches, key=lambda x: x.get("claimSettlementRatioPct", 0), reverse=True)
