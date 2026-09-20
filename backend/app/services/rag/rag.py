from __future__ import annotations

import html
import hashlib
import io
import math
import re
from typing import Any

VECTOR_SIZE = 128


def clean_text(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()


def extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from PDF, DOCX, or TXT content."""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"
    if suffix == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return clean_text("\n".join(page.extract_text() or "" for page in reader.pages))
    if suffix == "docx":
        from docx import Document

        document = Document(io.BytesIO(content))
        return clean_text("\n".join(paragraph.text for paragraph in document.paragraphs))
    return clean_text(content.decode("utf-8", errors="ignore"))


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    """Split text into word-based chunks with overlapping boundary windows."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunk = " ".join(words[start : start + size])
        if chunk:
            chunks.append(chunk)
        start += max(1, size - overlap)
    return chunks


def embed(text: str) -> list[float]:
    """Deterministic local vectorizer generating unit-normalized 128-dim vectors."""
    vector = [0.0] * VECTOR_SIZE
    for token in re.findall(r"[a-z0-9₹]+", text.lower()):
        index = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big") % VECTOR_SIZE
        vector[index] += 1.0
    magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / magnitude, 6) for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity between two unit vectors."""
    return sum(a * b for a, b in zip(left, right))
