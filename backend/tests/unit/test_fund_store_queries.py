"""FundStore.top and FundStore.search: ranking, sections and fund-house matching (spec section 5.3)."""

import pytest

from lib.fund_store import rank_funds

from .fund_store_fakes import make_store
from .stored_fund_fixtures import stored


def returns(**values):
    return {"1y": None, "3y": None, "5y": None, "max": None, **values}


async def loaded(*funds):
    store, *_ = make_store(seeded=funds)
    await store.load()
    return store


def names(funds):
    return [fund.name for fund in funds]


async def test_top_of_an_empty_store_is_four_empty_lists():
    store = await loaded()
    assert store.top("3y") == {"nifty": [], "large": [], "mid": [], "small": []}


async def test_top_ranks_each_segment_best_first_with_ties_by_name():
    store = await loaded(
        stored("1", name="B", returns=returns(**{"3y": 10.0})),
        stored("2", name="A", returns=returns(**{"3y": 10.0})),
        stored("3", name="C", returns=returns(**{"3y": 12.5})),
        stored("4", name="M", segment="mid", returns=returns(**{"3y": 9.0})),
    )
    top = store.top("3y")
    assert names(top["large"]) == ["C", "A", "B"] and names(top["mid"]) == ["M"]
    assert top["nifty"] == [] and top["small"] == []


async def test_top_leaves_out_funds_without_a_value_for_the_window_and_funds_without_a_segment():
    store = await loaded(
        stored("1", name="Old", returns=returns(**{"3y": 9.0, "5y": 8.0})),
        stored("2", name="New", returns=returns(**{"3y": 20.0})),
        stored("3", name="Liquid", segment=None, category="Liquid Fund", returns=returns(**{"5y": 7.0})),
    )
    assert names(store.top("5y")["large"]) == ["Old"]
    assert all(fund.segment is not None for funds in store.top("3y").values() for fund in funds)


async def test_top_is_capped_at_ten_per_segment():
    store = await loaded(*[stored(str(i), name=f"Fund {i:02d}", returns=returns(**{"3y": float(i)})) for i in range(12)])
    top = store.top("3y")["large"]
    assert len(top) == 10 and names(top)[0] == "Fund 11"


def test_max_ranks_a_fund_of_a_year_or_more_above_a_newer_fund_with_a_bigger_absolute_return():
    funds = [
        stored("1", name="NewHot", returns=returns(max=30.0), max_is_annualised=False),
        stored("2", name="Steady", returns=returns(max=11.0)),
        stored("3", name="Better", returns=returns(max=13.0)),
    ]
    assert names(rank_funds(funds, "max")) == ["Better", "Steady", "NewHot"]


async def test_search_matches_fund_house_names_only_and_lists_the_matching_houses():
    store = await loaded(
        stored("1", name="Alpha Large", fund_house="Alpha Mutual Fund"),
        stored("2", name="Beta Large", fund_house="Beta Mutual Fund"),
        stored("3", name="Alpha Bond", fund_house="Alpha Mutual Fund", segment=None, category="Corporate Bond Fund"),
    )
    houses, sections = store.search("alpha", "3y")
    assert houses == ["Alpha Mutual Fund"]
    assert [names(section.funds) for section in sections] == [["Alpha Large"], ["Alpha Bond"]]
    assert store.search("Large", "3y") == ([], [])  # a scheme name is not a fund house


async def test_search_is_case_insensitive_and_ignores_surrounding_spaces():
    store = await loaded(stored("1", fund_house="HDFC Mutual Fund"))
    assert store.search("  hdfc ", "3y")[0] == ["HDFC Mutual Fund"]
    assert store.search("MUTUAL", "3y")[0] == ["HDFC Mutual Fund"]


@pytest.mark.parametrize("query", ["", "   ", "(", ".*", "%", "[a-z]", "hdfc%", "\\"])
async def test_a_blank_or_pattern_like_query_matches_nothing_and_never_raises(query):
    store = await loaded(stored("1", fund_house="HDFC Mutual Fund"))
    assert store.search(query, "3y") == ([], [])


async def test_search_lists_segment_sections_first_in_segment_order_then_categories_a_to_z():
    store = await loaded(
        stored("1", segment="small", category="Small Cap Fund"),
        stored("2", segment="nifty", category="Index Funds"),
        stored("3", segment="mid", category="Mid Cap Fund"),
        stored("4", segment="large", category="Large Cap Fund"),
        stored("5", segment=None, category="Liquid Fund"),
        stored("6", segment=None, category="debt ETF"),
        stored("7", segment=None, category="Corporate Bond Fund"),
    )
    _, sections = store.search("alpha", "3y")
    assert [(section.key, section.title) for section in sections] == [
        ("nifty", "Nifty 50 index"), ("large", "Large cap"), ("mid", "Mid cap"), ("small", "Small cap"),
        ("cat-corporate-bond-fund", "Corporate Bond Fund"), ("cat-debt-etf", "debt ETF"), ("cat-liquid-fund", "Liquid Fund"),
    ]


async def test_a_segment_fund_is_listed_under_its_segment_and_not_again_under_its_category():
    store = await loaded(stored("1", segment="large", category="Large Cap Fund"), stored("2", segment=None, category="Large & Mid Cap Fund"))
    _, sections = store.search("alpha", "3y")
    assert [section.key for section in sections] == ["large", "cat-large-mid-cap-fund"]
    assert [len(section.funds) for section in sections] == [1, 1]


async def test_funds_with_the_same_category_label_share_one_section():
    store = await loaded(
        stored("1", segment=None, category="Contra Fund", fund_house="Alpha Mutual Fund"),
        stored("2", segment=None, category="Contra Fund", fund_house="Alpha Mutual Fund"),
    )
    _, sections = store.search("alpha", "3y")
    assert [(section.key, len(section.funds)) for section in sections] == [("cat-contra-fund", 2)]


@pytest.mark.parametrize(
    "category, key",
    [
        ("Sectoral/ Thematic", "cat-sectoral-thematic"),
        ("Fund of Funds Scheme (Domestic)", "cat-fund-of-funds-scheme-domestic"),
        ("Children's Fund", "cat-children-s-fund"),
        ("ELSS", "cat-elss"),
        ("", "cat-other-funds"),
    ],
)
async def test_a_category_key_is_cat_plus_the_label_lower_cased_with_hyphens(category, key):
    store = await loaded(stored("1", segment=None, category=category))
    _, sections = store.search("alpha", "3y")
    assert sections[0].key == key


async def test_inside_a_section_funds_with_a_value_come_first_best_first_then_the_rest_by_name():
    store = await loaded(
        stored("1", name="Zeta", segment=None, category="Liquid Fund", returns=returns()),
        stored("2", name="Beta", segment=None, category="Liquid Fund", returns=returns(**{"3y": 5.0})),
        stored("3", name="Alpha", segment=None, category="Liquid Fund", returns=returns()),
        stored("4", name="Gamma", segment=None, category="Liquid Fund", returns=returns(**{"3y": 7.0})),
    )
    _, sections = store.search("alpha", "3y")
    assert names(sections[0].funds) == ["Gamma", "Beta", "Alpha", "Zeta"]


async def test_search_never_hides_a_fund_and_is_not_capped():
    store = await loaded(*[stored(str(i), returns=returns()) for i in range(12)])
    _, sections = store.search("alpha", "3y")
    assert len(sections[0].funds) == 12
