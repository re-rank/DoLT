"""Parser 추상 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from dolt.models.document import StructuredDocument


class BaseParser(ABC):
    """모든 파서가 구현해야 하는 추상 인터페이스."""

    @abstractmethod
    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        """파일을 파싱하여 StructuredDocument를 반환한다."""

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """처리 가능한 확장자 목록 (예: ['.pdf'])."""
