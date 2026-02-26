"""Exporter 추상 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from dolt.models.chunk import EmbeddedChunk


class ExportResult(BaseModel):
    total: int
    success: int
    failed: int
    errors: list[str] = Field(default_factory=list)
    destination: str


class BaseExporter(ABC):
    @abstractmethod
    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        """임베딩 완료된 청크를 목적지로 내보낸다."""

    @abstractmethod
    def validate_connection(self) -> bool:
        """연결 상태를 확인한다."""
