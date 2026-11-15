
import pytest

from pdf_ingestion_service.models.document import ExtractedPage
from pdf_ingestion_service.processing.document_chunker import DocumentChunker


def test_document_chunker_with_overlap():

    pages = [
        ExtractedPage(
            page_number=1,
            raw_text="ABCDEFGHIJKLMNO",
            normalized_text="ABCDEFGHIJKLMNO"
        )
    ]

    chunker = DocumentChunker(
        chunk_size=10,
        chunk_overlap=3
    )

    chunks = chunker.chunk(pages)

    assert len(chunks) == 2

    assert chunks[0].chunk_index == 0
    assert chunks[0].text == "ABCDEFGHIJ"
    assert chunks[0].start_page == 1
    assert chunks[0].end_page == 1

    assert chunks[1].chunk_index == 1
    assert chunks[1].text == "HIJKLMNO"
    assert chunks[1].start_page == 1
    assert chunks[1].end_page == 1


def test_document_chunker_skips_empty_pages():

    pages = [
        ExtractedPage(
            page_number=1,
            raw_text="",
            normalized_text=""
        ),
        ExtractedPage(
            page_number=2,
            raw_text="Hello World",
            normalized_text="Hello World"
        )
    ]

    chunker = DocumentChunker(
        chunk_size=20,
        chunk_overlap=5
    )

    chunks = chunker.chunk(pages)

    assert len(chunks) == 1
    assert chunks[0].text == "Hello World"
    assert chunks[0].start_page == 2


def test_invalid_chunk_configuration():

    with pytest.raises(ValueError):
        DocumentChunker(
            chunk_size=100,
            chunk_overlap=100
        )
