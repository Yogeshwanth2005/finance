import io
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.demo_user import get_or_create_demo_user
from app.models import User, InsuranceDocument, InsuranceDocumentChunk
from app.services.rag.rag import embed


def test_list_documents_empty():
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_or_create_demo_user] = lambda: User(id="user-1", email="demo-1@fin.local")

    client = TestClient(app)
    response = client.get("/api/insurance/rag/documents")
    assert response.status_code == 200
    assert response.json() == {"documents": []}
    app.dependency_overrides.clear()


def test_rag_chat_guardrail_refusal():
    fake_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_or_create_demo_user] = lambda: User(id="user-1", email="demo-1@fin.local")

    client = TestClient(app)
    # Comparison / recommendation queries must be hard-refused per Invariant 4
    response = client.post(
        "/api/insurance/rag/chat",
        json={"query": "Which insurance plan is better for me?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_refusal"] is True
    assert "do not compare" in body["answer"]
    assert body["sources"] == []
    app.dependency_overrides.clear()


def test_rag_chat_factual_retrieval():
    fake_db = MagicMock()

    doc = InsuranceDocument(
        id="doc-123",
        title="Optima Secure Policy Wording",
        filename="optima_secure.pdf",
        status="active",
    )
    chunk = InsuranceDocumentChunk(
        id="chunk-1",
        documentId="doc-123",
        chunkIndex=0,
        content="Pre-existing diseases are covered after a waiting period of 36 months.",
        embedding=embed("pre-existing diseases waiting period 36 months"),
    )

    query_mock = fake_db.query.return_value.join.return_value.filter.return_value
    query_mock.all.return_value = [(chunk, doc)]

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_or_create_demo_user] = lambda: User(id="user-1", email="demo-1@fin.local")

    client = TestClient(app)
    response = client.post(
        "/api/insurance/rag/chat",
        json={"query": "What is the waiting period for pre-existing diseases?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_refusal"] is False
    assert "waiting period" in body["answer"]
    assert len(body["sources"]) > 0
    assert body["sources"][0]["document_id"] == "doc-123"
    app.dependency_overrides.clear()


def test_rag_ingest_document():
    fake_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_or_create_demo_user] = lambda: User(id="user-1", email="demo-1@fin.local")

    client = TestClient(app)
    file_bytes = b"Section 4.1 Exclusions: Cosmetic surgery is not covered under this policy."
    response = client.post(
        "/api/insurance/rag/ingest",
        data={"title": "Test Policy Wording"},
        files={"file": ("policy.txt", io.BytesIO(file_bytes), "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["title"] == "Test Policy Wording"
    assert body["total_chunks"] >= 1
    app.dependency_overrides.clear()
