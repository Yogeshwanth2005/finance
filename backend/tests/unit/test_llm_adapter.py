"""lib.llm is the only module that talks to OpenRouter; these tests never hit the real network.

The real httpx client runs against a MockTransport, so URL, headers, payload and SSE parsing are all exercised.
"""

import json

import httpx
import pytest

from lib import llm

_RealAsyncClient = httpx.AsyncClient


@pytest.fixture(autouse=True)
def _openrouter_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)


def _serve(monkeypatch, handler):
    """Route every httpx.AsyncClient that lib.llm builds through `handler`; returns the requests it saw."""
    seen: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: _RealAsyncClient(transport=httpx.MockTransport(respond), **kwargs))
    return seen


def _completion(text):
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": text}}]})


def _sse(*events):
    lines = []
    for event in events:
        lines.append(event if isinstance(event, str) else "data: " + json.dumps(event))
        lines.append("")
    return httpx.Response(200, content="\n".join(lines).encode(), headers={"content-type": "text/event-stream"})


def _delta(text):
    return {"choices": [{"delta": {"content": text}}]}


def test_llm_configured_reflects_env(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert llm.llm_configured() is False
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    assert llm.llm_configured() is True


def test_a_gemini_key_alone_does_not_count_as_configured(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "some-other-providers-key")
    assert llm.llm_configured() is False


async def test_generate_json_sends_an_authenticated_json_request_and_parses_the_reply(monkeypatch):
    seen = _serve(monkeypatch, lambda request: _completion('{"name": "Plan A"}'))

    result = await llm.generate_json("SYSTEM", "CONTENT")

    assert result == {"name": "Plan A"}
    request = seen[0]
    assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == llm.DEFAULT_MODEL
    assert body["messages"] == [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "CONTENT"}]
    assert body["response_format"] == {"type": "json_object"}


async def test_model_can_be_overridden_from_env(monkeypatch):
    seen = _serve(monkeypatch, lambda request: _completion("{}"))
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")

    await llm.generate_json("SYSTEM", "CONTENT")

    assert json.loads(seen[0].content)["model"] == "test-model"


async def test_generate_json_accepts_a_reply_wrapped_in_a_code_fence(monkeypatch):
    _serve(monkeypatch, lambda request: _completion('```json\n{"name": "Plan A"}\n```'))

    assert await llm.generate_json("SYSTEM", "CONTENT") == {"name": "Plan A"}


async def test_generate_json_raises_on_non_json_reply(monkeypatch):
    _serve(monkeypatch, lambda request: _completion("not json"))

    with pytest.raises(ValueError):
        await llm.generate_json("SYSTEM", "CONTENT")


async def test_generate_json_raises_on_http_error(monkeypatch):
    _serve(monkeypatch, lambda request: httpx.Response(401, json={"error": {"message": "No auth credentials found"}}))

    with pytest.raises(httpx.HTTPStatusError):
        await llm.generate_json("SYSTEM", "CONTENT")


async def test_generate_json_raises_when_a_200_body_carries_an_error(monkeypatch):
    _serve(monkeypatch, lambda request: httpx.Response(200, json={"error": {"message": "Provider returned error"}}))

    with pytest.raises(RuntimeError, match="Provider returned error"):
        await llm.generate_json("SYSTEM", "CONTENT")


async def test_stream_answer_yields_only_non_empty_text_and_skips_keepalives(monkeypatch):
    seen = _serve(
        monkeypatch,
        lambda request: _sse(": OPENROUTER PROCESSING", _delta("Hello"), _delta(""), {"choices": [{"delta": {}}]}, _delta(" world"), "data: [DONE]"),
    )

    deltas = [d async for d in llm.stream_answer("SYSTEM", "QUESTION")]

    assert deltas == ["Hello", " world"]
    request = seen[0]
    assert request.headers["authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["stream"] is True
    assert body["model"] == llm.DEFAULT_MODEL
    assert body["messages"] == [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "QUESTION"}]


async def test_stream_answer_raises_on_http_error(monkeypatch):
    _serve(monkeypatch, lambda request: httpx.Response(429, json={"error": {"message": "Rate limit exceeded"}}))

    with pytest.raises(httpx.HTTPStatusError):
        [d async for d in llm.stream_answer("SYSTEM", "QUESTION")]


async def test_stream_answer_raises_when_the_stream_reports_an_error(monkeypatch):
    _serve(monkeypatch, lambda request: _sse(_delta("Hel"), {"error": {"message": "Upstream disconnected"}}))

    with pytest.raises(RuntimeError, match="Upstream disconnected"):
        [d async for d in llm.stream_answer("SYSTEM", "QUESTION")]
