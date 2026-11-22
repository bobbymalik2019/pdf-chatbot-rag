
from uuid import uuid4

from pdf_ingestion_service.application.rag_context_builder import (
    RAGContextBuilder,
    RetrievedChunk
)


def test_context_builder():

    document_id = uuid4()
    chunk_id = 1

    retrieved_chunks = [
        RetrievedChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            filename="Bobby_Malik-CV.pdf",
            page_number=2,
            content=(
                "Patents & Innovations\n"
                "US Patent Holder: Method and System for "
                "Analyzing Rolling Element Bearing Systems "
                "- US 2009/0306955 A1\n"
                "Patent Filed: Utility Patent "
                "(Docket No. H0017060)"
            ),
            similarity_score=0.91
        )
    ]

    builder = RAGContextBuilder(
        max_context_chars=12000
    )

    result = builder.build(retrieved_chunks)

    print(result.context_text)
    print(result.model_dump_json(indent=2))

    assert result.included_chunks == 1
    assert result.sources[0].marker == "S1"
    assert result.sources[0].chunk_id == chunk_id
    assert result.sources[0].page_number == 2
    assert "[S1]" in result.context_text
    assert result.truncated is False

    print("RAGContextBuilder test passed")


def test_context_budget():

    builder = RAGContextBuilder(
        max_context_chars=50
    )

    result = builder.build([
        RetrievedChunk(
            chunk_id=1,
            document_id=uuid4(),
            filename="test.pdf",
            content="A" * 500
        )
    ])

    assert result.included_chunks == 0
    assert result.truncated is True
    assert result.context_text == ""

    print("Context budget test passed")


if __name__ == "__main__":
    test_context_builder()
    test_context_budget()
