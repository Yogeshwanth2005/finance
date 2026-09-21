from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from lib.auth import require_admin
from lib.db import db
from lib.llm import llm_configured
from lib.plan_extract import extract_plan
from lib.rag import chunk_text, embed, extract_text
from models.rag import AdminOverview, AdminQuestionRecord, AdminUserRecord, DocumentRecord, DocumentStatusInput, PlanCard, PlanStatusInput

router = APIRouter(prefix="/admin", tags=["admin"])
ALLOWED_EXTENSIONS = {"pdf", "txt", "docx"}
MAX_BYTES = 10 * 1024 * 1024


async def _save_document(title: str, source_type: str, text: str, source_url: str | None, admin: dict) -> DocumentRecord:
    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="The document did not contain readable text")
    document_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    display_title = title.strip() or "Untitled insurance document"
    # A draft card for the admin to review; None without a Gemini key or when nothing usable is found.
    plan = await extract_plan(display_title, text)
    plan_fields = {"plan": plan.model_dump() if plan else None, "plan_status": "draft" if plan else "none"}
    await db.rag_documents.insert_one(
        {
            "_id": document_id,
            "id": document_id,
            "title": display_title,
            "source_type": source_type,
            "source_url": source_url,
            "chunk_count": len(chunks),
            "status": "indexed",
            "enabled": True,
            "created_at": created_at,
            "created_by": admin["id"],
            **plan_fields,
        }
    )
    await db.rag_chunks.insert_many(
        [
            {"_id": str(uuid.uuid4()), "document_id": document_id, "document_title": display_title, "position": index, "text": chunk, "embedding": embed(chunk), "enabled": True}
            for index, chunk in enumerate(chunks)
        ]
    )
    return DocumentRecord(id=document_id, title=display_title, source_type=source_type, source_url=source_url, chunk_count=len(chunks), status="indexed", enabled=True, created_at=created_at, created_by=admin["id"], **plan_fields)


@router.get("/overview", response_model=AdminOverview)
async def admin_overview(_: dict = Depends(require_admin)) -> AdminOverview:
    total_users = await db.users.count_documents({"role": "user"})
    completed_profiles = await db.users.count_documents({"role": "user", "profile_complete": True})
    indexed_documents = await db.rag_documents.count_documents({})
    active_documents = await db.rag_documents.count_documents({"enabled": {"$ne": False}})
    vector_chunks = await db.rag_chunks.count_documents({"enabled": {"$ne": False}})
    user_questions = await db.chat_messages.count_documents({"role": "you"})
    return AdminOverview(total_users=total_users, completed_profiles=completed_profiles, indexed_documents=indexed_documents, active_documents=active_documents, vector_chunks=vector_chunks, user_questions=user_questions)


@router.get("/users", response_model=list[AdminUserRecord])
async def list_users(_: dict = Depends(require_admin)) -> list[AdminUserRecord]:
    users = await db.users.find({"role": "user"}, {"password_hash": 0}).sort("created_at", -1).to_list(200)
    return [AdminUserRecord(id=user["_id"], name=user["name"], email=user["email"], role=user.get("role", "user"), profile_complete=bool(user.get("profile_complete", False)), created_at=user["created_at"]) for user in users]


@router.get("/questions", response_model=list[AdminQuestionRecord])
async def list_recent_questions(_: dict = Depends(require_admin)) -> list[AdminQuestionRecord]:
    questions = await db.chat_messages.find({"role": "you"}, {"_id": 0}).sort("created_at", -1).to_list(100)
    user_ids = list({question["user_id"] for question in questions})
    users = await db.users.find({"_id": {"$in": user_ids}}, {"password_hash": 0}).to_list(200)
    user_map = {user["_id"]: user for user in users}
    return [
        AdminQuestionRecord(
            id=question["id"],
            user_id=question["user_id"],
            user_name=user_map.get(question["user_id"], {}).get("name", "Unknown user"),
            user_email=user_map.get(question["user_id"], {}).get("email", "Account unavailable"),
            question=question["text"],
            created_at=question["created_at"],
        )
        for question in questions
    ]


@router.get("/documents", response_model=list[DocumentRecord])
async def list_documents(_: dict = Depends(require_admin)) -> list[DocumentRecord]:
    records = await db.rag_documents.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [DocumentRecord(**record) for record in records]


