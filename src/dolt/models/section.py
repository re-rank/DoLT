"""문서 구조 요소 모델 — Page, Section, Table, CodeBlock."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Page(BaseModel):
    """문서의 페이지 단위."""

    page_number: int = Field(description="1-based 페이지 번호")
    text: str = Field(description="페이지 전체 텍스트")
    start_offset: int = Field(description="전체 텍스트 내 시작 위치")
    end_offset: int = Field(description="전체 텍스트 내 종료 위치")


class Section(BaseModel):
    """문서 내 논리적 섹션 (헤딩 기반)."""

    section_id: str = Field(description="섹션 고유 ID (예: sec-001)")
    title: str = Field(description="섹션 제목")
    level: int = Field(description="헤딩 레벨 (1=H1, 2=H2, ...)")
    content: str = Field(description="섹션 본문 텍스트")
    parent_id: str | None = Field(default=None, description="상위 섹션 ID")
    page_number: int | None = Field(default=None, description="소속 페이지")
    start_offset: int = Field(default=0, description="전체 텍스트 내 시작 위치")
    end_offset: int = Field(default=0, description="전체 텍스트 내 종료 위치")


class Table(BaseModel):
    """문서 내 표."""

    table_id: str = Field(description="테이블 고유 ID")
    headers: list[str] = Field(default_factory=list, description="컬럼 헤더 목록")
    rows: list[list[str]] = Field(default_factory=list, description="행 데이터")
    page_number: int | None = Field(default=None)
    section_id: str | None = Field(default=None, description="소속 섹션 ID")
    markdown: str = Field(default="", description="Markdown 테이블 표현")


class CodeBlock(BaseModel):
    """문서 내 코드블록."""

    code_id: str = Field(description="코드블록 고유 ID")
    language: str | None = Field(default=None, description="프로그래밍 언어")
    content: str = Field(description="코드 텍스트")
    page_number: int | None = Field(default=None)
    section_id: str | None = Field(default=None)
