
from uuid import UUID

from chat_history_service.persistence.message_repository import (
    ChatMessageRepository,
    message_repository,
)


class ChatMessageService:

    VALID_ROLES = {"user", "assistant"}
    VALID_STATUSES = {"pending", "completed", "failed"}

    def __init__(
        self,
        repository: ChatMessageRepository,
    ):
        self._repository = repository

    def save_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        sources: dict | list | None = None,
        status: str = "completed",
    ) -> dict:
        if role not in self.VALID_ROLES:
            raise ValueError("Invalid message role")

        if status not in self.VALID_STATUSES:
            raise ValueError("Invalid message status")

        if not content or not content.strip():
            raise ValueError("Message content cannot be empty")

        if sources is not None and not isinstance(
            sources, (dict, list)
        ):
            raise ValueError("Sources must be a dictionary or list")

        return self._repository.save_message(
            conversation_id=conversation_id,
            role=role,
            content=content.strip(),
            sources=sources,
            status=status,
        )

    def list_messages(
        self,
        conversation_id: UUID,
    ) -> list[dict]:
        return self._repository.list_messages(
            conversation_id
        )

    def update_status(
        self,
        message_id: UUID,
        status: str,
    ) -> dict | None:
        if status not in self.VALID_STATUSES:
            raise ValueError("Invalid message status")

        return self._repository.update_status(
            message_id=message_id,
            status=status,
        )


message_service = ChatMessageService(
    repository=message_repository
)
