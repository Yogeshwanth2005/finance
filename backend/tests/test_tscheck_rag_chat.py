"""Criterion: RAG chatbot answers from indexed documents with citations, and does not
invent an answer when no relevant source exists."""

import io
import uuid

ADMIN_EMAIL = "admin@surakshacfo.demo"
ADMIN_PASSWORD = "DemoAdmin!2026"


def test_chat_answers_with_citation_from_indexed_document(client):
    # Index a distinctive document as admin
    resp = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    admin_token = client.cookies.get("access_token")
    assert admin_token, "Expected access_token cookie on admin login"
    admin_header = {"Authorization": f"Bearer {admin_token}"}

    unique_term = f"Zephyrion{uuid.uuid4().hex[:6]}"
    title = f"tscheck-chat-doc-{uuid.uuid4().hex[:8]}"
    content = (
        f"The {unique_term} Term Shield policy offers a claim settlement ratio of 99% and covers "
        "accidental death, critical illness riders, and a terminal illness benefit for policyholders."
    ).encode()
    resp = client.post(
        "/admin/documents",
        data={"title": title, "source_url": ""},
        files={"file": ("tscheck_chat.txt", io.BytesIO(content), "text/plain")},
        headers=admin_header,
    )
    assert resp.status_code == 200, resp.text

    # New regular user asks a document-specific question
    email = f"tscheck-chatuser-{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Chat Tester", "email": email, "password": password})
    assert resp.status_code == 200, resp.text
    user_token = client.cookies.get("access_token")
    assert user_token, "Expected access_token cookie on register"
    user_header = {"Authorization": f"Bearer {user_token}"}

    # Retrieval is title-gated (see test_tscheck_plan_specific_retrieval_gating): the question must name the
    # document. Old test docs share title words, so also include the unique term to rank this doc's chunk first.
    resp = client.post(
        "/chat/stream",
        json={"question": f"What does the {title} policy say about the {unique_term} Term Shield?"},
        headers=user_header,
    )
    assert resp.status_code == 200, resp.text
    raw = resp.text
    assert "data:" in raw
    # sources should mention our indexed document title in the final "done" event
    assert title in raw or unique_term.lower() in raw.lower()


def test_chat_does_not_invent_when_no_source(client):
    email = f"tscheck-chatuser2-{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Chat Tester 2", "email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on register"
    auth_header = {"Authorization": f"Bearer {token}"}

    nonsense = f"Qxzplorf{uuid.uuid4().hex[:8]}nonexistentpolicycoverage"
    resp = client.post(
        "/chat/stream",
        json={"question": f"Tell me about {nonsense} policy benefits"},
        headers=auth_header,
    )
    assert resp.status_code == 200, resp.text
    raw = resp.text
    assert "data:" in raw
    # A question that names no indexed document is answered from the profile only: no document is cited
    # and nothing is said about the unknown policy.
    assert '"sources": ["your financial profile"]' in raw.lower()
    assert nonsense.lower() not in raw.lower()
