"""Criterion: the saved risk tolerance and investment horizon reach the dashboard's allocation split end to end."""

import uuid

from .unit.profiles import payload


def _signed_in_headers(client):
    email = f"alloc-{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post("/auth/register", json={"name": "Alloc Family", "email": email, "password": "TestPass!2026"})
    assert resp.status_code == 200, resp.text
    # Secure cookies need https; the test client is plain http, so authenticate with the Bearer header.
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on register"
    return {"Authorization": f"Bearer {token}"}


def test_allocation_follows_the_saved_risk_tolerance_and_horizon(client):
    headers = _signed_in_headers(client)

    resp = client.post("/profile", json=payload(age=30, risk_tolerance="aggressive", investment_horizon_years=3), headers=headers)
    assert resp.status_code == 200, resp.text
    saved = resp.json()
    # (100 - 30) x 1.2 = 84, minus the 20-point short-horizon shift = 64; gold is a flat 10; debt is the rest.
    assert saved["analysis"]["allocation"] == {"equity_pct": 64.0, "debt_pct": 26.0, "gold_pct": 10.0}

    resp = client.get("/profile", headers=headers)
    assert resp.status_code == 200, resp.text
    reread = resp.json()
    assert reread["profile"]["risk_tolerance"] == "aggressive"
    assert reread["profile"]["investment_horizon_years"] == 3
    assert reread["analysis"]["allocation"] == saved["analysis"]["allocation"]


def test_omitting_the_new_fields_falls_back_to_moderate_and_ten_years(client):
    headers = _signed_in_headers(client)

    resp = client.post("/profile", json=payload(age=35), headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["profile"]["risk_tolerance"] == "moderate"
    assert body["profile"]["investment_horizon_years"] == 10
    assert body["analysis"]["allocation"] == {"equity_pct": 65.0, "debt_pct": 25.0, "gold_pct": 10.0}


def test_an_unknown_risk_tolerance_is_rejected(client):
    headers = _signed_in_headers(client)

    resp = client.post("/profile", json=payload(risk_tolerance="reckless"), headers=headers)
    assert resp.status_code == 422, resp.text
