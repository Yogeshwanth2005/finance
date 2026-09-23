"""Shared synthetic household for the pure-function tests (same profile as the dashboard's frontend sample)."""

from __future__ import annotations

from typing import Any


def payload(**overrides: Any) -> dict[str, Any]:
    """A valid ProfileInput payload; pass keyword overrides to vary one thing at a time."""
    base: dict[str, Any] = {
        "full_name": "Sample Person",
        "dob": "1990-06-12",
        "age": 35,
        "city_tier": "tier_1",
        "marital_status": "married",
        "dependents": 3,
        "spouse_full_name": "Sample Partner",
        "spouse_dob": "1992-09-18",
        "spouse_age": 33,
        "spouse_employment_type": "mnc",
        "employment_type": "mnc",
        "annual_income": 2_400_000,
        "spouse_income": 900_000,
        "monthly_expenses": 85_000,
        "annual_bonus": 300_000,
        "home_loan": 6_500_000,
        "other_loans": 450_000,
        "monthly_emi": 58_000,
        "other_debts": 0,
        "current_health_cover_lakh": 5,
        "existing_term_cover_crore": 0.5,
        "emergency_savings": 300_000,
        "current_investments": 1_200_000,
    }
    return {**base, **overrides}
