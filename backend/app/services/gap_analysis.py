from typing import Dict, Any
from app.config import DEMO_MODE

def compute_gap_analysis(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic gap analysis engine (Sections 4.1-4.5).
    Pure function: Input profile -> Output gaps and scores.
    """
    # 1. Emergency Fund Gap (Target: 6x monthly expenses)
    monthly_exp = profile.get("monthly_expenses", 0)
    savings = profile.get("emergency_savings", 0)
    target_ef = monthly_exp * 6
    ef_gap = max(0, target_of_ef := target_ef - savings)

    ef_status = "adequate"
    if savings < (target_ef * 0.5):
        ef_status = "inadequate"
    elif savings < target_ef:
        ef_status = "building"

    # 2. Term Cover Gap (Simplified human life value: 10x annual income)
    income = profile.get("annual_income", 0)
    existing_term = profile.get("existing_term_cover", 0)
    target_term = income * 10
    term_gap = max(0, target_term - existing_term)

    # 3. Health Cover Gap (Baseline: 5L + 5L per dependent)
    dependents = profile.get("dependents_count", 0)
    personal_health = profile.get("personal_health_cover", 0)
    employer_health = profile.get("employer_health_cover", 0)
    effective_health = personal_health + employer_health
    target_health = 500000 + (dependents * 500000)
    health_gap = max(0, target_health - effective_health)

    # 4. Protection Score (Simple Weighted Average)
    # EF (40%), Term (30%), Health (30%)
    ef_score = min(100, (savings / target_ef * 100)) if target_ef > 0 else 100
    term_score = min(100, (existing_term / target_term * 100)) if target_term > 0 else 100
    health_score = min(100, (effective_health / target_health * 100)) if target_health > 0 else 100

    final_score = int((ef_score * 0.4) + (term_score * 0.3) + (health_score * 0.3))

    return {
        "emergency_fund_gap": ef_gap,
        "ef_status": ef_status,
        "term_cover_gap": term_gap,
        "health_cover_gap": health_gap,
        "protection_score": final_score,
        "details": {
            "target_ef": target_ef,
            "target_term": target_term,
            "target_health": target_health
        }
    }
