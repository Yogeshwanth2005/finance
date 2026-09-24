"""parse_navall turns AMFI's NAVAll.txt into the Direct + Growth catalog of every live scheme, tagging the four equity segments (spec section 5.1)."""

import pytest

from lib.funds import _category_label, _segment, parse_navall

from .funds_fixtures import NAVALL_LIVE_CODES, NAVALL_SAMPLE

INDEX_CATEGORY = "Open Ended Schemes(Other Scheme - Index Funds)"


def by_code(text=NAVALL_SAMPLE):
    return {entry.scheme_code: entry for entry in parse_navall(text)}


def test_keeps_every_live_direct_growth_scheme_whatever_its_category():
    assert set(by_code()) == NAVALL_LIVE_CODES


def test_the_four_equity_segments_are_tagged_and_every_other_scheme_has_none():
    assert {code: entry.segment for code, entry in by_code().items()} == {
        "100001": "large", "100005": "large", "100010": None, "200002": "mid", "300001": "small",
        "400001": "nifty", "400002": None, "400003": None, "400004": None, "400005": None, "400006": None, "500001": None,
    }


def test_regular_plans_and_idcw_options_are_left_out():
    assert "100002" not in by_code() and "100003" not in by_code()


def test_large_and_mid_cap_is_kept_but_is_neither_a_large_nor_a_mid_fund():
    entry = by_code()["100010"]
    assert entry.segment is None and entry.category == "Large & Mid Cap Fund"


def test_a_scheme_whose_nav_is_stale_against_the_file_is_dropped():
    assert "100004" not in by_code()  # last NAV 01-Jun-2026, the file's newest is 23-Sep-2026


def test_a_nav_a_few_days_behind_the_newest_is_still_live():
    assert "200002" in by_code()  # 22-Sep-2026


def test_a_row_without_a_numeric_nav_is_skipped():
    assert "200001" not in by_code()


def test_close_ended_schemes_are_kept_under_their_own_label():
    assert by_code()["500001"].category == "Growth"


def test_a_row_carries_the_label_of_the_category_line_above_it():
    found = by_code()
    assert [found[code].category for code in ("100001", "200002", "300001", "400001")] == ["Large Cap Fund", "Mid Cap Fund", "Small Cap Fund", "Index Funds"]


def test_fund_house_is_the_most_recent_house_line_above_the_row():
    found = by_code()
    assert found["100001"].fund_house == "Alpha Mutual Fund"
    assert found["100005"].fund_house == "Beta Mutual Fund"
    assert found["400001"].fund_house == "Alpha Mutual Fund"


def test_entry_carries_the_scheme_name_nav_and_date():
    entry = by_code()["100001"]
    assert (entry.name, entry.nav) == ("Alpha Bluechip Fund", 150.1)
    assert entry.nav_date.isoformat() == "2026-09-23"


def test_windows_line_endings_and_non_ascii_names_parse_the_same():
    crlf = by_code(NAVALL_SAMPLE.replace("\n", "\r\n"))
    assert set(crlf) == set(by_code())
    assert crlf["100005"].name == "Beta Investor’s Large Cap Fund"
    assert crlf["100001"].category == "Large Cap Fund"


def test_a_category_line_with_spaces_inside_the_parentheses_is_still_a_category_line():
    text = "Open Ended Schemes ( Equity Scheme - Large Cap Fund )\n\nAlpha Mutual Fund\n\n900001;INF;-;Alpha Large Cap Fund;Direct Plan;Growth;10.0000;23-Sep-2026\n"
    entry = by_code(text)["900001"]
    assert (entry.category, entry.segment) == ("Large Cap Fund", "large")


@pytest.mark.parametrize("text", ["", "\n\n", "garbage", "a;b;c", "Scheme Code;x\n\nOpen Ended Schemes(Equity Scheme - Large Cap Fund)\n"])
def test_empty_or_unrecognised_text_gives_an_empty_catalog(text):
    assert parse_navall(text) == []


