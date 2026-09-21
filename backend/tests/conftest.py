"""Pre-scaffolded pytest fixtures for the FastAPI backend.

Tests hit the live uvicorn process managed by supervisor (not an in-process ASGI app), so
the app under test is the same one the frontend and Playwright see. Do NOT re-create this
file — add app-specific fixtures below the marker at the bottom.
"""

import os

import httpx
import pytest
import pytest_asyncio

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
API_URL = f"{BACKEND_URL}/api"


def api_url(path: str = "") -> str:
    """Absolute URL for an /api route: api_url("/status") -> http://localhost:8001/api/status."""
    return f"{API_URL}{path}"


@pytest.fixture(scope="session")
def backend_url() -> str:
    return BACKEND_URL


@pytest.fixture
def client():
    """Sync httpx client rooted at /api — the default for endpoint tests.

    Example:
        def test_status(client):
            assert client.get("/status").status_code == 200
    """
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        yield c


@pytest_asyncio.fixture
async def aclient():
    """Async variant, for tests that also await motor/backend helpers directly."""
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as c:
        yield c


# --- app-specific fixtures below this line ---

# Several tests log in as this account and ask about these two plans; they were written against a
# database that already held them. Seed them (idempotently) so a fresh database passes too.
RETEST_EMAIL = "retest.1789882160559@example.com"
RETEST_PASSWORD = "StrongPass!2026"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@surakshacfo.demo")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "DemoAdmin!2026")
SEED_DOCUMENTS = {
    # Text is tuned so a "Compare Secure Life Shield ... vs Retest Family Term ..." query ranks Secure first
    # (tests assert that source order) and both carry ₹ values (grounded-language tests assert one is quoted).
    "Secure Life Shield Policy": "Secure Life Shield Policy: term life cover with a sum assured of ₹1 crore and annual premium from ₹12,000. Compare Secure Life Shield Policy with other policies.",
    "Retest Family Term Policy": "Retest Family Term Policy: family term life cover with a sum assured of ₹75 lakh and annual premium from ₹9,000, with an optional critical illness rider.",
}


@pytest.fixture(scope="session", autouse=True)
def seeded_retest_fixtures():
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        resp = c.post("/auth/register", json={"name": "Retest Family", "email": RETEST_EMAIL, "password": RETEST_PASSWORD})
        assert resp.status_code in (200, 409), resp.text  # 409: already registered

        resp = c.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert resp.status_code == 200, resp.text
        headers = {"Authorization": f"Bearer {c.cookies.get('access_token')}"}
        existing = {doc["title"] for doc in c.get("/admin/documents", headers=headers).json()}
        for title, text in SEED_DOCUMENTS.items():
            if title not in existing:
                resp = c.post(
                    "/admin/documents",
                    data={"title": title, "source_url": ""},
                    files={"file": (f"{title}.txt", text.encode(), "text/plain")},
                    headers=headers,
                )
                assert resp.status_code == 200, resp.text

        # xdist workers seed concurrently and can each upload a copy; keep the oldest per title.
        kept = set()
        for doc in sorted(c.get("/admin/documents", headers=headers).json(), key=lambda d: (d["created_at"], d["id"])):
            if doc["title"] not in SEED_DOCUMENTS:
                continue
            if doc["title"] in kept:
                c.delete(f"/admin/documents/{doc['id']}", headers=headers)  # 404 if the other worker already did
            kept.add(doc["title"])
