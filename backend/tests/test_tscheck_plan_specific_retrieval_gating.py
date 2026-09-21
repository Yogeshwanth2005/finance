"""Criterion: plan-specific retrieval requires explicit plan/provider intent.

A general protection/critical-illness question must NOT retrieve a policy document
(sources stay profile-only), while a question naming an indexed plan retrieves and
cites that plan's active document.
"""

RETEST_EMAIL = "retest.1789882160559@example.com"
RETEST_PASSWORD = "StrongPass!2026"


def _login(client):
    resp = client.post("/auth/login", json={"email": RETEST_EMAIL, "password": RETEST_PASSWORD})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on login"
    return {"Authorization": f"Bearer {token}"}


def test_general_protection_question_does_not_retrieve_a_document(client):
    headers = _login(client)
    resp = client.post(
        "/chat/stream",
        json={"question": "Should I add critical illness cover to my protection plan?"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    raw = resp.text
    assert "data:" in raw
    lowered = raw.lower()
    assert "secure life shield" not in lowered
    assert "retest family term policy" not in lowered
    assert '"sources": ["your financial profile"]' in lowered


def test_named_plan_question_retrieves_active_indexed_document(client):
    headers = _login(client)
    resp = client.post(
        "/chat/stream",
        json={"question": "What does the Secure Life Shield Policy cover?"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    raw = resp.text
    assert "data:" in raw
    lowered = raw.lower()
    assert "secure life shield" in lowered
    assert '"sources": ["secure life shield policy"]' in lowered
