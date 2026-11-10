"""Chat and conversation endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.error_handlers import AppError
from app.database.session import get_db
from app.schemas.chat import (
    AskQuestionRequest,
    AskQuestionResponse,
    CitationResponse,
    ConversationDeleteResponse,
    ConversationHistoryResponse,
    ConversationResponse,
)
from app.schemas.common import PaginationResponse
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "/{repository_id}",
    response_model=AskQuestionResponse,
    summary="Ask a question about a repository",
    responses={
        400: {"description": "Malformed request or invalid conversation/repository pairing"},
        404: {"description": "Repository or conversation does not exist"},
        409: {"description": "Repository is not ready, is being deleted, or has no active index"},
        413: {"description": "Question exceeds configured request limit"},
        422: {"description": "Request schema validation failed"},
        429: {"description": "Configured rate limit reached"},
        502: {"description": "LLM provider returned an upstream failure"},
        503: {"description": "Required retrieval/database service unavailable"},
        504: {"description": "LLM/retrieval operation timed out"},
    },
)
def ask_question(
    repository_id: UUID = Path(..., description="Repository UUID"),
    payload: AskQuestionRequest | None = None,
    db: Session = Depends(get_db),
) -> AskQuestionResponse:
    question = payload.question if payload else ""
    conversation_id = payload.conversation_id if payload else None

    result = chat_service.ask_question(
        db,
        repository_id=repository_id,
        question=question,
        conversation_id=conversation_id,
    )
    return AskQuestionResponse(
        conversation_id=result["conversation_id"],
        message_id=result["message_id"],
        answer=result["answer"],
        citations=[
            CitationResponse(
                source_id=c["source_id"],
                file_path=c["file_path"],
                symbol_name=c["symbol_name"],
                start_line=c["start_line"],
                end_line=c["end_line"],
                snippet=c["snippet"],
                commit_sha=c["commit_sha"],
            )
            for c in result["citations"]
        ],
        insufficient_evidence=result["insufficient_evidence"],
    )


@router.get(
    "/{repository_id}/history",
    response_model=ConversationHistoryResponse,
    summary="List conversations for a repository",
    responses={404: {"description": "Repository not found"}, 422: {"description": "Invalid query parameters"}},
)
def list_conversations(
    repository_id: UUID = Path(..., description="Repository UUID"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ConversationHistoryResponse:
    items, total = chat_service.list_conversations(
        db, repository_id=repository_id, limit=limit, offset=offset
    )
    return ConversationHistoryResponse(
        repository_id=repository_id,
        items=[
            {
                "id": item["id"],
                "title": item["title"],
                "created_at": item["created_at"],
                "updated_at": item["updated_at"],
                "message_count": item["message_count"],
            }
            for item in items
        ],
        pagination=PaginationResponse(
            limit=limit,
            offset=offset,
            total=total,
            has_more=offset + len(items) < total,
        ),
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get a conversation and its messages",
    responses={404: {"description": "Conversation does not exist"}, 422: {"description": "Invalid UUID"}},
)
def get_conversation(
    conversation_id: UUID = Path(..., description="Conversation UUID"),
    repository_id: UUID | None = Query(
        default=None,
        description="Repository UUID (used to verify conversation ownership if provided)",
    ),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    data = chat_service.get_conversation(
        db, conversation_id=conversation_id, repository_id=repository_id
    )
    return ConversationResponse(
        id=data["id"],
        repository_id=data["repository_id"],
        title=data["title"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        messages=[
            {
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "citations": m["citations"],
                "created_at": m["created_at"],
            }
            for m in data["messages"]
        ],
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=204,
    summary="Delete a conversation and its messages",
    responses={
        204: {"description": "Deleted"},
        404: {"description": "Conversation does not exist"},
        422: {"description": "Invalid UUID"},
    },
)
def delete_conversation(
    conversation_id: UUID = Path(..., description="Conversation UUID"),
    repository_id: UUID = Query(
        ..., description="Repository UUID (used to verify conversation ownership)"
    ),
    db: Session = Depends(get_db),
) -> None:
    chat_service.delete_conversation(
        db, conversation_id=conversation_id, repository_id=repository_id
    )
