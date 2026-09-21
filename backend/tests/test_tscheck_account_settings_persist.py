"""Criterion: Account settings (display name, preferred language, notification and
privacy preferences) persist per account and remain after re-fetching the session."""

import uuid


def _unique_email():
    return f"tscheck-settings-{uuid.uuid4().hex[:10]}@example.com"


def test_settings_persist_across_session_refetch(client):
    email = _unique_email()
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Settings Tester", "email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on register"
    headers = {"Authorization": f"Bearer {token}"}

    new_name = f"Tscheck Renamed {uuid.uuid4().hex[:6]}"
    resp = client.patch(
        "/auth/settings",
        json={
            "name": new_name,
            "preferred_language": "hi",
            "notifications_enabled": False,
            "privacy_mode": False,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == new_name
    assert body["preferred_language"] == "hi"
    assert body["notifications_enabled"] is False
    assert body["privacy_mode"] is False

    # Re-fetch the session (simulates page reload) and confirm values persisted server-side.
    # /auth/session reads the cookie directly (not the Authorization header), matching the
    # browser's reload behavior.
    resp = client.get("/auth/session", headers={"Cookie": f"access_token={token}"})
    assert resp.status_code == 200, resp.text
    refetched = resp.json()
    assert refetched["name"] == new_name
    assert refetched["preferred_language"] == "hi"
    assert refetched["notifications_enabled"] is False
    assert refetched["privacy_mode"] is False


def test_settings_update_rejects_unauthenticated(client):
    resp = client.patch("/auth/settings", json={"name": "No Auth"})
    assert resp.status_code in (401, 403), resp.text
