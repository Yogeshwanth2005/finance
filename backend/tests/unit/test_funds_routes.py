"""GET /api/funds/top and /api/funds/search: response shapes, window handling, query validation, status passthrough, auth (spec section 5.4)."""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.auth import get_current_user
from routers.funds import get_fund_store, router

from .fund_store_fakes import make_store
from .stored_fund_fixtures import unresolved, stored

SEGMENT_KEYS = ["nifty", "large", "mid", "small"]


def returns(**values):
    return {"1y": None, "3y": None, "5y": None, "max": None, **values}


def loaded_store(*extra):
    funds = [
        stored("1", name="Alpha Slow Large", returns=returns(**{"3y": 9.0, "max": 9.5})),
        stored("2", name="Alpha Fast Large", returns=returns(**{"3y": 15.0, "max": 15.5})),
        stored("3", name="Beta Mid", fund_house="Beta Mutual Fund", segment="mid", category="Mid Cap Fund", returns=returns(**{"3y": 12.0})),
        stored("4", name="Beta Small", fund_house="Beta Mutual Fund", segment="small", category="Small Cap Fund", returns=returns(**{"3y": 14.0})),
        stored("5", name="Alpha Nifty 50 Index", segment="nifty", category="Index Funds", returns=returns(**{"3y": 11.0})),
        stored("6", name="Alpha Liquid", segment=None, category="Liquid Fund", returns=returns()),
        *extra,
    ]
    store, amfi, *_ = make_store(seeded=funds)
    amfi.range_fails_after = 0  # a fund without a first NAV starts the background pass on a request: keep it from ever finding one
    asyncio.run(store.load())
    return store


class StubStore:
    """A store in a fixed state that records how often it was asked to stay fresh."""

    def __init__(self, status="warming"):
        self.status = status
        self.as_of = None
        self.max_pending = False
        self.fresh_calls = 0

    def ensure_fresh(self):
        self.fresh_calls += 1

    def top(self, window):
        return {key: [] for key in SEGMENT_KEYS}

    def search(self, query, window):
        return [], []


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
    assert (body["status"], body["window"], body["as_of"], body["max_pending"]) == ("ready", "3y", "2026-09-23", False)
    assert list(body["segments"]) == SEGMENT_KEYS
    assert names(body["segments"]["large"]) == ["Alpha Fast Large", "Alpha Slow Large"]
    assert names(body["segments"]["mid"]) == ["Beta Mid"] and names(body["segments"]["nifty"]) == ["Alpha Nifty 50 Index"]
    assert "failed_count" not in body


def test_a_fund_row_carries_everything_the_dashboard_shows_and_nothing_internal(client):
    fund = client.get("/api/funds/top").json()["segments"]["small"][0]
    assert set(fund) == {"scheme_code", "name", "fund_house", "category", "segment", "nav", "nav_date", "start_date", "returns", "max_is_annualised"}
    assert (fund["category"], fund["start_date"], fund["returns"]["3y"]) == ("Small Cap Fund", "2013-01-01", 14.0)
    assert set(fund["returns"]) == {"1y", "3y", "5y", "max"}


@pytest.mark.parametrize("window, large_count", [("1y", 0), ("3y", 2), ("5y", 0), ("max", 2)])
def test_each_window_ranks_only_the_funds_that_have_it(client, window, large_count):
    body = client.get(f"/api/funds/top?window={window}").json()
    assert body["window"] == window and len(body["segments"]["large"]) == large_count


def test_max_pending_is_true_while_a_first_nav_is_missing():
    client = client_for(loaded_store(unresolved("9", name="Gamma")))
    assert client.get("/api/funds/top").json()["max_pending"] is True
    assert client.get("/api/funds/search?q=alpha").json()["max_pending"] is True


def test_a_fund_with_no_first_nav_yet_has_null_start_date_and_max():
    client = client_for(loaded_store(unresolved("9", name="Gamma Large")))
    large = client.get("/api/funds/search?q=alpha").json()["sections"][1]["funds"]  # nifty comes first, then large
    fund = next(row for row in large if row["name"] == "Gamma Large")
    assert (fund["start_date"], fund["max_is_annualised"], fund["returns"]["max"]) == (None, None, None)


@pytest.mark.parametrize("query", ["window=2y", "window=", "window=3Y", "window=all"])
def test_an_unknown_window_is_rejected(client, query):
    assert client.get(f"/api/funds/top?{query}").status_code == 422
    assert client.get(f"/api/funds/search?q=alpha&{query}").status_code == 422


def test_search_returns_the_matching_houses_and_ordered_sections(client):
    body = client.get("/api/funds/search?q=alpha").json()
    assert (body["status"], body["query"], body["fund_houses"], body["max_pending"]) == ("ready", "alpha", ["Alpha Mutual Fund"], False)
    assert "groups" not in body and "failed_count" not in body
    assert [(section["key"], section["title"]) for section in body["sections"]] == [
        ("nifty", "Nifty 50 index"), ("large", "Large cap"), ("cat-liquid-fund", "Liquid Fund"),
    ]
    large = body["sections"][1]["funds"]
    assert names(large) == ["Alpha Fast Large", "Alpha Slow Large"]


def test_search_lists_a_fund_without_a_value_for_the_window_after_the_ranked_ones(client):
    liquid = client.get("/api/funds/search?q=alpha&window=3y").json()["sections"][2]["funds"]
    assert names(liquid) == ["Alpha Liquid"] and liquid[0]["returns"]["3y"] is None


def test_search_ranks_by_the_requested_window(client):
    body = client.get("/api/funds/search?q=mutual&window=max").json()
    assert body["fund_houses"] == ["Alpha Mutual Fund", "Beta Mutual Fund"]
    assert names(next(section for section in body["sections"] if section["key"] == "large")["funds"]) == ["Alpha Fast Large", "Alpha Slow Large"]


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
    assert body["fund_houses"] == [] and body["sections"] == []


@pytest.mark.parametrize("status", ["warming", "stale", "unavailable"])
def test_the_stores_status_reaches_the_response_with_empty_lists(status):
    client = client_for(StubStore(status))
    top = client.get("/api/funds/top").json()
    assert (top["status"], top["as_of"]) == (status, None)
    assert all(rows == [] for rows in top["segments"].values())
    search = client.get("/api/funds/search?q=alpha").json()
    assert (search["status"], search["sections"]) == (status, [])


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
