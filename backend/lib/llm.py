"""Single seam to the LLM provider. Swap providers by editing this file only."""

from __future__ import annotations

import os
from typing import AsyncIterator

DEFAULT_MODEL = "gemini-3-flash-preview"


def llm_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _client():
    from google import genai

    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


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
