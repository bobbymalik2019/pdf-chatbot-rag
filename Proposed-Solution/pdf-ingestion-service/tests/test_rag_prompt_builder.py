
from uuid import uuid4

import pytest

from pdf_ingestion_service.application.rag_context_builder import (
    RAGContext,
    ContextSource
)

from pdf_ingestion_service.application.rag_prompt_builder import (
    RAGPromptBuilder
)


@pytest.fixture
def prompt_builder():
    return RAGPromptBuilder()


@pytest.fixture
def sample_context():

    return RAGContext(
        context_text=(
            "[S1]\n"
            "Document: Bobby_Malik-CV.pdf\n"
            "Page: Unknown\n"
            "Content:\n"
            "Patent: Method and System for Analyzing "
            "Rolling Element Bearing Systems\n"
            "US 2009/0306955 A1"
        ),
        sources=[
            ContextSource(
                marker="S1",
                chunk_id = 1,
                document_id=uuid4(),
                filename="Bobby_Malik-CV.pdf",
                page_number=None
            )
        ],
        included_chunks=1,
        truncated=False
    )


def test_build_prompt(prompt_builder, sample_context):

    prompt = prompt_builder.build(
        question="Which patent did Bobby file?",
        context=sample_context
    )

    assert len(prompt.messages) == 2

    assert prompt.messages[0].role == "system"
    assert prompt.messages[1].role == "user"

    assert "Which patent did Bobby file?" in (
        prompt.messages[1].content
    )

    assert "US 2009/0306955 A1" in (
        prompt.messages[1].content
    )

    assert "[S1]" in prompt.messages[1].content


def test_empty_question(prompt_builder, sample_context):

    with pytest.raises(ValueError):
        prompt_builder.build(
            question="   ",
            context=sample_context
        )


def test_no_context(prompt_builder):

    empty_context = RAGContext(
        context_text="",
        sources=[],
        included_chunks=0
    )

    prompt = prompt_builder.build(
        question="Which patent did Bobby file?",
        context=empty_context
    )

    assert "No relevant document context" in (
        prompt.messages[1].content
    )


def test_system_prompt_contains_grounding_rules(
    prompt_builder,
    sample_context
):

    prompt = prompt_builder.build(
        question="Explain the patent.",
        context=sample_context
    )

    system_message = prompt.messages[0].content

    assert "Do not invent" in system_message
    assert "source citations" in system_message.lower()
    assert "untrusted data" in system_message.lower()
