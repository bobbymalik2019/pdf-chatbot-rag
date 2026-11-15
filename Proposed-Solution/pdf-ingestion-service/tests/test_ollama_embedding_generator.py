
import httpx
import pytest

from pdf_ingestion_service.embeddings.ollama_embedding_generator import (
    OllamaEmbeddingGenerator
)


def test_generate_embeddings(monkeypatch):

    def mock_post(url, json, timeout):
        assert url == "http://localhost:11434/api/embed"
        assert json["model"] == "nomic-embed-text"
        assert json["input"] == ["Java", "Python"]

        return httpx.Response(
            status_code=200,
            json={
                "embeddings": [
                    [0.1, 0.2, 0.3],
                    [0.4, 0.5, 0.6]
                ]
            },
            request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    generator = OllamaEmbeddingGenerator()

    result = generator.generate(["Java", "Python"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3]
    assert result[1] == [0.4, 0.5, 0.6]


def test_empty_input():

    generator = OllamaEmbeddingGenerator()

    assert generator.generate([]) == []


def test_blank_text_rejected():

    generator = OllamaEmbeddingGenerator()

    with pytest.raises(ValueError):
        generator.generate(["   "])


def test_embedding_count_mismatch(monkeypatch):

    def mock_post(url, json, timeout):
        return httpx.Response(
            status_code=200,
            json={"embeddings": [[0.1, 0.2, 0.3]]},
            request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    generator = OllamaEmbeddingGenerator()

    with pytest.raises(ValueError):
        generator.generate(["Java", "Python"])
