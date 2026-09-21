"""Criterion: explicit plan comparisons render as a markdown table with both plan names,
'Not stated in indexed documents' for missing facts, and cited source titles for both plans."""

RETEST_EMAIL = "retest.1789882160559@example.com"
RETEST_PASSWORD = "StrongPass!2026"


def test_compare_two_named_plans_returns_table_with_both_sources(client):
    resp = client.post("/auth/login", json={"email": RETEST_EMAIL, "password": RETEST_PASSWORD})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on login"
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/chat/stream",
        json={"question": "Compare Secure Life Shield Policy vs Retest Family Term Policy"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    raw = resp.text
    assert "data:" in raw
    lowered = raw.lower()

    # markdown table rows (pipe-delimited) present
    assert "|" in raw

    assert "secure life shield" in lowered
    assert "retest family term policy" in lowered
    assert "not stated in indexed documents" in lowered

    # both plan sources cited in the terminal "done" event
    assert '"sources": ["secure life shield policy", "retest family term policy"]' in lowered
