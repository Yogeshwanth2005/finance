"""Groq's free tier refuses a request over 8,000 tokens per minute, so a whole-document extraction must fit under it.

No server, DB or network: the LLM call is monkeypatched.
"""

from lib import plan_extract

# Measured against the live API: a 60,000-character document was refused with "Limit 8000, Requested 16800"
# (about 0.27 tokens per character). 18,000 characters is roughly 4,900 tokens, which leaves room in the
# same minute for the model's reasoning and reply.
FREE_TIER_SAFE_CHARS = 18_000


async def test_extraction_request_fits_the_free_tier_token_budget(monkeypatch):
    seen = {}

    async def fake_generate_json(system_message, content):
        seen["chars"] = len(system_message) + len(content)
        return {}

    monkeypatch.setattr(plan_extract, "llm_configured", lambda: True)
    monkeypatch.setattr(plan_extract, "generate_json", fake_generate_json)

    await plan_extract.extract_plan("A very long brochure", "x" * 200_000)

    assert seen["chars"] <= FREE_TIER_SAFE_CHARS
