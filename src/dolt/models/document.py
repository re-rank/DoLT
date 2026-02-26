"""문서 관련 데이터 모델."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from dolt.models.section import CodeBlock, Page, Section, Table


class IngestStatus(str, Enum):
    NEW = "new"
    UNCHANGED = "unchanged"
    UPDATED = "updated"


class IngestedDocument(BaseModel):
    """Ingestor가 수집 완료 후 반환하는 문서 메타 객체."""

    doc_id: str = Field(description="UUID v4 형식 문서 고유 ID")
    source: str = Field(description="원본 파일 경로 또는 URL")
    file_name: str = Field(description="파일명 (확장자 포함)")
    file_ext: str = Field(description="확장자 (예: .pdf, .docx)")
    file_size_bytes: int = Field(description="파일 크기 (bytes)")
    hash: str = Field(description="SHA-256 해시값")
    status: IngestStatus = Field(description="수집 상태")
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="수집 시각 (UTC)",
    )
    mime_type: str = Field(description="MIME 타입")


class StructuredDocument(BaseModel):
    """Parser의 최종 출력 — 구조화된 문서 객체."""

    doc_id: str
    source: str
    raw_text: str = Field(description="전체 원본 텍스트")
    pages: list[Page] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    code_blocks: list[CodeBlock] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict, description="파일 메타 (제목, 저자 등)")
    total_chars: int = Field(default=0, description="전체 문자 수")
    total_pages: int = Field(default=0, description="전체 페이지 수")
