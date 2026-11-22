
from uuid import UUID

from chat_history_service.persistence.conversation_repository import (
    ChatConversationRepository,
    conversation_repository,
)


class ChatConversationService:

    def __init__(
        self,
        repository: ChatConversationRepository,
    ):
        self._repository = repository

    def create_conversation(
        self,
        project_id: UUID,
        owner_id: str,
        title: str = "New Conversation",
    ) -> dict:
        if not owner_id or not owner_id.strip():
            raise ValueError("Owner ID is required")

        title = title.strip()

        if not title:
            raise ValueError("Conversation title cannot be empty")

        if len(title) > 255:
            raise ValueError(
                "Conversation title cannot exceed 255 characters"
            )

        return self._repository.create(
            project_id=project_id,
            owner_id=owner_id,
            title=title,
        )

    def get_conversation(
        self,
        conversation_id: UUID,
        owner_id: str,
    ) -> dict | None:
        return self._repository.get_by_id(
            conversation_id,
            owner_id,
        )

    def list_conversations(
        self,
        project_id: UUID,
        owner_id: str,
    ) -> list[dict]:
        return self._repository.list_by_project(
            project_id,
            owner_id,
        )

    def rename_conversation(
        self,
        conversation_id: UUID,
        owner_id: str,
        title: str,
    ) -> dict | None:
        title = title.strip()

        if not title:
            raise ValueError("Conversation title cannot be empty")

        if len(title) > 255:
            raise ValueError(
                "Conversation title cannot exceed 255 characters"
            )

        return self._repository.rename(
            conversation_id,
            owner_id,
            title,
        )

    def delete_conversation(
        self,
        conversation_id: UUID,
        owner_id: str,
    ) -> bool:
        return self._repository.delete(
            conversation_id,
            owner_id,
        )


conversation_service = ChatConversationService(
    repository=conversation_repository
)
