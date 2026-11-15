
import httpx

from pdf_ingestion_service.embeddings.embedding_generator import (
    EmbeddingGenerator
)


class OllamaEmbeddingGenerator(EmbeddingGenerator):

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        timeout: float = 120.0
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(
        self,
        texts: list[str]
    ) -> list[list[float]]:

        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise ValueError(
                "Cannot generate embeddings for empty text"
            )

        response = httpx.post(
            f"{self.base_url}/api/embed",
            json={
                "model": self.model,
                "input": texts
            },
            timeout=self.timeout
        )

        response.raise_for_status()

        embeddings = response.json()["embeddings"]

        if len(embeddings) != len(texts):
            raise ValueError(
                "Ollama returned an unexpected number of embeddings"
            )

        return embeddings
