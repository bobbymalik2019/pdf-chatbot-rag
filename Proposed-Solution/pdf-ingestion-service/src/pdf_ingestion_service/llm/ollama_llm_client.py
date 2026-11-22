
import logging
import time

import httpx

from pydantic import BaseModel, Field, ValidationError

from pdf_ingestion_service.config.settings import settings
from pdf_ingestion_service.application.rag_prompt_builder import (
    RAGPrompt
)


logger = logging.getLogger(__name__)


# --------------------------------------------
# Response model
# --------------------------------------------

class LLMResponse(BaseModel):

    answer: str = Field(min_length=1)
    model: str

    prompt_tokens: int | None = None
    generated_tokens: int | None = None

    duration_seconds: float


# --------------------------------------------
# Exceptions
# --------------------------------------------

class OllamaLLMError(Exception):
    """Base exception for Ollama LLM failures."""


class OllamaConnectionError(OllamaLLMError):
    pass


class OllamaResponseError(OllamaLLMError):
    pass


# --------------------------------------------
# Ollama LLM Client
# --------------------------------------------

class OllamaLLMClient:

    def __init__(
        self,
        base_url: str,
        model: str = "llama3.1:latest",
        timeout_seconds: float = 300
    ):

        if not base_url.strip():
            raise ValueError("Ollama base_url cannot be empty")

        if not model.strip():
            raise ValueError("Ollama model cannot be empty")

        if timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        prompt: RAGPrompt,
        temperature: float = 0.1,
        max_output_tokens: int = 2048
    ) -> LLMResponse:

        if not 0.0 <= temperature <= 2.0:
            raise ValueError(
                "temperature must be between 0 and 2"
            )

        if max_output_tokens <= 0:
            raise ValueError(
                "max_output_tokens must be positive"
            )

        if not prompt.messages:
            raise ValueError(
                "Prompt must contain at least one message"
            )

        payload = {
            "model": self.model,
            "messages": [
                message.model_dump()
                for message in prompt.messages
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_output_tokens
            }
        }

        url = f"{self.base_url}/api/chat"

        logger.info(
            "OLLAMA GENERATION START | "
            "model=%s | messages=%d | "
            "temperature=%.2f | max_tokens=%d",
            self.model,
            len(prompt.messages),
            temperature,
            max_output_tokens
        )

        start_time = time.perf_counter()

        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self.timeout_seconds
            )

            response.raise_for_status()

        except httpx.TimeoutException as exc:

            logger.error(
                "OLLAMA GENERATION TIMEOUT | model=%s",
                self.model
            )

            raise OllamaConnectionError(
                "Ollama request timed out"
            ) from exc

        except httpx.ConnectError as exc:

            logger.error(
                "OLLAMA CONNECTION FAILED | model=%s",
                self.model
            )

            raise OllamaConnectionError(
                "Unable to connect to Ollama"
            ) from exc

        except httpx.HTTPStatusError as exc:

            logger.error(
                "OLLAMA HTTP ERROR | status=%d",
                exc.response.status_code
            )

            raise OllamaResponseError(
                f"Ollama returned HTTP "
                f"{exc.response.status_code}"
            ) from exc

        except httpx.RequestError as exc:

            logger.error(
                "OLLAMA REQUEST FAILED | model=%s",
                self.model
            )

            raise OllamaConnectionError(
                "Ollama request failed"
            ) from exc

        duration = time.perf_counter() - start_time

        try:
            data = response.json()

            message = data["message"]
            answer = message["content"]

            if not isinstance(answer, str) or not answer.strip():
                raise ValueError(
                    "Ollama returned empty answer"
                )

            if data.get("done") is not True:
                raise ValueError(
                    "Ollama response is not complete"
                )

            result = LLMResponse(
                answer=answer.strip(),
                model=data["model"],
                prompt_tokens=data.get("prompt_eval_count"),
                generated_tokens=data.get("eval_count"),
                duration_seconds=duration
            )

        except (
            ValueError,
            TypeError,
            KeyError,
            ValidationError
        ) as exc:

            logger.error(
                "OLLAMA INVALID RESPONSE | model=%s",
                self.model
            )

            raise OllamaResponseError(
                "Invalid response received from Ollama"
            ) from exc

        logger.info(
            "OLLAMA GENERATION COMPLETE | "
            "model=%s | duration=%.2fs | "
            "prompt_tokens=%s | generated_tokens=%s",
            result.model,
            result.duration_seconds,
            result.prompt_tokens,
            result.generated_tokens
        )

        return result


# --------------------------------------------
# Shared module-level instance
# --------------------------------------------

ollama_llm_client = OllamaLLMClient(
    base_url=settings.ollama_base_url,
    model=settings.ollama_llm_model
)
