"""Plan-card extraction: LLM output is untrusted, so normalisation must never invent or leak bad values.

No server, DB or network: the LLM call is monkeypatched.
"""

import pytest

from lib import plan_extract
from lib.plan_extract import NOT_STATED, extract_plan, normalize_plan

FULL = {
    "category": "Term",
    "name": " Click 2 Protect Super ",
    "provider": "HDFC Life",
    "csr": "99.2 %",
    "annual_premium_from": "₹18,500",
    "cover_label": "Term cover ₹1 crore",
    "highlights": ["Flexible payout options", "Optional riders", "Flexible payout options", "", "A", "B", "C"],
    "fit": "Best for income replacement",
    "details": {
        "eligibility": "Age 18-65",
        "cover_range": "₹50 lakh to ₹5 crore",
        "waiting_periods": "not stated",
        "exclusions": "Suicide within 12 months",
        "riders": None,
        "claim_terms": "Claim within 30 days",
    },
}


def test_normalize_cleans_a_full_extraction():
    card = normalize_plan(FULL)
    assert card.category == "term"
    assert card.name == "Click 2 Protect Super"
    assert card.csr == "99.2%"
    assert card.annual_premium_from == 18500
    assert card.highlights == ["Flexible payout options", "Optional riders", "A", "B"]  # deduped, blanks dropped, max 4
    assert card.details.eligibility == "Age 18-65"


def test_missing_or_placeholder_details_become_not_stated():
    card = normalize_plan(FULL)
    assert card.details.waiting_periods == NOT_STATED  # model said "not stated"
    assert card.details.riders == NOT_STATED  # model said null


@pytest.mark.parametrize("csr", ["", None, "high", "150%", "n/a"])
def test_unreliable_csr_is_dropped_not_guessed(csr):
    assert normalize_plan({**FULL, "csr": csr}).csr is None


@pytest.mark.parametrize("premium", [None, "", "on request", 0, -5, 10**9, "n/a"])
def test_unreliable_premium_is_dropped_not_guessed(premium):
    assert normalize_plan({**FULL, "annual_premium_from": premium}).annual_premium_from is None


def test_health_category_and_numeric_premium_are_accepted():
    card = normalize_plan({**FULL, "category": "health insurance", "annual_premium_from": 26500.0})
    assert card.category == "health"
    assert card.annual_premium_from == 26500


@pytest.mark.parametrize("category", ["ulip", "", None, "savings"])
def test_unknown_category_makes_no_card(category):
    assert normalize_plan({**FULL, "category": category}) is None


@pytest.mark.parametrize("raw", [{}, {**FULL, "name": ""}, {**FULL, "name": None}, "text", None, []])
def test_no_name_or_wrong_shape_makes_no_card(raw):
    assert normalize_plan(raw) is None


def test_overlong_text_is_truncated_to_the_model_limits():
    card = normalize_plan({**FULL, "name": "N" * 500, "fit": "F" * 2000, "details": {"exclusions": "E" * 5000}})
    assert len(card.name) <= 120
    assert len(card.fit) <= 300
    assert len(card.details.exclusions) <= 600


async def test_extract_plan_skips_the_llm_when_not_configured(monkeypatch):
    monkeypatch.setattr(plan_extract, "llm_configured", lambda: False)
    assert await extract_plan("Title", "text") is None


async def test_extract_plan_returns_a_normalised_card(monkeypatch):
    seen = {}

    async def fake_generate_json(system_message, content):
        seen["system"], seen["content"] = system_message, content
        return FULL

    monkeypatch.setattr(plan_extract, "llm_configured", lambda: True)
    monkeypatch.setattr(plan_extract, "generate_json", fake_generate_json)

    card = await extract_plan("HDFC Life brochure", "x" * (plan_extract.MAX_EXTRACT_CHARS + 500))

    assert card.name == "Click 2 Protect Super"
    assert "HDFC Life brochure" in seen["content"]
    assert len(seen["content"]) < plan_extract.MAX_EXTRACT_CHARS + 500  # document text is capped
    assert "not stated" in seen["system"].lower()


async def test_extract_plan_returns_none_when_the_llm_fails(monkeypatch):
    async def boom(system_message, content):
        raise RuntimeError("429")

    monkeypatch.setattr(plan_extract, "llm_configured", lambda: True)
    monkeypatch.setattr(plan_extract, "generate_json", boom)
    assert await extract_plan("Title", "text") is None


async def test_extract_plan_times_out_instead_of_hanging_the_upload(monkeypatch):
    import asyncio

    async def slow(system_message, content):
        await asyncio.sleep(5)
        return FULL

    monkeypatch.setattr(plan_extract, "llm_configured", lambda: True)
    monkeypatch.setattr(plan_extract, "generate_json", slow)
    monkeypatch.setattr(plan_extract, "EXTRACT_TIMEOUT_SECONDS", 0.05)
    assert await extract_plan("Title", "text") is None
