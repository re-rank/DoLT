"""Embedding Provider 추상 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """텍스트 리스트를 임베딩 벡터 리스트로 변환한다."""

    @abstractmethod
    def model_name(self) -> str:
        """사용 중인 모델명."""

    @abstractmethod
    def dimension(self) -> int:
        """출력 벡터 차원 수."""
