import logging

import httpx

from pdf_ingestion_service.config.settings import settings

logger = logging.getLogger(__name__)


class OllamaTextGenerator:

    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_llm_model
        self.timeout = 120.0

    def generate(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        logger.info(
            "OLLAMA GENERATION START | model=%s",
            self.model,
        )

        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        answer = response.json()["response"]

        logger.info(
            "OLLAMA GENERATION COMPLETE | model=%s",
            self.model,
        )

        return answer