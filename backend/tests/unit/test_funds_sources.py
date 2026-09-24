"""The live fetchers, exercised against a mock transport: no network (spec sections 5.1, 5.2)."""

from datetime import date

import httpx
import pytest

from lib.funds import FundStore, _format_amfi_day, build_default_store, fetch_amfi_catalog, fetch_mfapi_history, fetch_nav_range, parse_nav_report

from .funds_fixtures import NAV_REPORT_SAMPLE, NAVALL_LIVE_CODES, NAVALL_SAMPLE

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
    assert {entry.scheme_code for entry in entries} == NAVALL_LIVE_CODES


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


START, END = date(2026, 9, 1), date(2026, 9, 7)


def test_a_dated_report_keeps_only_positive_navs_on_real_dates_ascending_per_scheme():
    report = parse_nav_report(NAV_REPORT_SAMPLE)
    assert set(report) == {"139619", "139617", "148921"}  # N.A., a zero NAV and an unparseable date are dropped
    assert report["148921"] == [(date(2026, 9, 15), 22.43), (date(2026, 9, 16), 22.51)]
    assert report["139619"] == [(date(2026, 9, 15), 10.0)]


def test_a_dated_report_parses_the_same_with_windows_line_endings_and_a_byte_order_mark():
    assert parse_nav_report("\N{ZERO WIDTH NO-BREAK SPACE}" + NAV_REPORT_SAMPLE.replace("\n", "\r\n")) == parse_nav_report(NAV_REPORT_SAMPLE)


def test_a_report_with_a_header_and_no_rows_is_an_empty_report_not_an_error():
    assert parse_nav_report("Scheme Code;NAV Name;Plan;Option;a;b;Net Asset Value;Date\r\n\r\n") == {}


@pytest.mark.parametrize("text", ["", "\n\n", "<!DOCTYPE html><html><body>Invalid date</body></html>", "\n\n<html>", "148921;name;;;;;22.43;15-Sep-2026"])
def test_a_response_that_is_not_the_report_raises(text):
    with pytest.raises(ValueError):
        parse_nav_report(text)


@pytest.mark.parametrize("day, text", [(date(2026, 3, 5), "05-Mar-2026"), (date(2013, 1, 1), "01-Jan-2013"), (date(2026, 12, 31), "31-Dec-2026")])
def test_dates_are_sent_in_amfis_form_with_english_month_names(day, text):
    assert _format_amfi_day(day) == text


async def test_a_range_is_downloaded_from_the_dated_report_endpoint_and_parsed():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["user_agent"] = request.headers["user-agent"]
        seen["timeout"] = request.extensions["timeout"]["read"]
        return httpx.Response(200, text=NAV_REPORT_SAMPLE)

    async with client_for(handler) as client:
        report = await fetch_nav_range(client, START, END)
    assert seen["url"] == "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt=01-Sep-2026&todt=07-Sep-2026"
    assert "SurakshaCFO" in seen["user_agent"] and seen["timeout"] == 120
    assert set(report) == {"139619", "139617", "148921"}


async def test_a_range_is_retried_once_after_a_failure():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500) if len(calls) == 1 else httpx.Response(200, text=NAV_REPORT_SAMPLE)

    async with client_for(handler) as client:
        report = await fetch_nav_range(client, START, END)
    assert len(calls) == 2 and "148921" in report


async def test_a_range_gives_up_after_the_retry():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500)

    async with client_for(handler) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_nav_range(client, START, END)
    assert len(calls) == 2


async def test_an_html_answer_is_retried_once_and_then_raises():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, text="<!DOCTYPE html><html>Invalid date</html>")

    async with client_for(handler) as client:
        with pytest.raises(ValueError):
            await fetch_nav_range(client, START, END)
    assert len(calls) == 2
