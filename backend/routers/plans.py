from __future__ import annotations

from fastapi import APIRouter, Depends

from lib.auth import get_current_user
from lib.db import db
from models.rag import PublishedPlan

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PublishedPlan])
async def list_published_plans(_: dict = Depends(get_current_user)) -> list[PublishedPlan]:
    """Cards an admin has reviewed and published, from documents that are currently active."""
    documents = await db.rag_documents.find({"plan_status": "published", "enabled": {"$ne": False}}, {"_id": 0}).sort("created_at", 1).to_list(100)
    return [PublishedPlan(**document["plan"], id=document["id"], source_title=document["title"]) for document in documents if document.get("plan")]
