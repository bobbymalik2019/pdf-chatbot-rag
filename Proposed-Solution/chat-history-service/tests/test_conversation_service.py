
from uuid import uuid4
from unittest.mock import Mock

import pytest

from chat_history_service.services.conversation_service import (
    ChatConversationService,
)


def test_create_conversation():
    repository = Mock()
    repository.create.return_value = {"title": "RAG Discussion"}

    service = ChatConversationService(repository)

    result = service.create_conversation(
        project_id=uuid4(),
        owner_id="test-user",
        title="  RAG Discussion  ",
    )

    assert result["title"] == "RAG Discussion"
    assert repository.create.call_args.kwargs["title"] == (
        "RAG Discussion"
    )


def test_empty_title_rejected():
    service = ChatConversationService(Mock())

    with pytest.raises(ValueError):
        service.create_conversation(
            project_id=uuid4(),
            owner_id="test-user",
            title="   ",
        )


def test_missing_owner_rejected():
    service = ChatConversationService(Mock())

    with pytest.raises(ValueError):
        service.create_conversation(
            project_id=uuid4(),
            owner_id="",
        )


def test_rename_conversation():
    repository = Mock()
    repository.rename.return_value = {"title": "Updated"}

    service = ChatConversationService(repository)

    result = service.rename_conversation(
        conversation_id=uuid4(),
        owner_id="test-user",
        title=" Updated ",
    )

    assert result["title"] == "Updated"


def test_delete_conversation():
    repository = Mock()
    repository.delete.return_value = True

    service = ChatConversationService(repository)

    assert service.delete_conversation(
        conversation_id=uuid4(),
        owner_id="test-user",
    ) is True
