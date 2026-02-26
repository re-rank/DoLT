"""메타데이터 플러그인 추상 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from dolt.models.chunk import Chunk
from dolt.models.document import StructuredDocument


class MetadataPlugin(ABC):
    """커스텀 메타데이터 플러그인의 추상 인터페이스."""

    @property
    @abstractmethod
    def name(self) -> str:
        """플러그인 이름 (고유 식별자)."""

    @abstractmethod
    def enrich(self, chunk: Chunk, doc: StructuredDocument) -> dict:
        """청크에 추가할 메타데이터 딕셔너리를 반환한다."""
