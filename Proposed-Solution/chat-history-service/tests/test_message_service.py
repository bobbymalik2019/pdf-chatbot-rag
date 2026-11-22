
from uuid import uuid4
from unittest.mock import Mock

import pytest

from chat_history_service.services.message_service import (
    ChatMessageService,
)


@pytest.fixture
def repository():
    return Mock()


@pytest.fixture
def service(repository):
    return ChatMessageService(repository)


def test_save_user_message(service, repository):
    conversation_id = uuid4()
    repository.save_message.return_value = {
        "id": uuid4(),
        "role": "user",
        "content": "What is RAG?",
    }

    result = service.save_message(
        conversation_id=conversation_id,
        role="user",
        content="  What is RAG?  ",
    )

    assert result["content"] == "What is RAG?"
    repository.save_message.assert_called_once_with(
        conversation_id=conversation_id,
        role="user",
        content="What is RAG?",
        sources=None,
        status="completed",
    )


def test_save_assistant_answer(service, repository):
    sources = {
        "citations": [
            {
                "filename": "rag-guide.pdf",
                "page_number": 3,
                "marker": "[1]",
            }
        ]
    }

    service.save_message(
        conversation_id=uuid4(),
        role="assistant",
        content="RAG is Retrieval-Augmented Generation.",
        sources=sources,
    )

    assert (
        repository.save_message.call_args.kwargs["sources"]
        == sources
    )


@pytest.mark.parametrize("role", ["system", "admin", ""])
def test_invalid_role_rejected(service, repository, role):
    with pytest.raises(ValueError, match="Invalid message role"):
        service.save_message(
            conversation_id=uuid4(),
            role=role,
            content="Test",
        )

    repository.save_message.assert_not_called()


@pytest.mark.parametrize("status", ["unknown", "processing", ""])
def test_invalid_status_rejected(service, repository, status):
    with pytest.raises(ValueError, match="Invalid message status"):
        service.save_message(
            conversation_id=uuid4(),
            role="user",
            content="Test",
            status=status,
        )

    repository.save_message.assert_not_called()


def test_empty_message_rejected(service, repository):
    with pytest.raises(ValueError, match="cannot be empty"):
        service.save_message(
            conversation_id=uuid4(),
            role="user",
            content="   ",
        )

    repository.save_message.assert_not_called()


def test_invalid_sources_rejected(service, repository):
    with pytest.raises(ValueError, match="Sources"):
        service.save_message(
            conversation_id=uuid4(),
            role="assistant",
            content="Answer",
            sources="invalid",
        )

    repository.save_message.assert_not_called()


def test_list_messages(service, repository):
    conversation_id = uuid4()
    repository.list_messages.return_value = [
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Answer"},
    ]

    result = service.list_messages(conversation_id)

    assert len(result) == 2
    repository.list_messages.assert_called_once_with(
        conversation_id
    )


def test_update_message_status(service, repository):
    message_id = uuid4()
    repository.update_status.return_value = {
        "id": message_id,
        "status": "completed",
    }

    result = service.update_status(
        message_id,
        "completed",
    )

    assert result["status"] == "completed"
    repository.update_status.assert_called_once_with(
        message_id=message_id,
        status="completed",
    )


def test_invalid_status_update_rejected(service, repository):
    with pytest.raises(ValueError, match="Invalid message status"):
        service.update_status(uuid4(), "unknown")

    repository.update_status.assert_not_called()
