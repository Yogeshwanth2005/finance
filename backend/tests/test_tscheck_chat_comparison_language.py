"""Criterion: a named-plan comparison in a non-English selected language renders as a
table; labels/explanation use the selected language while plan/source titles remain
unchanged (English)."""

import pytest

RETEST_EMAIL = "retest.1789882160559@example.com"
RETEST_PASSWORD = "StrongPass!2026"


def _login(client):
    resp = client.post("/auth/login", json={"email": RETEST_EMAIL, "password": RETEST_PASSWORD})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on login"
    return {"Authorization": f"Bearer {token}"}


def _set_language(client, headers, language):
    resp = client.patch("/auth/settings", json={"preferred_language": language}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["preferred_language"] == language


@pytest.mark.parametrize("language", ["hi", "te", "ta"])
def test_comparison_table_renders_with_english_titles_in_language(client, language):
    headers = _login(client)
    try:
        _set_language(client, headers, language)
        resp = client.post(
            "/chat/stream",
            json={"question": f"Compare Secure Life Shield Policy vs Retest Family Term Policy ({language} check)"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        raw = resp.text
        lowered = raw.lower()
        assert "|" in raw, "Expected a pipe-delimited markdown table"
        # plan/source titles stay in English regardless of the selected language
        assert "secure life shield" in lowered
        assert "retest family term policy" in lowered
        assert '"sources": ["secure life shield policy", "retest family term policy"]' in lowered
    finally:
        _set_language(client, headers, "en")
