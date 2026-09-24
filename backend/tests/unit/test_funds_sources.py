"""The live fetchers, exercised against a mock transport: no network (spec sections 5.1, 5.2)."""

from datetime import date

import httpx
import pytest

from lib.funds import FundStore, build_default_store, fetch_amfi_catalog, fetch_mfapi_history

from .funds_fixtures import NAVALL_SAMPLE

MFAPI_PAYLOAD = {
    "meta": {"scheme_code": 100001},
    "data": [{"date": "23-09-2026", "nav": "150.10000"}, {"date": "22-09-2026", "nav": "149.90000"}],
    "status": "SUCCESS",
}


def client_for(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_the_amfi_file_is_downloaded_and_parsed():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["user_agent"] = request.headers["user-agent"]
        return httpx.Response(200, text=NAVALL_SAMPLE)

    async with client_for(handler) as client:
        entries = await fetch_amfi_catalog(client)
    assert seen["url"] == "https://www.amfiindia.com/spages/NAVAll.txt"
    assert "SurakshaCFO" in seen["user_agent"]
    assert {entry.scheme_code for entry in entries} == {"100001", "100005", "200002", "300001", "400001"}


async def test_an_amfi_error_response_raises():
    async with client_for(lambda request: httpx.Response(503)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_amfi_catalog(client)


async def test_mfapi_history_parses_day_month_year_dates_and_navs():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json=MFAPI_PAYLOAD)

    async with client_for(handler) as client:
        history = await fetch_mfapi_history(client, "100001")
    assert seen["url"] == "https://api.mfapi.in/mf/100001"
    assert history == [(date(2026, 9, 23), 150.1), (date(2026, 9, 22), 149.9)]


async def test_mfapi_is_retried_once_after_a_failure():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500) if len(calls) == 1 else httpx.Response(200, json=MFAPI_PAYLOAD)

    async with client_for(handler) as client:
        history = await fetch_mfapi_history(client, "100001")
    assert len(calls) == 2
    assert len(history) == 2


async def test_mfapi_gives_up_after_the_retry():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500)

    async with client_for(handler) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_mfapi_history(client, "100001")
    assert len(calls) == 2


@pytest.mark.parametrize(
    "payload, error",
    [
        ({"unexpected": 1}, KeyError),
        ({"data": [{"date": "2026-09-23", "nav": "1.0"}]}, ValueError),
        ({"data": [{"date": "23-09-2026", "nav": "N.A."}]}, ValueError),
    ],
)
async def test_a_malformed_mfapi_payload_raises_after_the_retry(payload, error):
    async with client_for(lambda request: httpx.Response(200, json=payload)) as client:
        with pytest.raises(error):
            await fetch_mfapi_history(client, "100001")


async def test_the_default_store_starts_warming_and_closes_its_http_client():
    store = build_default_store()
    assert isinstance(store, FundStore)
    assert store.status == "warming"
    await store.aclose()
