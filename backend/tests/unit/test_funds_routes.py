"""GET /api/funds/top and /api/funds/search: window handling, query validation, status passthrough, auth (spec section 5.4)."""

import asyncio
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.auth import get_current_user
from lib.funds import CatalogEntry, FundStore
from routers.funds import get_fund_store, router

END = date(2026, 9, 23)
SEGMENT_KEYS = ["nifty", "large", "mid", "small"]


def growth(annual_pct, years=4):
    days = round(years * 365.25)
    return [(END - timedelta(days=offset), 100 * (1 + annual_pct / 100) ** (-offset / 365.25)) for offset in range(days, -1, -1)]


def loaded_store():
    entries = [
        CatalogEntry("1", "Alpha Slow Large", "Alpha Mutual Fund", "large", 10.0, END),
        CatalogEntry("2", "Alpha Fast Large", "Alpha Mutual Fund", "large", 10.0, END),
        CatalogEntry("3", "Beta Mid", "Beta Mutual Fund", "mid", 10.0, END),
        CatalogEntry("4", "Beta Small", "Beta Mutual Fund", "small", 10.0, END),
        CatalogEntry("5", "Alpha Nifty 50 Index", "Alpha Mutual Fund", "nifty", 10.0, END),
    ]
    rates = {"1": 9.0, "2": 15.0, "3": 12.0, "4": 14.0, "5": 11.0}

    async def fetch_catalog():
        return entries

    async def fetch_history(code):
        return growth(rates[code])

    store = FundStore(fetch_catalog, fetch_history)
    asyncio.run(store.refresh())
    return store


class StubStore:
    """A store in a fixed state that records how often it was asked to stay fresh."""

    def __init__(self, status="warming"):
        self.status = status
        self.as_of = None
        self.failed_count = 0
        self.fresh_calls = 0

    def ensure_fresh(self):
        self.fresh_calls += 1

    def top(self, window):
        return {key: [] for key in SEGMENT_KEYS}

    def search(self, query, window):
        return [], {key: [] for key in SEGMENT_KEYS}


def client_for(store, signed_in=True):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_fund_store] = lambda: store
    if signed_in:
        app.dependency_overrides[get_current_user] = lambda: {"id": "user-1"}
    return TestClient(app)


@pytest.fixture(scope="module")
def client():
    return client_for(loaded_store())


def names(rows):
    return [row["name"] for row in rows]


def test_top_defaults_to_the_three_year_window_and_ranks_each_segment(client):
    body = client.get("/api/funds/top").json()
    assert (body["status"], body["window"], body["as_of"], body["failed_count"]) == ("ready", "3y", "2026-09-23", 0)
    assert list(body["segments"]) == SEGMENT_KEYS
    assert names(body["segments"]["large"]) == ["Alpha Fast Large", "Alpha Slow Large"]
    assert names(body["segments"]["mid"]) == ["Beta Mid"]
    assert names(body["segments"]["nifty"]) == ["Alpha Nifty 50 Index"]


def test_a_fund_row_carries_everything_the_dashboard_shows(client):
    fund = client.get("/api/funds/top").json()["segments"]["small"][0]
    assert set(fund) == {"scheme_code", "name", "fund_house", "segment", "nav", "nav_date", "start_date", "returns", "max_is_annualised"}
    assert set(fund["returns"]) == {"1y", "3y", "5y", "max"}
    assert fund["returns"]["3y"] == pytest.approx(14.0, abs=0.05)
    assert fund["start_date"] == str(END - timedelta(days=round(4 * 365.25)))


@pytest.mark.parametrize("window, large_count", [("1y", 2), ("3y", 2), ("5y", 0), ("max", 2)])
def test_each_window_ranks_only_the_funds_that_have_it(client, window, large_count):
    body = client.get(f"/api/funds/top?window={window}").json()
    assert body["window"] == window
    assert len(body["segments"]["large"]) == large_count  # the fixture funds are four years old: no 5y


@pytest.mark.parametrize("query", ["window=2y", "window=", "window=3Y", "window=all"])
def test_an_unknown_window_is_rejected(client, query):
    assert client.get(f"/api/funds/top?{query}").status_code == 422
    assert client.get(f"/api/funds/search?q=alpha&{query}").status_code == 422


def test_search_groups_a_fund_houses_funds_by_segment(client):
    body = client.get("/api/funds/search?q=alpha").json()
    assert (body["status"], body["query"], body["fund_houses"]) == ("ready", "alpha", ["Alpha Mutual Fund"])
    assert body["failed_count"] == 0
    assert names(body["groups"]["large"]) == ["Alpha Fast Large", "Alpha Slow Large"]
    assert names(body["groups"]["nifty"]) == ["Alpha Nifty 50 Index"]
    assert body["groups"]["mid"] == [] and body["groups"]["small"] == []


def test_search_ranks_by_the_requested_window(client):
    body = client.get("/api/funds/search?q=mutual&window=max").json()
    assert body["fund_houses"] == ["Alpha Mutual Fund", "Beta Mutual Fund"]
    assert names(body["groups"]["large"]) == ["Alpha Fast Large", "Alpha Slow Large"]


def test_the_query_is_trimmed_in_the_response(client):
    assert client.get("/api/funds/search?q=%20alpha%20").json()["query"] == "alpha"


@pytest.mark.parametrize("query", ["", "a", "a" * 61, "%20%20", "%20%20%20%20"])
def test_a_query_outside_two_to_sixty_characters_is_rejected_including_blank_ones(client, query):
    assert client.get(f"/api/funds/search?q={query}").status_code == 422


def test_a_missing_query_is_rejected(client):
    assert client.get("/api/funds/search").status_code == 422


@pytest.mark.parametrize("query", ["zzzz", "(*", "%25%25", "..", "hdfc%25"])
def test_a_query_that_matches_nothing_or_looks_like_a_pattern_is_an_empty_result_not_an_error(client, query):
    response = client.get(f"/api/funds/search?q={query}")
    assert response.status_code == 200
    body = response.json()
    assert body["fund_houses"] == []
    assert all(rows == [] for rows in body["groups"].values())


@pytest.mark.parametrize("status", ["warming", "stale", "unavailable"])
def test_the_stores_status_reaches_the_response_with_empty_lists(status):
    stub = StubStore(status)
    client = client_for(stub)
    top = client.get("/api/funds/top").json()
    assert (top["status"], top["as_of"]) == (status, None)
    assert all(rows == [] for rows in top["segments"].values())
    assert client.get("/api/funds/search?q=alpha").json()["status"] == status


def test_every_request_asks_the_store_to_stay_fresh():
    stub = StubStore("ready")
    client = client_for(stub)
    client.get("/api/funds/top")
    client.get("/api/funds/search?q=alpha")
    client.get("/api/funds/search?q=a")  # rejected before it reaches the store
    assert stub.fresh_calls == 2


@pytest.mark.parametrize("path", ["/api/funds/top", "/api/funds/search?q=alpha"])
def test_a_signed_out_request_is_refused(path):
    assert client_for(StubStore("ready"), signed_in=False).get(path).status_code == 401
