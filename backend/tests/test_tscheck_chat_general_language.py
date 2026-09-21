"""Criterion: a newly asked general term-insurance question returns the deterministic
profile-based explanation in the user's saved language (Hindi/Telugu/Tamil), and never
names a specific policy/provider."""

import uuid

LANGUAGE_MARKERS = {
    # a few characters unique to each script, used to confirm the response is actually
    # rendered in that language rather than falling back to English.
    "hi": "आपका",
    "te": "మీ",
    "ta": "உங்கள்",
}

FORBIDDEN_POLICY_NAMES = ("secure life shield", "retest family term policy")


def _unique_email(tag):
    return f"tscheck-genlang-{tag}-{uuid.uuid4().hex[:8]}@example.com"


def _register_and_set_language(client, language):
    email = _unique_email(language)
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Lang Tester", "email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.patch("/auth/settings", json={"preferred_language": language}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["preferred_language"] == language
    return headers


def _assert_general_answer_in_language(client, language):
    headers = _register_and_set_language(client, language)
    resp = client.post(
        "/chat/stream",
        json={"question": "Why do I need to take term insurance?"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    raw = resp.text
    lowered = raw.lower()
    assert LANGUAGE_MARKERS[language] in raw, f"Expected {language} script marker in response: {raw[:300]}"
    for name in FORBIDDEN_POLICY_NAMES:
        assert name not in lowered, f"Generic question must not name a policy, found '{name}'"


def test_general_question_answers_in_hindi(client):
    _assert_general_answer_in_language(client, "hi")


def test_general_question_answers_in_telugu(client):
    _assert_general_answer_in_language(client, "te")


def test_general_question_answers_in_tamil(client):
    _assert_general_answer_in_language(client, "ta")
