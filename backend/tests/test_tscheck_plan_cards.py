"""Criterion: plan cards are drafted from documents, reviewed by an admin, and only published cards
from active documents reach customers.

Works with or without GROQ_API_KEY on the server: the test sets the card itself, so it does not
depend on AI extraction (which only pre-fills a draft).
"""

import io
import uuid

ADMIN_EMAIL = "admin@surakshacfo.demo"
ADMIN_PASSWORD = "DemoAdmin!2026"


def _card(name):
    return {
        "category": "term",
        "name": name,
        "provider": "Test Insurer",
        "csr": "98.5%",
        "annual_premium_from": 12000,
        "cover_label": "Term cover ₹1 crore",
        "highlights": ["Flexible payout", "Optional riders"],
        "fit": "Best for income replacement",
        "details": {"eligibility": "Age 18-60", "exclusions": "Suicide in first 12 months"},
    }


def _admin_headers(client):
    resp = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {client.cookies.get('access_token')}"}


def _user_headers(client):
    email = f"tscheck-plancards-{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post("/auth/register", json={"name": "Plan Viewer", "email": email, "password": "TestPass!2026"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {client.cookies.get('access_token')}"}


def _upload(client, admin, title):
    text = f"{title} is a term life plan with a sum assured of ₹1 crore.".encode()
    resp = client.post(
        "/admin/documents",
        data={"title": title, "source_url": ""},
        files={"file": ("plan.txt", io.BytesIO(text), "text/plain")},
        headers=admin,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _published_ids(client, headers):
    resp = client.get("/plans", headers=headers)
    assert resp.status_code == 200, resp.text
    return {plan["id"]: plan for plan in resp.json()}


def test_plans_endpoint_requires_login(client):
    client.cookies.clear()
    assert client.get("/plans").status_code == 401


def test_draft_review_publish_pause_and_unpublish_flow(client):
    admin = _admin_headers(client)
    title = f"tscheck-plancard-{uuid.uuid4().hex[:8]}"
    document = _upload(client, admin, title)
    document_id = document["id"]
    name = f"Tscheck Plan {uuid.uuid4().hex[:6]}"
    try:
        user = _user_headers(client)

        # A customer cannot edit or publish cards.
        assert client.put(f"/admin/documents/{document_id}/plan", json=_card(name), headers=user).status_code == 403
        assert client.patch(f"/admin/documents/{document_id}/plan/status", json={"status": "published"}, headers=user).status_code == 403

        # Nothing to publish until the plan details exist (they may not if AI extraction is off).
        admin = _admin_headers(client)
        if document["plan"] is None:
            resp = client.patch(f"/admin/documents/{document_id}/plan/status", json={"status": "published"}, headers=admin)
            assert resp.status_code == 409, resp.text

        # Admin reviews: saving the card keeps it a draft, invisible to customers.
        resp = client.put(f"/admin/documents/{document_id}/plan", json=_card(name), headers=admin)
        assert resp.status_code == 200, resp.text
        assert resp.json()["plan"]["name"] == name
        assert resp.json()["plan_status"] == "draft"
        user = _user_headers(client)
        assert document_id not in _published_ids(client, user)

        # Publishing shows it, with the details and the source document title for the chat.
        admin = _admin_headers(client)
        resp = client.patch(f"/admin/documents/{document_id}/plan/status", json={"status": "published"}, headers=admin)
        assert resp.status_code == 200, resp.text
        assert resp.json()["plan_status"] == "published"
        user = _user_headers(client)
        published = _published_ids(client, user)[document_id]
        assert published["name"] == name
        assert published["source_title"] == title
        assert published["details"]["eligibility"] == "Age 18-60"
        assert published["details"]["riders"] == "Not stated in the document"

        # A paused document's card disappears, and returns when reactivated.
        admin = _admin_headers(client)
        client.patch(f"/admin/documents/{document_id}/status", json={"enabled": False}, headers=admin)
        user = _user_headers(client)
        assert document_id not in _published_ids(client, user)
        admin = _admin_headers(client)
        client.patch(f"/admin/documents/{document_id}/status", json={"enabled": True}, headers=admin)
        user = _user_headers(client)
        assert document_id in _published_ids(client, user)

        # Unpublishing hides it again.
        admin = _admin_headers(client)
        client.patch(f"/admin/documents/{document_id}/plan/status", json={"status": "draft"}, headers=admin)
        user = _user_headers(client)
        assert document_id not in _published_ids(client, user)
    finally:
        client.delete(f"/admin/documents/{document_id}", headers=_admin_headers(client))


def test_invalid_card_is_rejected(client):
    admin = _admin_headers(client)
    document_id = _upload(client, admin, f"tscheck-plancard-invalid-{uuid.uuid4().hex[:8]}")["id"]
    try:
        bad_category = {**_card("Bad Category"), "category": "ulip"}
        assert client.put(f"/admin/documents/{document_id}/plan", json=bad_category, headers=admin).status_code == 422
        bad_premium = {**_card("Bad Premium"), "annual_premium_from": -1}
        assert client.put(f"/admin/documents/{document_id}/plan", json=bad_premium, headers=admin).status_code == 422
    finally:
        client.delete(f"/admin/documents/{document_id}", headers=admin)
