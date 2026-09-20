from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    id: str
    title: str
    source_type: str
    source_url: str | None = None
    chunk_count: int
    status: str
    enabled: bool = True
    created_at: datetime
    created_by: str


class DocumentStatusInput(BaseModel):
    enabled: bool


class AdminOverview(BaseModel):
    total_users: int
    completed_profiles: int
    indexed_documents: int
    active_documents: int
    vector_chunks: int
    user_questions: int


class AdminUserRecord(BaseModel):
    id: str
    name: str
    email: str
    role: str
    profile_complete: bool
    created_at: datetime


class AdminQuestionRecord(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_email: str
    question: str
    created_at: datetime


class ChatQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class ChatMessageRecord(BaseModel):
    id: str
    role: str
    text: str
    sources: list[str] = Field(default_factory=list)
    created_at: datetime