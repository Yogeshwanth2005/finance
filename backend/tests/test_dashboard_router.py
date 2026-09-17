from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.demo_user import get_or_create_demo_user
from app.models import User


def _fake_gap_result():
    r = MagicMock()
    r.emergencyFundCoveragePct = 75
    r.emergencyFundStatus = "building"
    r.emergencyFundTarget = 240000
    r.emergencyFundCurrent = 180000
    r.termCoverAdequacyPct = 33.33
    r.termCoverGap = 4000000
    r.healthCoverAdequacyPct = 60
    r.healthCoverGap = 200000
    r.savingsRatePct = 20
    r.debtToIncomePct = 17.77
    return r


def _fake_allocation_result():
    r = MagicMock()
    r.equityPct = 70
    r.debtPct = 20
    r.goldPct = 10
    return r


def test_dashboard_returns_404_when_no_results_yet():
    fake_db = MagicMock()
    fake_db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = None
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_or_create_demo_user] = lambda: User(id="user-1", email="demo-1@fin.local")

    response = TestClient(app).get("/api/dashboard")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_dashboard_returns_kpis_and_allocation_when_results_exist():
    fake_db = MagicMock()
    query_mock = fake_db.query.return_value
    query_mock.filter_by.return_value.order_by.return_value.first.side_effect = [
        _fake_gap_result(), _fake_allocation_result(),
    ]
    query_mock.all.return_value = []

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_or_create_demo_user] = lambda: User(id="user-1", email="demo-1@fin.local")

    response = TestClient(app).get("/api/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["kpis"]["emergency_fund_coverage_pct"] == 75
    assert body["allocation"]["equity_pct"] == 70
    app.dependency_overrides.clear()
