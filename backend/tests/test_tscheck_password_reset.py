"""Criterion: Password reset flow works end-to-end with a demo token."""

import uuid

import pytest


def test_forgot_password_and_reset_with_demo_token(client):
    email = f"tscheck-reset-{uuid.uuid4().hex[:10]}@example.com"
    original_password = "TestPass!2026"
    new_password = "NewTestPass!2027"

    resp = client.post("/auth/register", json={"name": "Reset Tester", "email": email, "password": original_password})
    assert resp.status_code == 200, resp.text

    resp = client.post("/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    if not body.get("demo_token"):
        pytest.skip("server runs without EXPOSE_RESET_TOKEN=true, so no reset token is returned")
    token = body["demo_token"]

    resp = client.post("/auth/reset-password", json={"token": token, "password": new_password})
    assert resp.status_code == 200, resp.text

    # Old password should no longer work
    resp = client.post("/auth/login", json={"email": email, "password": original_password})
    assert resp.status_code == 401, resp.text

    # New password logs in successfully
    resp = client.post("/auth/login", json={"email": email, "password": new_password})
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == email


def test_forgot_password_unknown_email_does_not_error(client):
    resp = client.post("/auth/forgot-password", json={"email": f"tscheck-nouser-{uuid.uuid4().hex[:8]}@example.com"})
    assert resp.status_code == 200, resp.text
    assert resp.json().get("demo_token") is None
