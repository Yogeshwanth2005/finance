from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.demo_user import get_or_create_demo_user
from app.models import User

VALID_PAYLOAD = {
    "age": 30,
    "dependentsCount": 1,
    "riskTolerance": "moderate",
    "investmentHorizonYears": 10,
    "monthlyIncome": 50000,
    "monthlyExpenses": 40000,
    "currentSavings": 180000,
    "debts": [
        {"label": "Credit card", "outstandingAmount": 100000, "interestRatePct": 12, "tenureMonths": 12},
    ],
    "existingTermCoverAmount": 2000000,
    "personalHealthCoverAmount": 200000,
    "employerHealthCoverAmount": 100000,
}


def _override_dependencies():
    fake_db = MagicMock()
    fake_db.query.return_value.filter_by.return_value.first.return_value = None
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_or_create_demo_user] = lambda: User(id="user-1", email="demo-1@fin.local")
    return fake_db


def test_submit_onboarding_returns_success():
    fake_db = _override_dependencies()
    client = TestClient(app)

    response = client.post("/api/onboarding/submit", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert fake_db.commit.call_count == 2
    app.dependency_overrides.clear()


def test_submit_onboarding_rejects_missing_required_field():
    _override_dependencies()
    client = TestClient(app)

    bad_payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "monthlyIncome"}
    response = client.post("/api/onboarding/submit", json=bad_payload)

    assert response.status_code == 422
    app.dependency_overrides.clear()
