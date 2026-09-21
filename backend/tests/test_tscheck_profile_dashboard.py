"""Criterion: family profile completion + dual-income dashboard calculations."""

import uuid


def _profile_payload():
    return {
        "full_name": "Tscheck Family",
        "dob": "1990-01-01",
        "age": 35,
        "city_tier": "tier_1",
        "marital_status": "married",
        "dependents": 2,
        "spouse_full_name": "Tscheck Partner",
        "spouse_dob": "1991-02-02",
        "spouse_age": 34,
        "spouse_employment_type": "mnc",
        "employment_type": "mnc",
        "annual_income": 1800000,
        "spouse_income": 1200000,
        "monthly_expenses": 60000,
        "annual_bonus": 100000,
        "home_loan": 3000000,
        "other_loans": 0,
        "monthly_emi": 25000,
        "other_debts": 0,
        "current_health_cover_lakh": 5,
        "existing_term_cover_crore": 0.5,
        "emergency_savings": 200000,
        "current_investments": 500000,
    }


def test_save_profile_and_dashboard_reflects_dual_income(client):
    email = f"tscheck-profile-{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Tscheck Family", "email": email, "password": password})
    assert resp.status_code == 200, resp.text
    # Secure cookies require https; test client hits plain http, so authenticate via Bearer header.
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on register"
    auth_header = {"Authorization": f"Bearer {token}"}

    payload = _profile_payload()
    resp = client.post("/profile", json=payload, headers=auth_header)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["profile"]["full_name"] == "Tscheck Family"
    assert body["profile"]["spouse_full_name"] == "Tscheck Partner"

    analysis = body["analysis"]
    expected_income = payload["annual_income"] + payload["spouse_income"] + payload["annual_bonus"]
    assert analysis["annual_household_income"] == expected_income
    assert analysis["protection_score"] >= 0
    assert "term_gap_crore" in analysis
    assert "health_gap_lakh" in analysis
    assert "emergency_gap" in analysis
    assert "investable_surplus" in analysis

    # GET reflects the saved account-owned profile
    resp = client.get("/profile", headers=auth_header)
    assert resp.status_code == 200, resp.text
    assert resp.json()["profile"]["full_name"] == "Tscheck Family"
    assert resp.json()["analysis"]["annual_household_income"] == expected_income


def test_profile_requires_authentication(client):
    resp = client.get("/profile")
    assert resp.status_code in (401, 403), resp.text
