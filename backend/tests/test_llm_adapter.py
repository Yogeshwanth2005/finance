"""lib.llm is the only module that talks to Gemini; these tests never hit the network."""

import pytest

from lib import llm


def test_llm_configured_reflects_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert llm.llm_configured() is False
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert llm.llm_configured() is True


class _Chunk:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self):
        self.kwargs = None

    async def generate_content_stream(self, **kwargs):
        self.kwargs = kwargs

        async def gen():
            for text in ("Hello", None, " world"):
                yield _Chunk(text)

        return gen()


class _FakeClient:
    def __init__(self):
        self.aio = type("Aio", (), {"models": _FakeModels()})()


async def test_stream_answer_yields_only_non_empty_text(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(llm, "_client", lambda: fake)
    monkeypatch.setenv("GEMINI_MODEL", "test-model")

    deltas = [d async for d in llm.stream_answer("SYSTEM", "QUESTION")]

    assert deltas == ["Hello", " world"]
    assert fake.aio.models.kwargs["model"] == "test-model"
    assert fake.aio.models.kwargs["contents"] == "QUESTION"
    assert fake.aio.models.kwargs["config"].system_instruction == "SYSTEM"
