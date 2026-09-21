"""Criterion: generic term-insurance questions stay general and profile-based; they must
not name any specific plan/provider and must cite only 'Your financial profile'."""

RETEST_EMAIL = "retest.1789882160559@example.com"
RETEST_PASSWORD = "StrongPass!2026"

FORBIDDEN_TERMS = [
    "secure life shield",
    "hdfc",
    "retest family term policy",
]


def test_generic_term_insurance_question_is_profile_only(client):
    resp = client.post("/auth/login", json={"email": RETEST_EMAIL, "password": RETEST_PASSWORD})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on login"
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/chat/stream",
        json={"question": "Why do I need to take term insurance?"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    raw = resp.text
    assert "data:" in raw
    lowered = raw.lower()

    for term in FORBIDDEN_TERMS:
        assert term not in lowered, f"Generic profile-based answer must not name '{term}': {raw[:800]}"

    # the "done" event should cite only the profile, not any document title
    assert '"sources": ["your financial profile"]' in lowered or "your financial profile" in lowered
    assert "dependent" in lowered or "income" in lowered or "gap" in lowered
