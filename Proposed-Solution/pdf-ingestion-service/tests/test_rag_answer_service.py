
from uuid import uuid4
from unittest.mock import Mock

import pytest

from pdf_ingestion_service.application.rag_context_builder import (
    RAGContextBuilder
)

from pdf_ingestion_service.application.rag_prompt_builder import (
    RAGPromptBuilder
)

from pdf_ingestion_service.llm.ollama_llm_client import (
    LLMResponse
)

from pdf_ingestion_service.services.rag_answer_service import (
    RAGAnswerService
)


@pytest.fixture
def project_id():
    return uuid4()


@pytest.fixture
def owner_id():
    return uuid4()


@pytest.fixture
def search_results():
    return [
        {
            "chunk_id": uuid4(),
            "document_id": uuid4(),
            "filename": "Bobby_Malik-CV.pdf",
            "chunk_index": 0,
            "text": (
                "Patent: Method and System for Analyzing "
                "Rolling Element Bearing Systems. "
                "Publication US 2009/0306955 A1."
            ),
            "start_page": 2,
            "end_page": 2,
            "similarity": 0.91
        }
    ]


@pytest.fixture
def semantic_search_service(search_results):
    service = Mock()
    service.search.return_value = search_results
    return service


@pytest.fixture
def llm_client():
    client = Mock()
    client.generate.return_value = LLMResponse(
        answer=(
            "The patent is Method and System for "
            "Analyzing Rolling Element Bearing Systems [S1]."
        ),
        model="llama3.1:latest",
        prompt_tokens=320,
        generated_tokens=58,
        duration_seconds=10.17
    )
    return client


@pytest.fixture
def service(semantic_search_service, llm_client):
    return RAGAnswerService(
        semantic_search_service=semantic_search_service,
        context_builder=RAGContextBuilder(),
        prompt_builder=RAGPromptBuilder(),
        llm_client=llm_client
    )


def test_generate_answer(
    service,
    project_id,
    owner_id,
    llm_client
):
    result = service.answer(
        project_id=project_id,
        owner_id=owner_id,
        question="Which patent did Bobby file?"
    )

    assert result.project_id == project_id
    assert result.retrieved_chunks == 1
    assert result.included_chunks == 1
    assert len(result.sources) == 1
    assert result.sources[0].marker == "S1"
    assert result.model == "llama3.1:latest"

    llm_client.generate.assert_called_once()


def test_no_retrieval_results(
    service,
    semantic_search_service,
    llm_client,
    project_id,
    owner_id
):
    semantic_search_service.search.return_value = []

    result = service.answer(
        project_id=project_id,
        owner_id=owner_id,
        question="What is the patent?"
    )

    assert result.answer == RAGAnswerService.NO_ANSWER
    assert result.sources == []
    assert result.retrieved_chunks == 0

    llm_client.generate.assert_not_called()


def test_invalid_citation_removed(
    service,
    llm_client,
    project_id,
    owner_id
):
    llm_client.generate.return_value = LLMResponse(
        answer="The patent concerns bearing systems [S99].",
        model="llama3.1:latest",
        duration_seconds=0.5
    )

    result = service.answer(
        project_id=project_id,
        owner_id=owner_id,
        question="Which patent?"
    )

    assert "[S99]" not in result.answer
    assert result.sources == []


def test_empty_question(
    service,
    semantic_search_service,
    project_id,
    owner_id
):
    with pytest.raises(ValueError):
        service.answer(
            project_id=project_id,
            owner_id=owner_id,
            question="   "
        )

    semantic_search_service.search.assert_not_called()


def test_project_id_and_owner_forwarded(
    service,
    semantic_search_service,
    project_id,
    owner_id
):
    service.answer(
        project_id=project_id,
        owner_id=owner_id,
        question="Which patent?",
        top_k=3
    )

    semantic_search_service.search.assert_called_once_with(
        project_id=project_id,
        owner_id=owner_id,
        query="Which patent?",
        top_k=3
    )
