"""Pydantic contracts for chat and conversation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import APIModel, PaginationResponse


class CitationResponse(BaseModel):
    source_id: str
    file_path: str
    symbol_name: str | None = None
    start_line: int
    end_line: int
    snippet: str
    commit_sha: str


class AskQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None

    @field_validator("question")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A question is required.")
        return value


class AskQuestionResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    citations: list[CitationResponse]
    insufficient_evidence: bool


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    citations: list[dict[str, Any]]
    created_at: datetime


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationHistoryResponse(BaseModel):
    repository_id: UUID
    items: list[ConversationSummary]
    pagination: PaginationResponse


class ConversationResponse(BaseModel):
    id: UUID
    repository_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]


class ConversationDeleteResponse(BaseModel):
    conversation_id: UUID
    status: str
    message: str
