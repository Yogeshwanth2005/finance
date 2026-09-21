"""Criterion: password change requires the current password; a wrong current password is
rejected, and after a successful change the user can log in with the new password (and the
old password no longer works)."""

import uuid


def _unique_email():
    return f"tscheck-pwdchange-{uuid.uuid4().hex[:10]}@example.com"


def test_wrong_current_password_rejected_then_successful_change_allows_new_login(client):
    email = _unique_email()
    old_password = "TestPass!2026"
    new_password = "NewTestPass!2027"

    resp = client.post("/auth/register", json={"name": "Password Tester", "email": email, "password": old_password})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on register"
    headers = {"Authorization": f"Bearer {token}"}

    # Wrong current password must be rejected.
    resp = client.post(
        "/auth/change-password",
        json={"current_password": "TotallyWrongPassword1", "new_password": new_password},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text
    assert "incorrect" in resp.json()["detail"].lower()

    # Correct current password succeeds.
    resp = client.post(
        "/auth/change-password",
        json={"current_password": old_password, "new_password": new_password},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    # Old password no longer works.
    resp = client.post("/auth/login", json={"email": email, "password": old_password})
    assert resp.status_code == 401, resp.text

    # New password logs in successfully.
    resp = client.post("/auth/login", json={"email": email, "password": new_password})
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == email