@pytest.mark.parametrize(
    "header, label",
    [
        ("Open Ended Schemes(Equity Scheme - Large Cap Fund)", "Large Cap Fund"),
        ("Open Ended Schemes(Equity Schemes - Large Cap Fund)", "Large Cap Fund"),
        ("Open Ended Schemes(Other Scheme - Index Funds)", "Index Funds"),
        ("Close Ended Schemes(ELSS)", "ELSS"),
        ("Open Ended Schemes(Fund of Funds Scheme (Domestic))", "Fund of Funds Scheme (Domestic)"),
        ("Open Ended Schemes(Exchange Traded Funds (ETFs) - Debt ETF)", "Debt ETF"),
        ("Open Ended Schemes ( Debt Scheme - Overnight Fund )", "Overnight Fund"),
        ("Open Ended Schemes(Solution Oriented Scheme - Children\N{REPLACEMENT CHARACTER}s Fund)", "Children's Fund"),
    ],
)
def test_the_category_label_is_amfis_own_text_after_the_first_dash(header, label):
    assert _category_label(header) == label


@pytest.mark.parametrize(
    "category",
    [
        "Open Ended Schemes(Equity Scheme - Large Cap Fund)",
        "Open Ended Schemes(Equity Schemes - Large Cap Fund)",
    ],
)
def test_both_header_spellings_map_to_the_same_segment(category):
    assert _segment(category, "Any Fund") == "large"


@pytest.mark.parametrize(
    "name, is_plain_nifty_50",
    [
        ("HDFC Nifty 50 Index Fund", True),
        ("UTI Nifty50 Index Fund", True),
        ("Alpha NIFTY 50 Index Fund", True),
        ("Nextgen Nifty 50 Index Fund", True),
        ("Value Partners Nifty 50 Index Fund", True),
        ("Alpha Nifty Next 50 Index Fund", False),
        ("Alpha Nifty 500 Index Fund", False),
        ("Alpha Nifty 50 Equal Weight Index Fund", False),
        ("Alpha Nifty 50 Value 20 Index Fund", False),
        ("Alpha Nifty 50 Quality Index Fund", False),
        ("Alpha Nifty Alpha 50 Index Fund", False),
        ("Alpha Nifty 50 Momentum 30 Index Fund", False),
        ("Alpha Nifty 50 Low Volatility Index Fund", False),
        ("Alpha Sensex Index Fund", False),
        ("SBI NIFTY INDEX FUND", True),
        ("Alpha Nifty 100 Index Fund", False),
    ],
)
def test_only_plain_nifty_50_index_funds_make_the_nifty_segment(name, is_plain_nifty_50):
    assert (_segment(INDEX_CATEGORY, name) == "nifty") is is_plain_nifty_50


def one_scheme(option, plan="Direct Plan"):
    return (
        "Open Ended Schemes(Equity Scheme - Large Cap Fund)\n\nAlpha Mutual Fund\n\n"
        f"900001;INF000A09001;-;Alpha Large Cap Fund;{plan};{option};10.0000;23-Sep-2026\n"
    )


@pytest.mark.parametrize("option", ["Growth", "Growth Option", "GROWTH", "GROWTH OPTION", "Growth option", "Direct Growth", "Cumulative"])
def test_every_growth_label_fund_houses_use_is_accepted(option):
    assert list(by_code(one_scheme(option))) == ["900001"]


@pytest.mark.parametrize("option", ["IDCW", "IDCW Payout", "Bonus Option", "Payout", "", "Income Distribution cum capital withdrawal", "Annual IDCW"])
def test_dividend_bonus_and_unlabelled_options_are_not_growth(option):
    assert by_code(one_scheme(option)) == {}


def test_plan_label_is_matched_without_regard_to_case():
    assert list(by_code(one_scheme("Growth", plan="DIRECT PLAN"))) == ["900001"]
    assert by_code(one_scheme("Growth", plan="Regular Plan")) == {}
