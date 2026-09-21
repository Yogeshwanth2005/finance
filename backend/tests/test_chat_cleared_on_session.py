"""Chat history must not outlive a session: it is wiped on logout, and a login always starts clean."""

import uuid

import httpx


def _register(client):
    email = f"tscheck-chatclear-{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Chat Clear", "email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return email, password


def _ask(client, question="Why do I need term insurance?"):
    resp = client.post("/chat/stream", json={"question": question})
    assert resp.status_code == 200, resp.text


def _history(client):
    resp = client.get("/chat/history")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_history_exists_during_the_session(client):
    _register(client)
    _ask(client)
    assert len(_history(client)) >= 2  # the question and the advisor's answer


def test_logout_clears_the_chat_and_next_login_is_clean(client):
    email, password = _register(client)
    _ask(client)
    assert _history(client)

    assert client.post("/auth/logout").status_code == 200

    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    assert _history(client) == []


def test_login_starts_clean_even_if_the_last_session_never_logged_out(client):
    email, password = _register(client)
    _ask(client)
    assert _history(client)

    # A second device signs in without the first ever logging out (e.g. the tab was just closed).
    with httpx.Client(base_url=client.base_url, timeout=30.0) as other:
        resp = other.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        assert _history(other) == []
