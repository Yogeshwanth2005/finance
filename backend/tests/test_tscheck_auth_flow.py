"""Criterion: Email/password signup, secure session persistence, login, and logout work."""

import uuid

import pytest


def _unique_email():
    return f"tscheck-auth-{uuid.uuid4().hex[:10]}@example.com"


def test_register_login_session_logout(client):
    email = _unique_email()
    password = "TestPass!2026"

    # Register
    resp = client.post("/auth/register", json={"name": "Tscheck User", "email": email, "password": password})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == email
    assert body["role"] == "user"
    assert body["profile_complete"] is False

    # The backend sets secure (https-only) cookies since FRONTEND_URL is https; the test
    # client talks to the server over plain http, so the cookie jar will not resend them
    # automatically (matches real browser behavior on http-only origins). We resend the
    # issued cookie value explicitly via the Cookie header to exercise the same
    # /auth/session flow the frontend relies on for persistence.
    access_token = client.cookies.get("access_token")
    assert access_token, "Expected access_token cookie to be set on register"
    cookie_header = {"Cookie": f"access_token={access_token}"}

    resp = client.get("/auth/session", headers=cookie_header)
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == email

    # Logout clears session (uses Bearer since /logout also accepts Authorization header)
    resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200, resp.text

    # Log back in with same account
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == email
    new_token = client.cookies.get("access_token")
    assert new_token, "Expected access_token cookie to be re-issued on login"

    resp = client.get("/auth/session", headers={"Cookie": f"access_token={new_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == email


def test_login_rejects_wrong_password(client):
    email = _unique_email()
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Tscheck User", "email": email, "password": password})
    assert resp.status_code == 200, resp.text

    resp = client.post("/auth/login", json={"email": email, "password": "WrongPassword1"})
    assert resp.status_code == 401, resp.text


def test_auth_me_endpoint_crashes_bug(client):
    """BUG: GET /auth/me returns 500 for any authenticated user.

    routers/auth.py `_public()` does `user.get("id", user["_id"])`; Python evaluates the
    default argument `user["_id"]` eagerly even when "id" is present, and the dict built by
    get_current_user() only has an "id" key (no "_id"), so this always raises KeyError.
    The frontend does not currently call /auth/me (it uses /auth/session), so this does not
    block the acceptance criterion, but the endpoint itself is broken for any caller.
    """
    email = _unique_email()
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Bug Check", "email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 500, "Expected the known 500 bug on /auth/me; if this now passes, the bug is fixed"


def test_duplicate_registration_rejected(client):
    email = _unique_email()
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Tscheck User", "email": email, "password": password})
    assert resp.status_code == 200

    resp = client.post("/auth/register", json={"name": "Tscheck User2", "email": email, "password": password})
    assert resp.status_code == 409, resp.text
