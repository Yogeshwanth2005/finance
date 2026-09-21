from __future__ import annotations

import html
import hashlib
import io
import math
import re
from typing import Any

from lib.chat_context import top_chunks_per_document
from lib.db import db

VECTOR_SIZE = 128


def clean_text(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()


def extract_text(filename: str, content: bytes) -> str:
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
    """Small deterministic local vectorizer; vectors stay in Mongo with each chunk."""
    vector = [0.0] * VECTOR_SIZE
    for token in re.findall(r"[a-z0-9₹]+", text.lower()):
        index = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big") % VECTOR_SIZE
        vector[index] += 1.0
    magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / magnitude, 6) for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


async def retrieve(question: str, limit: int = 5, document_ids: list[str] | None = None) -> list[dict[str, Any]]:
    query_vector = embed(question)
    query: dict[str, Any] = {"enabled": {"$ne": False}}
    if document_ids:
        query["document_id"] = {"$in": document_ids}
    candidates = await db.rag_chunks.find(query, {"_id": 0}).to_list(5000)
    ranked = sorted(((cosine(query_vector, item.get("embedding", [])), item) for item in candidates), key=lambda pair: pair[0], reverse=True)
    return [item for score, item in ranked[:limit] if score > 0.05]


async def retrieve_across_documents(question: str, per_document: int = 2, max_documents: int = 6) -> list[dict[str, Any]]:
    """Retrieval for questions that name no plan: the best chunks of every relevant active document."""
    query_vector = embed(question)
    candidates = await db.rag_chunks.find({"enabled": {"$ne": False}}, {"_id": 0}).to_list(5000)
    scored = [(cosine(query_vector, item.get("embedding", [])), item) for item in candidates]
    return top_chunks_per_document([pair for pair in scored if pair[0] > 0.05], per_document, max_documents)