@router.patch("/documents/{document_id}/status", response_model=DocumentRecord)
async def change_document_status(document_id: str, input_data: DocumentStatusInput, _: dict = Depends(require_admin)) -> DocumentRecord:
    document = await db.rag_documents.find_one({"id": document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    next_status = "indexed" if input_data.enabled else "disabled"
    await db.rag_documents.update_one({"id": document_id}, {"$set": {"enabled": input_data.enabled, "status": next_status}})
    await db.rag_chunks.update_many({"document_id": document_id}, {"$set": {"enabled": input_data.enabled}})
    document.update({"enabled": input_data.enabled, "status": next_status})
    document.pop("_id", None)
    return DocumentRecord(**document)


async def _get_document(document_id: str) -> dict:
    document = await db.rag_documents.find_one({"id": document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    document.pop("_id", None)
    return document


async def _set_plan_fields(document_id: str, document: dict, fields: dict) -> DocumentRecord:
    await db.rag_documents.update_one({"id": document_id}, {"$set": fields})
    return DocumentRecord(**{**document, **fields})


@router.put("/documents/{document_id}/plan", response_model=DocumentRecord)
async def save_plan(document_id: str, plan: PlanCard, _: dict = Depends(require_admin)) -> DocumentRecord:
    """Admin review: store the edited card. A new card starts as a draft; a published one stays published."""
    document = await _get_document(document_id)
    plan_status = document.get("plan_status", "none")
    return await _set_plan_fields(document_id, document, {"plan": plan.model_dump(), "plan_status": "draft" if plan_status == "none" else plan_status})


@router.patch("/documents/{document_id}/plan/status", response_model=DocumentRecord)
async def change_plan_status(document_id: str, input_data: PlanStatusInput, _: dict = Depends(require_admin)) -> DocumentRecord:
    document = await _get_document(document_id)
    if not document.get("plan"):
        raise HTTPException(status_code=409, detail="Add the plan details before publishing")
    return await _set_plan_fields(document_id, document, {"plan_status": input_data.status})


@router.post("/documents/{document_id}/plan/extract", response_model=DocumentRecord)
async def extract_plan_from_document(document_id: str, _: dict = Depends(require_admin)) -> DocumentRecord:
    """Re-run AI extraction from the indexed chunks. The result replaces the card and goes back to draft."""
    if not llm_configured():
        raise HTTPException(status_code=503, detail="AI extraction is not configured on the server; enter the plan details manually")
    document = await _get_document(document_id)
    chunks = await db.rag_chunks.find({"document_id": document_id}, {"_id": 0, "text": 1, "position": 1}).to_list(5000)
    text = " ".join(chunk["text"] for chunk in sorted(chunks, key=lambda chunk: chunk.get("position", 0)))
    plan = await extract_plan(document["title"], text)
    if plan is None:
        raise HTTPException(status_code=422, detail="No term or health plan details could be extracted from that document; enter them manually")
    return await _set_plan_fields(document_id, document, {"plan": plan.model_dump(), "plan_status": "draft"})


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, _: dict = Depends(require_admin)) -> Response:
    result = await db.rag_documents.delete_one({"id": document_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.rag_chunks.delete_many({"document_id": document_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/documents", response_model=DocumentRecord)
async def upload_document(
    title: str = Form(default=""),
    source_url: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    admin: dict = Depends(require_admin),
) -> DocumentRecord:
    if file is None and not source_url.strip():
        raise HTTPException(status_code=422, detail="Upload a PDF, TXT, DOCX, or provide a web URL")
    if file is not None:
        filename = file.filename or "document.txt"
        extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=415, detail="Only PDF, TXT and DOCX files are supported")
        content = await file.read()
        if len(content) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="Documents must be smaller than 10 MB")
        return await _save_document(title or filename.rsplit(".", 1)[0], extension, extract_text(filename, content), None, admin)

    if not source_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="URL must start with http:// or https://")
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        response = await client.get(source_url)
        response.raise_for_status()
    filename = source_url.split("?")[0].rsplit("/", 1)[-1] or "page.txt"
    if "application/pdf" in response.headers.get("content-type", "") and not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    return await _save_document(title or source_url, "web", extract_text(filename, response.content), source_url, admin)