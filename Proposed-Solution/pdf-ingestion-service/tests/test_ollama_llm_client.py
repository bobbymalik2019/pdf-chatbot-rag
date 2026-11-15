
import httpx
import pytest

from pdf_ingestion_service.application.rag_prompt_builder import (
    RAGPrompt,
    PromptMessage
)

from pdf_ingestion_service.llm.ollama_llm_client import (
    OllamaLLMClient,
    OllamaConnectionError,
    OllamaResponseError
)


@pytest.fixture
def client():
    return OllamaLLMClient(
        base_url="http://localhost:11434",
        model="llama3.1:latest"
    )


@pytest.fixture
def sample_prompt():
    return RAGPrompt(
        messages=[
            PromptMessage(
                role="system",
                content="Answer using the supplied evidence."
            ),
            PromptMessage(
                role="user",
                content="Which patent did Bobby file?"
            )
        ]
    )


def test_generate_success(
    client,
    sample_prompt,
    monkeypatch
):

    captured = {}

    def mock_post(url, json, timeout):

        captured["url"] = url
        captured["payload"] = json

        return httpx.Response(
            status_code=200,
            json={
                "model": "llama3.1:latest",
                "message": {
                    "role": "assistant",
                    "content": (
                        "Method and System for Analyzing "
                        "Rolling Element Bearing Systems [S1]"
                    )
                },
                "done": True,
                "prompt_eval_count": 120,
                "eval_count": 25
            },
            request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    result = client.generate(sample_prompt)

    assert "Rolling Element Bearing Systems" in result.answer
    assert result.model == "llama3.1:latest"
    assert result.prompt_tokens == 120
    assert result.generated_tokens == 25

    assert captured["url"] == (
        "http://localhost:11434/api/chat"
    )

    assert captured["payload"]["stream"] is False
    assert captured["payload"]["options"]["temperature"] == 0.1
    assert captured["payload"]["options"]["num_predict"] == 2048

    assert captured["payload"]["messages"][0]["role"] == "system"
    assert captured["payload"]["messages"][1]["role"] == "user"


def test_generate_timeout(
    client,
    sample_prompt,
    monkeypatch
):

    def mock_post(url, json, timeout):
        raise httpx.ReadTimeout("Request timed out")

    monkeypatch.setattr(httpx, "post", mock_post)

    with pytest.raises(OllamaConnectionError):
        client.generate(sample_prompt)


def test_generate_invalid_response(
    client,
    sample_prompt,
    monkeypatch
):

    def mock_post(url, json, timeout):

        return httpx.Response(
            status_code=200,
            json={
                "model": "llama3.1:latest",
                "message": {},
                "done": True
            },
            request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    with pytest.raises(OllamaResponseError):
        client.generate(sample_prompt)


def test_invalid_temperature(
    client,
    sample_prompt
):

    with pytest.raises(ValueError):
        client.generate(
            sample_prompt,
            temperature=3.0
        )
