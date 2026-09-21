"""Single seam to the LLM provider. Swap providers by editing this file only."""

from __future__ import annotations

import json
import os
from typing import AsyncIterator

DEFAULT_MODEL = "gemini-3-flash-preview"


def llm_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _client():
    from google import genai

    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


async def generate_json(system_message: str, content: str) -> dict:
    """One-shot structured call: the model replies with a JSON object, parsed here (ValueError if it is not JSON)."""
    from google.genai import types

    response = await _client().aio.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
        contents=content,
        config=types.GenerateContentConfig(system_instruction=system_message, response_mime_type="application/json"),
    )
    try:
        return json.loads(response.text or "")
    except json.JSONDecodeError as error:
        raise ValueError("The model did not return valid JSON") from error


async def stream_answer(system_message: str, question: str) -> AsyncIterator[str]:
    from google.genai import types

    stream = await _client().aio.models.generate_content_stream(
        model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
        contents=question,
        config=types.GenerateContentConfig(system_instruction=system_message),
    )
    async for chunk in stream:
        if chunk.text:
            yield chunk.text
