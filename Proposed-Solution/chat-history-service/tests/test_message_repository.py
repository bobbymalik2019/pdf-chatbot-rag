
from uuid import uuid4

from chat_history_service.persistence.conversation_repository import (
    conversation_repository,
)
from chat_history_service.persistence.message_repository import (
    message_repository,
)


def test_message_repository():
    project_id = uuid4()
    owner_id = f"test-user-{uuid4()}"

    conversation = conversation_repository.create(
        project_id=project_id,
        owner_id=owner_id,
        title="Message Repository Test",
    )

    conversation_id = conversation["id"]

    try:
        # 1. Save user question
        question = message_repository.save_message(
            conversation_id=conversation_id,
            role="user",
            content="What is RAG?",
            status="pending",
        )

        assert question["role"] == "user"
        assert question["status"] == "pending"

        # 2. Save assistant answer with citations
        sources = {
            "citations": [
                {
                    "document_id": str(uuid4()),
                    "filename": "rag-guide.pdf",
                    "page_number": 3,
                    "marker": "[1]",
                }
            ]
        }

        answer = message_repository.save_message(
            conversation_id=conversation_id,
            role="assistant",
            content="RAG stands for Retrieval-Augmented Generation.",
            sources=sources,
        )

        assert answer["role"] == "assistant"
        assert answer["sources"] == sources

        # 3. Verify message retrieval
        messages = message_repository.list_messages(
            conversation_id
        )

        assert len(messages) == 2
        assert {m["id"] for m in messages} == {
            question["id"],
            answer["id"],
        }

        # 4. Update question status
        updated = message_repository.update_status(
            message_id=question["id"],
            status="completed",
        )

        assert updated["status"] == "completed"

        # 5. Verify cascade deletion
        assert conversation_repository.delete(
            conversation_id,
            owner_id,
        )

        conversation_id = None

        assert message_repository.list_messages(
            conversation["id"]
        ) == []

    finally:
        if conversation_id is not None:
            conversation_repository.delete(
                conversation_id,
                owner_id,
            )
