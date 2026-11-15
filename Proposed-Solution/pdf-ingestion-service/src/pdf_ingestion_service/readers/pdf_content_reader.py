
# from matplotlib import text

import pymupdf

from pdf_ingestion_service.readers.content_reader import ContentReader
from pdf_ingestion_service.models.document import ExtractedPage


class PDFContentReader(ContentReader):

    def extract(self, content: bytes) -> list[ExtractedPage]:

        pages = []

        with pymupdf.open(
            stream=content,
            filetype="pdf"
        ) as document:

            for page_number ,page in enumerate(document, start=1):
                extracted = page.get_text("text")
                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        raw_text=extracted,
                        normalized_text=extracted  # Placeholder, will be normalized later
                    )
                )

        return pages
