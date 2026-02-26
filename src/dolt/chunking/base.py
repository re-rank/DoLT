"""Chunker 추상 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from dolt.models.chunk import Chunk
from dolt.models.config import ChunkConfig
from dolt.models.document import StructuredDocument


class BaseChunker(ABC):
    """모든 청커가 구현해야 하는 추상 인터페이스."""

    def __init__(self, config: ChunkConfig) -> None:
        self.config = config

    @abstractmethod
    def chunk(self, doc: StructuredDocument) -> list[Chunk]:
        """StructuredDocument를 Chunk 리스트로 분할한다."""
