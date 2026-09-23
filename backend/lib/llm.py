"""Single seam to the LLM provider (OpenRouter's OpenAI-compatible API). Swap providers by editing this file only."""

from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx

BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter/free"  # OpenRouter's router over whichever free models are live; pin one with OPENROUTER_MODEL
TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def llm_configured() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BASE_URL, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, timeout=TIMEOUT)


def _payload(system_message: str, content: str, **extra) -> dict:
    return {
        "model": os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL),
        "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": content}],
        **extra,
    }


def _raise_if_error(body: dict) -> None:
    """OpenRouter can report a provider failure inside a 200 body (or mid-stream) instead of an HTTP status."""
    error = body.get("error")
    if error:
        raise RuntimeError(str(error.get("message", error)) if isinstance(error, dict) else str(error))


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.removesuffix("```")
    return text.strip()


async def generate_json(system_message: str, content: str) -> dict:
    """One-shot structured call: the model replies with a JSON object, parsed here (ValueError if it is not JSON)."""
    async with _client() as client:
        response = await client.post("/chat/completions", json=_payload(system_message, content, response_format={"type": "json_object"}))
    response.raise_for_status()
    body = response.json()
    _raise_if_error(body)
    text = body["choices"][0]["message"].get("content") or ""
    try:
        return json.loads(_strip_code_fence(text))
    except json.JSONDecodeError as error:
        raise ValueError("The model did not return valid JSON") from error


async def stream_answer(system_message: str, question: str) -> AsyncIterator[str]:
    async with _client() as client:
        async with client.stream("POST", "/chat/completions", json=_payload(system_message, question, stream=True)) as response:
            if response.is_error:
                await response.aread()  # so the caller can read the provider's message off the raised error
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue  # blank separators and ": OPENROUTER PROCESSING" keep-alive comments
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                _raise_if_error(chunk)
                text = chunk["choices"][0]["delta"].get("content")
                if text:
                    yield text
