from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


NOT_STATED = "Not stated in the document"


class PlanDetails(BaseModel):
    eligibility: str = Field(default=NOT_STATED, max_length=600)
    cover_range: str = Field(default=NOT_STATED, max_length=600)
    waiting_periods: str = Field(default=NOT_STATED, max_length=600)
    exclusions: str = Field(default=NOT_STATED, max_length=600)
    riders: str = Field(default=NOT_STATED, max_length=600)
    claim_terms: str = Field(default=NOT_STATED, max_length=600)


class PlanCard(BaseModel):
    """The card shown on the Insurance page, extracted from one indexed document and reviewed by an admin."""

    category: Literal["term", "health"]
    name: str = Field(min_length=1, max_length=120)
    provider: str = Field(default=NOT_STATED, max_length=120)
    csr: str | None = Field(default=None, max_length=12)
    annual_premium_from: int | None = Field(default=None, gt=0, lt=10_000_000)
    cover_label: str | None = Field(default=None, max_length=160)
    highlights: list[str] = Field(default_factory=list, max_length=6)
    fit: str | None = Field(default=None, max_length=300)
    details: PlanDetails = Field(default_factory=PlanDetails)


class PlanStatusInput(BaseModel):
    status: Literal["draft", "published"]


class PublishedPlan(PlanCard):
    id: str
    source_title: str


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
    plan: PlanCard | None = None
    plan_status: Literal["none", "draft", "published"] = "none"


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