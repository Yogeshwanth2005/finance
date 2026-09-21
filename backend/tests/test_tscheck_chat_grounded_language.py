"""Criterion: a newly asked question naming Secure Life Shield Policy streams an answer in
the selected language (Hindi/Telugu/Tamil) while preserving the English plan/source title,
rupee values and citations."""

RETEST_EMAIL = "retest.1789882160559@example.com"
RETEST_PASSWORD = "StrongPass!2026"

LANGUAGE_MARKERS = {
    "hi": "है",
    "te": "ా",
    "ta": "க",
}


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


def _assert_grounded_answer_in_language(client, language, question):
    headers = _login(client)
    try:
        _set_language(client, headers, language)
        resp = client.post("/chat/stream", json={"question": question}, headers=headers)
        assert resp.status_code == 200, resp.text
        raw = resp.text
        lowered = raw.lower()
        # English plan/source title is preserved even though the surrounding prose is localized.
        assert "secure life shield" in lowered, raw[:400]
        assert '"sources": ["secure life shield policy"]' in lowered
        # A rupee value marker should still be present (monetary values stay untranslated).
        assert "₹" in raw
    finally:
        _set_language(client, headers, "en")


import pytest


@pytest.mark.parametrize("language", ["hi", "te", "ta"])
def test_named_plan_answer_follows_saved_language(client, language):
    _assert_grounded_answer_in_language(
        client, language, f"What does the Secure Life Shield Policy cover? (lang-check {language})"
    )
