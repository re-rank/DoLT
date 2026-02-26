"""Embedding 모듈 테스트."""

from __future__ import annotations

import pytest

from dolt.embedding.base import BaseEmbeddingProvider
from dolt.errors import APIKeyMissingError


def test_openai_provider_requires_api_key(monkeypatch):
    """OPENAI_API_KEY가 없으면 APIKeyMissingError를 발생시킨다."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from dolt.embedding.openai_provider import OpenAIEmbeddingProvider

    with pytest.raises(APIKeyMissingError):
        OpenAIEmbeddingProvider()


def test_openai_provider_with_api_key(monkeypatch):
    """API 키를 직접 전달하면 정상 생성된다."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from dolt.embedding.openai_provider import OpenAIEmbeddingProvider

    provider = OpenAIEmbeddingProvider(api_key="test-key-123")
    assert provider.model_name() == "text-embedding-3-small"
    assert provider.dimension() == 1536


def test_openai_provider_custom_model(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from dolt.embedding.openai_provider import OpenAIEmbeddingProvider

    provider = OpenAIEmbeddingProvider(
        model="text-embedding-3-large", api_key="test-key"
    )
    assert provider.model_name() == "text-embedding-3-large"
    assert provider.dimension() == 3072


def test_cohere_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("COHERE_API_KEY", raising=False)

    from dolt.embedding.cohere_provider import CohereEmbeddingProvider

    with pytest.raises(APIKeyMissingError):
        CohereEmbeddingProvider()


def test_cohere_provider_with_api_key(monkeypatch):
    monkeypatch.delenv("COHERE_API_KEY", raising=False)

    from dolt.embedding.cohere_provider import CohereEmbeddingProvider

    provider = CohereEmbeddingProvider(api_key="test-key")
    assert provider.model_name() == "embed-multilingual-v3.0"
    assert provider.dimension() == 1024


def test_base_embedding_provider_is_abstract():
    """BaseEmbeddingProvider는 직접 인스턴스화할 수 없다."""
    with pytest.raises(TypeError):
        BaseEmbeddingProvider()
