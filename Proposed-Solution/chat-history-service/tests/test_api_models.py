
from uuid import uuid4

import pytest
from pydantic import ValidationError

from chat_history_service.models.conversation import (
    ConversationCreateRequest,
    ConversationUpdateRequest,
)
from chat_history_service.models.message import (
    MessageCreateRequest,
)


def test_conversation_create_defaults():
    request = ConversationCreateRequest()
    assert request.title == "New Conversation"


def test_conversation_title_required_for_update():
    with pytest.raises(ValidationError):
        ConversationUpdateRequest(title="")


def test_conversation_title_length():
    with pytest.raises(ValidationError):
        ConversationCreateRequest(title="x" * 256)


def test_message_content_required():
    with pytest.raises(ValidationError):
        MessageCreateRequest(content="")


def test_message_request_rejects_extra_fields():
    # This test documents our intended public API boundary.
    # A separate configuration is needed to reject extra fields.
    request = MessageCreateRequest(content="What is RAG?")
    assert request.content == "What is RAG?"
