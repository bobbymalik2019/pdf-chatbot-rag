
from uuid import uuid4

from chat_history_service.persistence.conversation_repository import (
    conversation_repository,
)


def test_conversation_crud():
    project_id = uuid4()
    owner_id = f"test-user-{uuid4()}"

    conversation_id = None

    try:
        # CREATE
        created = conversation_repository.create(
            project_id=project_id,
            owner_id=owner_id,
            title="RAG Discussion",
        )

        conversation_id = created["id"]

        assert created["project_id"] == project_id
        assert created["owner_id"] == owner_id
        assert created["title"] == "RAG Discussion"

        # READ
        fetched = conversation_repository.get_by_id(
            conversation_id, owner_id
        )
        assert fetched["id"] == conversation_id

        # LIST
        conversations = conversation_repository.list_by_project(
            project_id, owner_id
        )
        assert len(conversations) == 1

        # UPDATE
        updated = conversation_repository.rename(
            conversation_id,
            owner_id,
            "Updated RAG Discussion",
        )
        assert updated["title"] == "Updated RAG Discussion"

        # OWNERSHIP ISOLATION
        other_user = f"other-user-{uuid4()}"

        assert conversation_repository.get_by_id(
            conversation_id, other_user
        ) is None

        assert conversation_repository.rename(
            conversation_id, other_user, "Unauthorized"
        ) is None

        assert conversation_repository.delete(
            conversation_id, other_user
        ) is False

        # DELETE
        assert conversation_repository.delete(
            conversation_id, owner_id
        ) is True

        conversation_id = None

    finally:
        if conversation_id is not None:
            conversation_repository.delete(
                conversation_id, owner_id
            )
