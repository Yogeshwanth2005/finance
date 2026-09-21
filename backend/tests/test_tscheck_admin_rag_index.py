"""Criterion: Admin can build the RAG knowledge base (index TXT, list documents); non-admin blocked."""

import io
import uuid

ADMIN_EMAIL = "admin@surakshacfo.demo"
ADMIN_PASSWORD = "DemoAdmin!2026"


def test_admin_can_index_txt_and_list_it(client):
    resp = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "admin"
    # Secure cookies require https; test client hits plain http, so authenticate via Bearer header.
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on admin login"
    auth_header = {"Authorization": f"Bearer {token}"}

    title = f"tscheck-doc-{uuid.uuid4().hex[:8]}"
    file_content = b"This is a demo insurance policy document used for automated testing of RAG indexing."
    resp = client.post(
        "/admin/documents",
        data={"title": title, "source_url": ""},
        files={"file": ("tscheck.txt", io.BytesIO(file_content), "text/plain")},
        headers=auth_header,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == title
    assert body["status"] == "indexed"
    assert body["chunk_count"] >= 1

    resp = client.get("/admin/documents", headers=auth_header)
    assert resp.status_code == 200, resp.text
    titles = [d["title"] for d in resp.json()]
    assert title in titles


def test_non_admin_cannot_access_documents(client):
    email = f"tscheck-nonadmin-{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass!2026"
    resp = client.post("/auth/register", json={"name": "Regular User", "email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = client.cookies.get("access_token")
    assert token, "Expected access_token cookie on register"
    auth_header = {"Authorization": f"Bearer {token}"}

    resp = client.get("/admin/documents", headers=auth_header)
    assert resp.status_code in (401, 403), resp.text

    resp = client.post("/admin/documents", data={"title": "x", "source_url": "http://example.com"}, headers=auth_header)
    assert resp.status_code in (401, 403), resp.text
