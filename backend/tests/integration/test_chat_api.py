"""Phase 4 chat API integration tests."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.models import Conversation, Message, Repository
from app.services import chat_service, rag_service
from app.services.rag_service import RagAnswer, ValidatedCitation


def _create_ready_repository(db_session, index_version="index-v1", commit_sha="abc123"):
    repository = Repository(
        github_url="https://github.com/octocat/hello-world",
        repository_name="hello-world",
        owner_name="octocat",
        status="ready",
        active_index_version=index_version,
        active_commit_sha=commit_sha,
    )
    db_session.add(repository)
    db_session.flush()
    return repository


def _mock_rag_answer(monkeypatch, answer_text="The answer is here.", citations=None, insufficient=False):
    if citations is None:
        citations = []
    validated_citations = [
        ValidatedCitation(
            source_id=c["source_id"],
            file_path=c["file_path"],
            symbol_name=c["symbol_name"],
            start_line=c["start_line"],
            end_line=c["end_line"],
            snippet=c["snippet"],
            commit_sha=c["commit_sha"],
        )
        for c in citations
    ]

    def fake_answer_question(*, repository, question, conversation_id=None):
        return RagAnswer(
            conversation_id=uuid4(),
            message_id=uuid4(),
            answer=answer_text,
            citations=validated_citations,
            insufficient_evidence=insufficient,
        )

    monkeypatch.setattr(rag_service, "answer_question", fake_answer_question)


def test_ask_question_creates_new_conversation(client, db_session, monkeypatch):
    repository = _create_ready_repository(db_session)
    _mock_rag_answer(
        monkeypatch,
        answer_text="Auth is handled by the auth service.",
        citations=[
            {
                "source_id": "source-1",
                "file_path": "src/auth/service.py",
                "symbol_name": "authenticate_user",
                "start_line": 12,
                "end_line": 34,
                "snippet": "def authenticate_user(username, password): ...",
                "commit_sha": "abc123",
            }
        ],
        insufficient=False,
    )

    response = client.post(
        f"/api/chat/{repository.id}",
        json={"question": "Where is authentication handled?", "conversation_id": None},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Auth is handled by the auth service."
    assert body["insufficient_evidence"] is False
    assert len(body["citations"]) == 1
    assert body["citations"][0]["source_id"] == "source-1"
    assert body["citations"][0]["file_path"] == "src/auth/service.py"
    assert body["citations"][0]["commit_sha"] == "abc123"
    assert "conversation_id" in body
    assert "message_id" in body

    # Verify the conversation was created in the database.
    factory = sessionmaker(bind=db_session.get_bind())
    session = factory()
    try:
        conv = session.get(Conversation, UUID(body["conversation_id"]))
        assert conv is not None
        assert conv.repository_id == repository.id
        assert conv.title == "Where is authentication handled?"
        messages = session.query(Message).filter_by(conversation_id=conv.id).all()
        assert len(messages) == 2  # user + assistant
    finally:
        session.close()


def test_ask_question_continues_existing_conversation(client, db_session, monkeypatch):
    repository = _create_ready_repository(db_session)
    conversation = Conversation(
        repository_id=repository.id, title="Existing conversation"
    )
    db_session.add(conversation)
    db_session.flush()
    conversation_id = conversation.id
    db_session.commit()

    _mock_rag_answer(monkeypatch, answer_text="Continuing the answer.")

    response = client.post(
        f"/api/chat/{repository.id}",
        json={"question": "Follow-up question", "conversation_id": str(conversation_id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] == str(conversation_id)
    assert body["answer"] == "Continuing the answer."


def test_ask_question_repository_not_found(client):
    response = client.post(
        f"/api/chat/{uuid4()}",
        json={"question": "Hello"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "repository_not_found"


def test_ask_question_repository_not_ready(client, db_session):
    repository = Repository(
        github_url="https://github.com/octocat/hello-world",
        repository_name="hello-world",
        owner_name="octocat",
        status="indexing",  # not ready
        active_index_version=None,
    )
    db_session.add(repository)
    db_session.flush()
    db_session.commit()

    response = client.post(
        f"/api/chat/{repository.id}",
        json={"question": "Hello"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "repository_conflict"


def test_ask_question_validation_error(client, db_session):
    repository = _create_ready_repository(db_session)

    # Empty question body -> 422 validation error
    response = client.post(
        f"/api/chat/{repository.id}",
        json={"question": "   "},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_list_conversations_empty(client, db_session):
    repository = _create_ready_repository(db_session)
    response = client.get(f"/api/chat/{repository.id}/history")
    assert response.status_code == 200
    body = response.json()
    assert body["repository_id"] == str(repository.id)
    assert body["items"] == []
    assert body["pagination"]["total"] == 0
    assert body["pagination"]["has_more"] is False


def test_list_conversations_with_data(client, db_session):
    repository = _create_ready_repository(db_session)
    conv1 = Conversation(repository_id=repository.id, title="First conversation")
    conv2 = Conversation(repository_id=repository.id, title="Second conversation")
    db_session.add_all([conv1, conv2])
    db_session.flush()
    # Add messages to set updated_at ordering
    msg1 = Message(
        conversation_id=conv1.id, role="user", content="Q1", sequence_number=1, citations=[]
    )
    msg2 = Message(
        conversation_id=conv2.id, role="user", content="Q2", sequence_number=1, citations=[]
    )
    db_session.add_all([msg1, msg2])
    db_session.commit()

    response = client.get(f"/api/chat/{repository.id}/history")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    # Most recently updated first
    titles = [item["title"] for item in body["items"]]
    assert "Second conversation" in titles
    assert "First conversation" in titles


def test_get_conversation(client, db_session):
    repository = _create_ready_repository(db_session)
    conversation = Conversation(
        repository_id=repository.id, title="Test conversation"
    )
    db_session.add(conversation)
    db_session.flush()
    msg = Message(
        conversation_id=conversation.id,
        role="user",
        content="Hello?",
        sequence_number=1,
        citations=[],
    )
    db_session.add(msg)
    db_session.commit()

    response = client.get(
        f"/api/chat/conversations/{conversation.id}",
        params={"repository_id": str(repository.id)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(conversation.id)
    assert body["title"] == "Test conversation"
    assert len(body["messages"]) == 1
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][0]["content"] == "Hello?"


def test_get_conversation_wrong_repository(client, db_session):
    repository = _create_ready_repository(db_session)
    conversation = Conversation(
        repository_id=repository.id, title="Test"
    )
    db_session.add(conversation)
    db_session.flush()
    db_session.commit()

    response = client.get(
        f"/api/chat/conversations/{conversation.id}",
        params={"repository_id": str(uuid4())},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "repository_conflict"


def test_delete_conversation(client, db_session):
    repository = _create_ready_repository(db_session)
    conversation = Conversation(
        repository_id=repository.id, title="To delete"
    )
    db_session.add(conversation)
    db_session.flush()
    conv_id = conversation.id
    db_session.commit()

    response = client.delete(
        f"/api/chat/conversations/{conv_id}",
        params={"repository_id": str(repository.id)},
    )
    assert response.status_code == 204

    # Verify it's gone.
    factory = sessionmaker(bind=db_session.get_bind())
    session = factory()
    try:
        assert session.get(Conversation, conv_id) is None
    finally:
        session.close()


def test_ask_question_insufficient_evidence(client, db_session, monkeypatch):
    repository = _create_ready_repository(db_session)
    _mock_rag_answer(
        monkeypatch,
        answer_text="I could not find enough evidence.",
        citations=[],
        insufficient=True,
    )

    response = client.post(
        f"/api/chat/{repository.id}",
        json={"question": "Obscure question about nothing"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["insufficient_evidence"] is True
    assert body["citations"] == []
    assert "could not find enough evidence" in body["answer"]
