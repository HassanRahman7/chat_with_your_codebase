"""Chat application service: conversation and message persistence.

Resolves repositories, creates/validates conversations, and persists user and
assistant messages with validated citation data. Thin orchestration over the
SQLAlchemy session; all RAG logic lives in ``rag_service``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.models import Conversation, Message, Repository
from app.database.session import SessionLocal
from app.services import rag_service
from app.services.errors import RepositoryNotFoundError
from app.services.rag_service import RagAnswer, ValidatedCitation

logger = logging.getLogger(__name__)


def _serialize_citations(
    citations: list[ValidatedCitation],
) -> list[dict[str, object]]:
    return [
        {
            "source_id": c.source_id,
            "file_path": c.file_path,
            "symbol_name": c.symbol_name,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "snippet": c.snippet,
            "commit_sha": c.commit_sha,
        }
        for c in citations
    ]


def ask_question(
    db: Session,
    repository_id: UUID,
    question: str,
    *,
    conversation_id: UUID | None = None,
) -> dict:
    """Persist the user message, generate an answer, persist the assistant message."""
    repository = db.get(Repository, repository_id)
    if repository is None:
        raise RepositoryNotFoundError()
    if repository.status != "ready" or not repository.active_index_version:
        from app.services.errors import RepositoryConflictError

        raise RepositoryConflictError(
            "This repository is not ready for questions yet."
        )

    # Resolve or create the conversation.
    conversation: Conversation | None = None
    if conversation_id is not None:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None:
            raise RepositoryNotFoundError(
                "The requested conversation could not be found."
            )
        if conversation.repository_id != repository_id:
            from app.services.errors import RepositoryConflictError

            raise RepositoryConflictError(
                "The conversation does not belong to this repository."
            )
    else:
        title = question[:80]
        conversation = Conversation(
            repository_id=repository_id,
            title=title,
        )
        db.add(conversation)
        db.flush()

    # Persist the user message.
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=question,
        sequence_number=_next_sequence(db, conversation.id),
        citations=[],
    )
    db.add(user_message)
    db.flush()

    # Generate the answer via RAG.
    try:
        answer = rag_service.answer_question(
            repository=repository,
            question=question,
            conversation_id=conversation.id,
        )
    except Exception:
        # Keep the user question; do not fabricate an assistant message.
        db.commit()
        raise

    # Persist the assistant message with validated citations.
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer.answer,
        sequence_number=_next_sequence(db, conversation.id),
        citations=_serialize_citations(answer.citations),
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(conversation)
    db.refresh(assistant_message)

    logger.info(
        "Answered question repository_id=%s conversation_id=%s "
        "citations=%d insufficient_evidence=%s",
        repository_id,
        conversation.id,
        len(answer.citations),
        answer.insufficient_evidence,
    )

    return {
        "conversation_id": str(conversation.id),
        "message_id": str(assistant_message.id),
        "answer": answer.answer,
        "citations": _serialize_citations(answer.citations),
        "insufficient_evidence": answer.insufficient_evidence,
    }


def _next_sequence(db: Session, conversation_id: UUID) -> int:
    row = db.execute(
        text(
            "SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM messages "
            "WHERE conversation_id = :cid"
        ),
        {"cid": str(conversation_id)},
    ).scalar()
    return int(row or 1)


def list_conversations(
    db: Session,
    repository_id: UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    """List conversation summaries for a repository, most recently updated first."""
    repository = db.get(Repository, repository_id)
    if repository is None:
        raise RepositoryNotFoundError()

    total = db.execute(
        text(
            "SELECT COUNT(*) FROM conversations WHERE repository_id = :rid"
        ),
        {"rid": str(repository_id)},
    ).scalar() or 0

    rows = db.execute(
        text(
            """
            SELECT id, title, created_at, updated_at,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id)
                   AS message_count
              FROM conversations c
             WHERE repository_id = :rid
             ORDER BY updated_at DESC
             LIMIT :limit OFFSET :offset
            """
        ),
        {"rid": str(repository_id), "limit": limit, "offset": offset},
    ).mappings().all()

    items = [
        {
            "id": str(row["id"]),
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "message_count": row["message_count"],
        }
        for row in rows
    ]
    return items, int(total)


def get_conversation(
    db: Session,
    conversation_id: UUID,
    repository_id: UUID,
) -> dict:
    """Get a conversation and its messages in chronological order."""
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise RepositoryNotFoundError()
    if repository_id is not None and conversation.repository_id != repository_id:
        from app.services.errors import RepositoryConflictError

        raise RepositoryConflictError(
            "The conversation does not belong to this repository."
        )

    messages = db.execute(
        text(
            """
            SELECT id, role, content, citations, created_at, sequence_number
              FROM messages
             WHERE conversation_id = :cid
             ORDER BY sequence_number ASC
            """
        ),
        {"cid": str(conversation_id)},
    ).mappings().all()

    return {
        "id": str(conversation.id),
        "repository_id": str(conversation.repository_id),
        "title": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": [
            {
                "id": str(row["id"]),
                "role": row["role"],
                "content": row["content"],
                "citations": row["citations"] or [],
                "created_at": row["created_at"],
            }
            for row in messages
        ],
    }


def delete_conversation(
    db: Session,
    conversation_id: UUID,
    repository_id: UUID,
) -> None:
    """Delete one conversation and its messages."""
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise RepositoryNotFoundError()
    if conversation.repository_id != repository_id:
        from app.services.errors import RepositoryConflictError

        raise RepositoryConflictError(
            "The conversation does not belong to this repository."
        )

    db.delete(conversation)
    db.commit()
