
from abc import ABC, abstractmethod
from pdf_ingestion_service.models.document import ExtractedPage


class ContentReader(ABC):

    @abstractmethod
    def extract(self, content: bytes) -> list[ExtractedPage]:
        """
        Extract text from a document.

        Returns a list of extracted pages.
        """
        pass
