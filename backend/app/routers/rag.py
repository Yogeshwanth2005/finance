from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from supabase import Client

from app.config import DEMO_MODE
from app.db import get_supabase
from app.demo_user import get_or_create_demo_user
from app.models import User
from app.mapping import get_table_name
from app.services.rag.guardrails import evaluate_guardrail
from app.services.rag.rag import extract_text, chunk_text, embed, cosine

router = APIRouter()


class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    plan_id: str | None = None


class ChatQueryResponse(BaseModel):
    is_refusal: bool
    answer: str
    sources: list[dict[str, Any]]
    demo_mode: bool


@router.get("/api/insurance/rag/documents")
def list_documents(
    supabase: Client = Depends(get_supabase),
    user: User = Depends(get_or_create_demo_user),
):
    """List all active insurance policy documents available for RAG retrieval."""
    doc_table = get_table_name("InsuranceDocument")
    res = supabase.table(doc_table).select("*").eq("status", "active").order("createdAt", desc=True).execute()

    return {
        "documents": [
            {
                "id": doc["id"],
                "title": doc["title"],
                "filename": doc["filename"],
                "plan_id": doc["planId"],
                "source_type": doc["sourceType"],
                "total_chunks": doc["totalChunks"],
                "created_at": doc["createdAt"],
            }
            for doc in res.data
        ]
    }


@router.post("/api/insurance/rag/chat", response_model=ChatQueryResponse)
def query_rag_chat(
    req: ChatQueryRequest,
    supabase: Client = Depends(get_supabase),
    user: User = Depends(get_or_create_demo_user),
):
    """
    RAG chat query endpoint.
    Enforces Invariant 4: Hard regulatory refusal for comparisons, rankings, or advice.
    Retrieves factual clauses from indexed policy documents using deterministic vector similarity.
    """
    # 1. Guardrail evaluation
    is_allowed, refusal_message = evaluate_guardrail(req.query)
    if not is_allowed:
        # Record refusal message in history
        chat_table = get_table_name("InsuranceChatMessage")
        supabase.table(chat_table).insert({
            "userId": user.id,
            "role": "assistant",
            "content": refusal_message or "",
            "sources": [],
        }).execute()

        return ChatQueryResponse(
            is_refusal=True,
            answer=refusal_message or "",
            sources=[],
            demo_mode=DEMO_MODE,
        )

    # 2. Vector search over active document chunks
    query_vec = embed(req.query)

    # Query chunks and join with documents
    chunk_table = get_table_name("InsuranceDocumentChunk")
    doc_table = get_table_name("InsuranceDocument")

    # Supabase REST join: select chunks and their related document
    # Filter for active documents
    query_str = f"*, {doc_table}(*)"
    res = supabase.table(chunk_table).select(query_str).execute()

    # Filter for active documents and plan_id in-memory (since REST filtering on joined tables can be tricky)
    all_chunks = res.data
    valid_chunks = []
    for chunk in all_chunks:
        doc = chunk.get(doc_table)
        if not doc: continue
        if doc.get("status") != "active": continue
        if req.plan_id and doc.get("planId") != req.plan_id: continue
        valid_chunks.append((chunk, doc))

    scored_chunks: list[tuple[float, dict, dict]] = []
    for chunk, doc in valid_chunks:
        sim = cosine(query_vec, chunk["embedding"])
        scored_chunks.append((sim, chunk, doc))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    top_results = [item for item in scored_chunks[:3] if item[0] > 0.05]

    if not top_results:
        fallback_answer = (
            "No specific clause in the available policy documents matched your query. "
            "Please check the official policy brochure or verify plan documentation."
        )
        chat_table = get_table_name("InsuranceChatMessage")
        supabase.table(chat_table).insert({
            "userId": user.id,
            "role": "assistant",
            "content": fallback_answer,
            "sources": [],
        }).execute()

        return ChatQueryResponse(
            is_refusal=False,
            answer=fallback_answer,
            sources=[],
            demo_mode=DEMO_MODE,
        )

    sources = [
        {
            "document_id": doc["id"],
            "title": doc["title"],
            "filename": doc["filename"],
            "chunk_index": chunk["chunkIndex"],
            "similarity": round(score, 4),
            "excerpt": chunk["content"][:300] + ("..." if len(chunk["content"]) > 300 else ""),
        }
        for score, chunk, doc in top_results
    ]

    answer_parts = [
        f"Based on the official wording from **{top_results[0][2]['title']}**:\n",
        top_results[0][1]["content"],
    ]
    if len(top_results) > 1:
        answer_parts.append("\n\n**Additional relevant clauses:**\n" + top_results[1][1]["content"])

    full_answer = "\n".join(answer_parts)

    chat_table = get_table_name("InsuranceChatMessage")
    supabase.table(chat_table).insert({
        "userId": user.id,
        "role": "assistant",
        "content": full_answer,
        "sources": sources,
    }).execute()

    return ChatQueryResponse(
        is_refusal=False,
        answer=full_answer,
        sources=sources,
        demo_mode=DEMO_MODE,
    )


@router.post("/api/insurance/rag/ingest")
async def ingest_document(
    title: str = Form(...),
    plan_id: str | None = Form(None),
    file: UploadFile = File(...),
    supabase: Client = Depends(get_supabase),
    user: User = Depends(get_or_create_demo_user),
):
    \"\"\"
    Ingest and index an insurance policy document (PDF, DOCX, TXT).
    Extracts text, splits into overlapping chunks, computes deterministic embeddings, and persists.
    \"\"\"
    content = await file.read()
    raw_text = extract_text(file.filename or "policy.txt", content)
    if not raw_text:
        raise HTTPException(status_code=400, detail="Could not extract readable text from document")

    chunks = chunk_text(raw_text)
    if not chunks:
        raise HTTPException(status_code=400, detail="Document produced 0 text chunks")

    source_type = (file.filename or "txt").lower().rsplit(".", 1)[-1]

    doc_table = get_table_name("InsuranceDocument")
    doc_res = supabase.table(doc_table).insert({
        "title": title,
        "filename": file.filename or "uploaded_doc",
        "planId": plan_id,
        "sourceType": source_type,
        "status": "active",
        "totalChunks": len(chunks),
    }).execute()

    doc = doc_res.data[0] if doc_res.data else None
    if not doc:
        raise HTTPException(status_code=500, detail="Failed to create insurance document")

    chunk_table = get_table_name("InsuranceDocumentChunk")
    chunks_to_insert = []
    for idx, chunk in enumerate(chunks):
        emb = embed(chunk)
        chunks_to_insert.append({
            "documentId": doc["id"],
            "chunkIndex": idx,
            "content": chunk,
            "embedding": emb,
        })

    if chunks_to_insert:
        supabase.table(chunk_table).insert(chunks_to_insert).execute()

    return {
        "success": True,
        "document_id": doc["id"],
        "title": doc["title"],
        "total_chunks": doc["totalChunks"],
    }
