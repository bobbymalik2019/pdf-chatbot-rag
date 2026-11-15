
from pdf_ingestion_service.models.document import ExtractedPage
from pdf_ingestion_service.models.chunk import DocumentChunk


class DocumentChunker:

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(
        self,
        pages: list[ExtractedPage]
    ) -> list[DocumentChunk]:

        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for page in pages:

            text = page.normalized_text

            if not text or not text.strip():
                continue

            start = 0

            while start < len(text):

                end = min(
                    start + self.chunk_size,
                    len(text)
                )

                chunk_text = text[start:end]

                chunks.append(
                    DocumentChunk(
                        chunk_index=chunk_index,
                        text=chunk_text,
                        start_page=page.page_number,
                        end_page=page.page_number
                    )
                )

                chunk_index += 1

                if end == len(text):
                    break

                start = end - self.chunk_overlap

        return chunks
